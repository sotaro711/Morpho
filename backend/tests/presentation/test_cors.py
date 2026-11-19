"""CORS の許可先を S4WEB_CORS_ORIGINS で決められることを確かめる。

httpx を入れていないので TestClient は使わず、ASGI アプリを直接呼ぶ。
"""

import anyio
import pytest

from s4web.presentation.app import create_app


async def _preflight(origin: str) -> dict[str, str]:
    app = create_app()
    headers: dict[str, str] = {}

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        if message["type"] == "http.response.start":
            raw = message["headers"]
            assert isinstance(raw, list)
            headers.update({k.decode(): v.decode() for k, v in raw})

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "OPTIONS",
        "scheme": "http",
        "path": "/api/simulate/sweep",
        "raw_path": b"/api/simulate/sweep",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"origin", origin.encode()),
            (b"access-control-request-method", b"POST"),
            (b"access-control-request-headers", b"authorization,content-type"),
        ],
        "client": ("test", 0),
        "server": ("test", 80),
    }
    await app(scope, receive, send)
    return headers


def test_allows_localhost_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("S4WEB_CORS_ORIGINS", raising=False)
    headers = anyio.run(_preflight, "http://localhost:3000")
    assert headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_allows_configured_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S4WEB_CORS_ORIGINS", "https://a.example, https://b.example")
    for origin in ("https://a.example", "https://b.example"):
        headers = anyio.run(_preflight, origin)
        assert headers.get("access-control-allow-origin") == origin


def test_rejects_unlisted_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S4WEB_CORS_ORIGINS", "https://a.example")
    headers = anyio.run(_preflight, "https://evil.example")
    assert "access-control-allow-origin" not in headers
