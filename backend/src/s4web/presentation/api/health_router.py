"""ヘルスチェックのルーター。Cloud Run から認証なしで呼ばれる。"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
