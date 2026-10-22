"""/api/health（liveness probe の確認先）が、スレッドプールが埋まっていても応答するかを確かめる。

httpx を入れていないので TestClient は使わず、ASGI アプリを直接呼ぶ。
"""

import threading

import anyio
import anyio.to_thread

from s4web.presentation.app import create_app


async def _get_status(path: str) -> int | None:
    app = create_app()
    status: int | None = None

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]  # type: ignore[assignment]

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("test", 0),
        "server": ("test", 80),
    }
    await app(scope, receive, send)
    return status


def test_health_returns_ok() -> None:
    assert anyio.run(_get_status, "/api/health") == 200


def test_health_responds_while_thread_pool_is_full() -> None:
    async def run() -> int | None:
        # 同期のエンドポイント（S4 の計算など）が使うスレッドプールを 1 本にして、それを塞ぐ。
        anyio.to_thread.current_default_thread_limiter().total_tokens = 1
        release = threading.Event()
        async with anyio.create_task_group() as tg:
            tg.start_soon(anyio.to_thread.run_sync, release.wait)
            await anyio.sleep(0.05)
            try:
                with anyio.fail_after(2):
                    return await _get_status("/api/health")
            finally:
                release.set()

    assert anyio.run(run) == 200
