"""FastAPI アプリケーションの組み立て。"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from s4web.presentation.api.me_router import router as me_router
from s4web.presentation.api.simulation_router import router as simulation_router
from s4web.presentation.auth import current_user, ensure_configured

# 開発時だけ backend/.env を読む。探索に任せると起動方法で起点が変わるため、パスを明示する。
# ファイルがなければ何もせず、既に設定済みの環境変数（Cloud Run など）も上書きしない。
load_dotenv(Path(__file__).resolve().parents[3] / ".env")


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # 設定漏れを最初のリクエスト(500)ではなくサーバー起動時に検出する。
    # Cloud Run では起動に失敗した新リビジョンに切り替わらず、旧リビジョンが動き続ける。
    # create_app() ではなくここで確かめるのは、openapi.json の書き出しやテストのように
    # サーバーを起動しない用途を環境変数なしで動かせるようにするため。
    ensure_configured()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="S4 RCWA Simulator API", version="0.1.0", lifespan=_lifespan)

    # 開発時の保険。本番は Next.js の rewrites でプロキシし CORS 不要にする想定。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # /api 配下はすべてログイン必須。health だけはルーターの外に置いて公開のままにする。
    app.include_router(simulation_router, prefix="/api", dependencies=[Depends(current_user)])
    app.include_router(me_router, prefix="/api")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # S4WEB_STATIC_DIR にフロントのビルド成果物があれば配信する(本番コンテナ用)。
    # /api/* のルートが優先され、それ以外のパスが静的ファイルに割り当てられる。
    static_dir = os.environ.get("S4WEB_STATIC_DIR")
    if static_dir and Path(static_dir).is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

    return app


app = create_app()
