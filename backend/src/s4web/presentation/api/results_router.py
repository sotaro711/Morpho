"""ユーザーが保存する計算結果の API。

他人の結果は、存在しないものと同じ 404 にする（存在の有無も分からないようにする）。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from s4web.application.usecases.save_result import SaveResultUseCase
from s4web.domain.entities.saved_result import MissingMaterialError
from s4web.domain.ports.result_repository import ResultRepository, ResultTooLargeError
from s4web.presentation.auth import AuthenticatedUser, current_user
from s4web.presentation.dependencies import (
    MaterialRepositoryFactory,
    get_material_repository_factory,
    get_result_repository,
)
from s4web.presentation.schemas.result_dto import ResultCreateRequest, ResultDTO, ResultSummaryDTO

router = APIRouter()

# 一覧に出す件数。古いものは一覧に出ないだけで消えない。
LIST_LIMIT = 50

User = Annotated[AuthenticatedUser, Depends(current_user)]
Repository = Annotated[ResultRepository, Depends(get_result_repository)]


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="計算結果が見つかりません")


@router.get("/results", response_model=list[ResultSummaryDTO])
def list_results(user: User, repository: Repository) -> list[ResultSummaryDTO]:
    return [ResultSummaryDTO.from_entity(r) for r in repository.list_for(user.id, LIST_LIMIT)]


@router.get("/results/{result_id}", response_model=ResultDTO)
def get_result(result_id: str, user: User, repository: Repository) -> ResultDTO:
    saved = repository.get(user.id, result_id)
    if saved is None:
        raise _not_found()
    return ResultDTO.from_entity(saved)


@router.post("/results", response_model=ResultSummaryDTO, status_code=status.HTTP_201_CREATED)
def create_result(
    body: ResultCreateRequest,
    user: User,
    repository: Repository,
    open_materials: Annotated[MaterialRepositoryFactory, Depends(get_material_repository_factory)],
) -> ResultSummaryDTO:
    request, colors, angles = body.to_json()
    try:
        saved = SaveResultUseCase(open_materials, repository).execute(
            user.id, request, colors, angles
        )
    except MissingMaterialError as exc:
        raise HTTPException(
            status_code=422, detail="選択した材料が見つかりません。材料を選び直してください"
        ) from exc
    except ResultTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="計算結果が大きすぎて保存できません。波長や入射角の点数を減らしてください",
        ) from exc
    return ResultSummaryDTO.from_entity(saved.summary())


@router.delete("/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_result(result_id: str, user: User, repository: Repository) -> Response:
    if not repository.delete(user.id, result_id):
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
