"""リクエストの開始・終了ログと、Cloud Run 向けの JSON 形式の確認。

httpx を入れていないので TestClient は使わず、ASGI アプリを直接呼ぶ（test_health と同じ）。
"""

import json
import logging

import anyio
import pytest

from s4web.presentation.logging_setup import (
    RequestLogMiddleware,
    _CloudLoggingFormatter,
    _trace,
)


async def _call(path: str, headers: tuple[tuple[bytes, bytes], ...] = ()) -> None:
    async def app(scope, receive, send) -> None:
        # 同期エンドポイントと同様にスレッドプールで出したログにも trace が付くことを確かめる。
        await anyio.to_thread.run_sync(logging.getLogger("s4web.test").info, "working")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        pass

    scope = {"type": "http", "method": "POST", "path": path, "headers": headers}
    await RequestLogMiddleware(app)(scope, receive, send)


def test_logs_start_and_end_of_api_requests(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        anyio.run(_call, "/api/simulate/sweep")
    messages = [r.getMessage() for r in caplog.records]
    assert messages[0] == "→ POST /api/simulate/sweep"
    assert messages[1] == "working"
    assert messages[2].startswith("← POST /api/simulate/sweep 200 in ")


def test_health_and_static_paths_are_quiet(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        anyio.run(_call, "/api/health")
        anyio.run(_call, "/_next/static/x.js")
    assert [r.getMessage() for r in caplog.records] == ["working", "working"]


def test_trace_from_cloud_run_header_reaches_logs_in_thread_pool(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "morpho-sim")
    formatter = _CloudLoggingFormatter()
    header = ((b"x-cloud-trace-context", b"abc123/456;o=1"),)
    traces: list[str | None] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            traces.append(json.loads(formatter.format(record)).get("logging.googleapis.com/trace"))

    root = logging.getLogger()
    handler = Capture(level=logging.INFO)
    root.addHandler(handler)
    try:
        with caplog.at_level(logging.INFO):
            anyio.run(_call, "/api/simulate", header)
    finally:
        root.removeHandler(handler)
    assert traces == ["projects/morpho-sim/traces/abc123"] * 3


def test_cloud_logging_format_has_severity_and_message() -> None:
    record = logging.LogRecord("s4web.x", logging.WARNING, "f.py", 1, "R=%.2f", (0.5,), None)
    _trace.set(None)
    payload = json.loads(_CloudLoggingFormatter().format(record))
    assert payload == {"severity": "WARNING", "message": "R=0.50", "logger": "s4web.x"}
