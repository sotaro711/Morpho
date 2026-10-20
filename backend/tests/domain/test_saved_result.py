import pytest

from s4web.domain.entities.material import DispersionPoint, DispersiveMaterial
from s4web.domain.entities.saved_result import (
    MissingMaterialError,
    ResultDraft,
    referenced_material_ids,
)

_TABLE = DispersiveMaterial((DispersionPoint(300, 2.4), DispersionPoint(900, 2.2)))


def _request(*layers: dict[str, object]) -> dict[str, object]:
    return {"wlMin": 380, "wlMax": 780, "wlPoints": 41, "layers": list(layers)}


def test_referenced_material_ids_collects_layers_and_regions() -> None:
    request = _request(
        {"name": "air", "thicknessNm": 0, "n": 1},
        {"name": "film", "thicknessNm": 100, "materialId": "a", "regions": [{"materialId": "b"}]},
    )
    assert referenced_material_ids(request) == {"a", "b"}


def test_draft_accepts_constant_materials_without_snapshots() -> None:
    ResultDraft(_request({"name": "film", "n": 2.0}), {}, colors={}, angles={})


def test_draft_rejects_missing_material_snapshot() -> None:
    request = _request({"name": "film", "materialId": "a"}, {"name": "sub", "materialId": "b"})
    with pytest.raises(MissingMaterialError, match="材料のデータがありません: b"):
        ResultDraft(request, {"a": _TABLE}, colors={}, angles={})
