from fastapi import APIRouter

router = APIRouter()


# 同期関数にするとスレッドプールで動くため、S4 の計算でプールが埋まると応答できず、
# 忙しいだけのインスタンスが再起動されてしまう。async にしてイベントループで直接返す。
@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
