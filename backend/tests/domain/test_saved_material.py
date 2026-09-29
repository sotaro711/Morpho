import pytest

from s4web.domain.entities.material import DispersionPoint, DispersiveMaterial
from s4web.domain.entities.saved_material import MAX_MATERIAL_NAME_LENGTH, MaterialDraft


def _table(lo: float, hi: float) -> DispersiveMaterial:
    return DispersiveMaterial((DispersionPoint(lo, 2.4), DispersionPoint(hi, 2.2)))


def test_draft_trims_the_name() -> None:
    assert MaterialDraft("  TiO2 (ALD) ", _table(300, 900)).name == "TiO2 (ALD)"


@pytest.mark.parametrize(
    "name", ["   ", "x" * (MAX_MATERIAL_NAME_LENGTH + 1)], ids=["blank", "long"]
)
def test_draft_rejects_invalid_names(name: str) -> None:
    with pytest.raises(ValueError, match="材料名"):
        MaterialDraft(name, _table(300, 900))


def test_draft_accepts_data_covering_the_required_range_exactly() -> None:
    MaterialDraft("ok", _table(380, 780))


@pytest.mark.parametrize("lo, hi", [(400, 900), (300, 700)], ids=["starts late", "ends early"])
def test_draft_rejects_data_not_covering_the_required_range(lo: float, hi: float) -> None:
    with pytest.raises(ValueError, match="380〜780 nm を含んでいません"):
        MaterialDraft("TiO2", _table(lo, hi))
