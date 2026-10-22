"""ヘルスチェックのルーター。Cloud Run から認証なしで呼ばれる。

liveness probe の確認先なので、軽く、外部サービス（DB・Firestore）に依存させない。
外部の一時的な障害で全インスタンスが再起動され続けるのを避けるため。
"""

from fastapi import APIRouter

router = APIRouter()


# 同期関数にするとスレッドプールで動くため、S4 の計算でプールが埋まると応答できず、
# 忙しいだけのインスタンスが再起動されてしまう。async にしてイベントループで直接返す。
@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
