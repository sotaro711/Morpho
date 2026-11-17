import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from s4web.infrastructure.repositories.firestore_result_repository import (
    ensure_firestore_configured,
)
from s4web.infrastructure.repositories.postgres_material_repository import (
    ensure_database_configured,
)
from s4web.infrastructure.solvers.availability import ensure_solver_available
from s4web.presentation.api.health_router import router as health_router
from s4web.presentation.api.materials_router import router as materials_router
from s4web.presentation.api.me_router import router as me_router
from s4web.presentation.api.results_router import router as results_router
from s4web.presentation.api.simulation_router import router as simulation_router
from s4web.presentation.auth import current_user, ensure_configured
from s4web.presentation.logging_setup import RequestLogMiddleware, configure_logging

# 開発時だけ backend/.env を読む。探索に任せると起動方法で起点が変わるため、パスを明示する。
load_dotenv(Path(__file__).resolve().parents[3] / ".env")


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    ensure_configured()
    ensure_database_configured()
    ensure_firestore_configured()
    ensure_solver_available()
    yield


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="S4 RCWA Simulator API", version="0.1.0", lifespan=_lifespan)
    app.add_middleware(RequestLogMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(simulation_router, prefix="/api", dependencies=[Depends(current_user)])
    app.include_router(me_router, prefix="/api", dependencies=[Depends(current_user)])
    app.include_router(materials_router, prefix="/api", dependencies=[Depends(current_user)])
    app.include_router(results_router, prefix="/api", dependencies=[Depends(current_user)])
    app.include_router(health_router, prefix="/api")

    static_dir = os.environ.get("S4WEB_STATIC_DIR")
    if static_dir and Path(static_dir).is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

    return app


app = create_app()
