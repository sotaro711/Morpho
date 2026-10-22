"""起動時の確認。S4 を読み込めないときは起動に失敗することを確かめる。

S4 の有無は sys.modules を差し替えて再現するので、S4 が入っていない環境（CI）でも動く。
"""

import asyncio
import sys
import types

import pytest

from s4web.infrastructure.solvers.availability import ensure_solver_available
from s4web.presentation.app import create_app


@pytest.fixture
def configured_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # 起動時の確認は値の有無だけを見るので、ダミーで足りる。
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("DATABASE_URL", "postgresql://dummy")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "dummy")


def _without_s4(monkeypatch: pytest.MonkeyPatch) -> None:
    # sys.modules に None を入れると、その名前の import は ImportError になる。
    monkeypatch.setitem(sys.modules, "S4", None)


def _with_s4(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "S4", types.ModuleType("S4"))


def _start_up() -> None:
    app = create_app()

    async def run() -> None:
        async with app.router.lifespan_context(app):
            pass

    asyncio.run(run())


def test_ensure_solver_available_raises_without_s4(monkeypatch: pytest.MonkeyPatch) -> None:
    _without_s4(monkeypatch)
    with pytest.raises(RuntimeError, match="S4 を読み込めません"):
        ensure_solver_available()


def test_ensure_solver_available_passes_with_s4(monkeypatch: pytest.MonkeyPatch) -> None:
    _with_s4(monkeypatch)
    ensure_solver_available()


@pytest.mark.usefixtures("configured_env")
def test_startup_fails_without_s4(monkeypatch: pytest.MonkeyPatch) -> None:
    _without_s4(monkeypatch)
    with pytest.raises(RuntimeError, match="S4 を読み込めません"):
        _start_up()


@pytest.mark.usefixtures("configured_env")
def test_startup_succeeds_with_s4(monkeypatch: pytest.MonkeyPatch) -> None:
    _with_s4(monkeypatch)
    _start_up()
