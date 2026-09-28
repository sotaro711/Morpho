"""ログイン中ユーザーを返すルーター。フロントとの疎通確認に使う。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from s4web.presentation.auth import AuthenticatedUser, current_user
from s4web.presentation.schemas.user_dto import MeResponse

router = APIRouter()


@router.get("/me", response_model=MeResponse)
def me(user: Annotated[AuthenticatedUser, Depends(current_user)]) -> MeResponse:
    return MeResponse(id=user.id, email=user.email)
