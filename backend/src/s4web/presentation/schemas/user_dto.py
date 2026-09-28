"""ログイン中ユーザーの DTO。"""

from pydantic import BaseModel


class MeResponse(BaseModel):
    id: str
    email: str
