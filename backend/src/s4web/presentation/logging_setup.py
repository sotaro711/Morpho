"""ログの出力先と形式、リクエスト単位の開始・終了ログ。

Cloud Run は stdout / stderr の各行を Cloud Logging に取り込む。1 行を JSON にして
severity と trace を付けると、重要度で絞り込めるほか、計算中に出た進捗ログを
「このリクエストのもの」として辿れる（リクエストログと同じ trace になる）。
ローカルでは読みやすいテキスト形式にする。

uvicorn のアクセスログはレスポンスを返した時点でしか出ないので、受け付けた時点の
ログはここのミドルウェアで出す。数百秒かかる計算で「止まっているのか、動いているのか」
を区別するため。
"""

import json
import logging
import os
import sys
import time
from collections.abc import Awaitable, Callable, MutableMapping
from contextvars import ContextVar
from typing import Any

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

_logger = logging.getLogger(__name__)

# 処理中のリクエストの trace。同期エンドポイントはスレッドプールで動くが、
# contextvars は anyio がスレッドに複製するので、計算中のログからも読める。
_trace: ContextVar[str | None] = ContextVar("trace", default=None)

# liveness probe が 30 秒ごとに叩くので、開始・終了ログは出さない。
_QUIET_PATHS = frozenset({"/api/health"})


class _CloudLoggingFormatter(logging.Formatter):
    """Cloud Logging の構造化ログ（1 行 JSON）。"""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        payload: dict[str, str] = {
            "severity": record.levelname,
            "message": message,
            "logger": record.name,
        }
        trace = _trace.get()
        if trace:
            payload["logging.googleapis.com/trace"] = trace
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """root ロガーの出力先と形式、レベル（LOG_LEVEL、既定 INFO）を設定する。

    uvicorn 自身のロガー（アクセスログなど）は propagate しないので影響しない。
    """
    handler = logging.StreamHandler(sys.stderr)
    if os.environ.get("K_SERVICE"):
        # Cloud Run が設定する環境変数。
        handler.setFormatter(_CloudLoggingFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())


def _trace_from_headers(scope: Scope) -> str | None:
    # Cloud Run のロードバランサが付ける "TRACE_ID/SPAN_ID;o=1" から trace を組み立てる。
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        return None
    for name, value in scope.get("headers", ()):
        if name == b"x-cloud-trace-context":
            trace_id = value.decode("latin-1").split("/", 1)[0]
            return f"projects/{project}/traces/{trace_id}" if trace_id else None
    return None


class RequestLogMiddleware:
    """/api 配下のリクエストの開始と終了（status と所要秒）をログに出す純 ASGI ミドルウェア。

    BaseHTTPMiddleware ではなく生の ASGI にするのは、/api/health の応答を
    スレッドプールの空きに依存させないため（test_health を参照）。
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or not path.startswith("/api") or path in _QUIET_PATHS:
            await self._app(scope, receive, send)
            return

        _trace.set(_trace_from_headers(scope))
        label = f"{scope['method']} {path}"
        status: int | None = None

        async def send_with_status(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        _logger.info("→ %s", label)
        started = time.perf_counter()
        try:
            await self._app(scope, receive, send_with_status)
        except BaseException:
            _logger.exception("✗ %s failed after %.1fs", label, time.perf_counter() - started)
            raise
        _logger.info("← %s %s in %.1fs", label, status, time.perf_counter() - started)
