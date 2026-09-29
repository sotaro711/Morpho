"""ユーザーが登録する材料（波長ごとの n, k の表）の API。

他人の材料は、存在しないものと同じ 404 にする（存在の有無も分からないようにする）。
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from s4web.domain.entities.saved_material import MaterialDraft, validate_material_name
from s4web.domain.ports.material_repository import (
    DuplicateMaterialNameError,
    MaterialRepository,
)
from s4web.domain.services.optical_constants_file import parse_optical_constants
from s4web.presentation.auth import AuthenticatedUser, current_user
from s4web.presentation.dependencies import get_material_repository
from s4web.presentation.schemas.material_dto import (
    MaterialCreateRequest,
    MaterialDTO,
    MaterialRenameRequest,
    MaterialSummaryDTO,
)

router = APIRouter()

User = Annotated[AuthenticatedUser, Depends(current_user)]
Repository = Annotated[MaterialRepository, Depends(get_material_repository)]


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="材料が見つかりません")


def _conflict(name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"「{name}」という名前の材料はすでにあります。成膜条件などを名前に入れて区別してください",
    )


@router.get("/materials", response_model=list[MaterialSummaryDTO])
def list_materials(user: User, repository: Repository) -> list[MaterialSummaryDTO]:
    return [MaterialSummaryDTO.from_entity(m) for m in repository.list_for(user.id)]


@router.get("/materials/{material_id}", response_model=MaterialDTO)
def get_material(material_id: UUID, user: User, repository: Repository) -> MaterialDTO:
    saved = repository.get(user.id, str(material_id))
    if saved is None:
        raise _not_found()
    return MaterialDTO.from_entity(saved)


@router.post("/materials", response_model=MaterialDTO, status_code=status.HTTP_201_CREATED)
def create_material(
    request: MaterialCreateRequest, user: User, repository: Repository
) -> MaterialDTO:
    # ファイルの読み取り・名前・波長範囲の検証は domain が日本語の ValueError で返す。
    try:
        draft = MaterialDraft(request.name, parse_optical_constants(request.content))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        saved = repository.create(user.id, draft)
    except DuplicateMaterialNameError as exc:
        raise _conflict(draft.name) from exc
    return MaterialDTO.from_entity(saved)


@router.patch("/materials/{material_id}", response_model=MaterialSummaryDTO)
def rename_material(
    material_id: UUID, request: MaterialRenameRequest, user: User, repository: Repository
) -> MaterialSummaryDTO:
    try:
        name = validate_material_name(request.name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        saved = repository.rename(user.id, str(material_id), name)
    except DuplicateMaterialNameError as exc:
        raise _conflict(name) from exc
    if saved is None:
        raise _not_found()
    return MaterialSummaryDTO.from_entity(saved)


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(material_id: UUID, user: User, repository: Repository) -> Response:
    if not repository.delete(user.id, str(material_id)):
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
