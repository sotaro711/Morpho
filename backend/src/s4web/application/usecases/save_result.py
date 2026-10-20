"""計算結果を保存するユースケース。"""

from collections.abc import Callable
from contextlib import AbstractContextManager

from s4web.domain.entities.saved_result import (
    Json,
    ResultDraft,
    SavedResult,
    referenced_material_ids,
)
from s4web.domain.ports.material_repository import MaterialRepository
from s4web.domain.ports.result_repository import ResultRepository


class SaveResultUseCase:
    """計算条件が参照する材料のデータを添えて、結果を保存する。"""

    def __init__(
        self,
        open_materials: Callable[[], AbstractContextManager[MaterialRepository]],
        results: ResultRepository,
    ) -> None:
        self._open_materials = open_materials
        self._results = results

    def execute(self, owner_id: str, request: Json, colors: Json, angles: Json) -> SavedResult:
        """材料が見つからなければ MissingMaterialError（ResultDraft が出す）。"""
        ids = referenced_material_ids(request)
        materials = {}
        if ids:
            with self._open_materials() as repository:
                found = repository.get_many(owner_id, ids)
            materials = {material_id: saved.material for material_id, saved in found.items()}
        draft = ResultDraft(request=request, materials=materials, colors=colors, angles=angles)
        return self._results.add(owner_id, draft)
