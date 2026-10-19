from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest

from s4web.application.usecases.save_result import SaveResultUseCase
from s4web.domain.entities.material import DispersionPoint, DispersiveMaterial
from s4web.domain.entities.saved_material import MaterialDraft, SavedMaterial
from s4web.domain.entities.saved_result import MissingMaterialError, ResultDraft, SavedResult
from s4web.domain.ports.material_repository import MaterialRepository
from s4web.domain.ports.result_repository import ResultRepository

OWNER = "u1"
TABLE = DispersiveMaterial((DispersionPoint(300, 2.4), DispersionPoint(900, 2.2)))


class _Materials(MaterialRepository):
    def __init__(self, materials: dict[str, DispersiveMaterial]) -> None:
        self.materials = materials
        self.opened = False

    def get_many(self, owner_id: str, material_ids: set[str]) -> dict[str, SavedMaterial]:
        return {
            material_id: SavedMaterial(material_id, material_id, material, datetime.now(UTC))
            for material_id, material in self.materials.items()
            if owner_id == OWNER and material_id in material_ids
        }

    def list_for(self, owner_id: str) -> tuple[SavedMaterial, ...]:
        raise NotImplementedError

    def get(self, owner_id: str, material_id: str) -> SavedMaterial | None:
        raise NotImplementedError

    def create(self, owner_id: str, draft: MaterialDraft) -> SavedMaterial:
        raise NotImplementedError

    def rename(self, owner_id: str, material_id: str, name: str) -> SavedMaterial | None:
        raise NotImplementedError

    def delete(self, owner_id: str, material_id: str) -> bool:
        raise NotImplementedError


class _Results(ResultRepository):
    def __init__(self) -> None:
        self.added: list[ResultDraft] = []

    def add(self, owner_id: str, draft: ResultDraft) -> SavedResult:
        self.added.append(draft)
        return SavedResult(str(len(self.added)), draft, datetime.now(UTC))

    def list_for(self, owner_id: str) -> tuple[SavedResult, ...]:
        raise NotImplementedError

    def get(self, owner_id: str, result_id: str) -> SavedResult | None:
        raise NotImplementedError

    def delete(self, owner_id: str, result_id: str) -> bool:
        raise NotImplementedError


def _use_case(materials: _Materials, results: _Results) -> SaveResultUseCase:
    @contextmanager
    def open_materials() -> Iterator[MaterialRepository]:
        materials.opened = True
        yield materials

    return SaveResultUseCase(open_materials, results)


def test_attaches_referenced_materials() -> None:
    results = _Results()
    request = {"layers": [{"name": "film", "materialId": "m1"}]}

    _use_case(_Materials({"m1": TABLE, "m2": TABLE}), results).execute(OWNER, request, {}, {})

    assert results.added[0].materials == {"m1": TABLE}


def test_does_not_open_materials_for_constant_layers() -> None:
    materials = _Materials({})
    _use_case(materials, _Results()).execute(OWNER, {"layers": [{"n": 2.0}]}, {}, {})
    assert not materials.opened


def test_rejects_materials_of_other_owners() -> None:
    results = _Results()
    request = {"layers": [{"name": "film", "materialId": "m1"}]}

    with pytest.raises(MissingMaterialError):
        _use_case(_Materials({"m1": TABLE}), results).execute("other", request, {}, {})
    assert results.added == []
