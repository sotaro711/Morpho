import pytest

from s4web.domain.entities.material import Material


def test_material_exposes_complex_refractive_index() -> None:
    assert Material(2.3, 0.1).refractive_index == complex(2.3, 0.1)


@pytest.mark.parametrize("n, k", [(0.0, 0.0), (-1.0, 0.0), (1.5, -0.1)])
def test_material_rejects_unphysical_values(n: float, k: float) -> None:
    with pytest.raises(ValueError):
        Material(n, k)
