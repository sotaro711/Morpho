import pytest

from s4web.domain.entities.material import (
    MAX_DISPERSION_POINTS,
    DispersionPoint,
    DispersiveMaterial,
    Material,
)


def _material(*points: tuple[float, float, float]) -> DispersiveMaterial:
    return DispersiveMaterial(tuple(DispersionPoint(w, n, k) for w, n, k in points))


def test_material_exposes_complex_refractive_index() -> None:
    assert Material(2.3, 0.1).refractive_index == complex(2.3, 0.1)


@pytest.mark.parametrize("n, k", [(0.0, 0.0), (-1.0, 0.0), (1.5, -0.1)])
def test_material_rejects_unphysical_values(n: float, k: float) -> None:
    with pytest.raises(ValueError):
        Material(n, k)


def test_constant_material_is_the_same_at_every_wavelength() -> None:
    m = Material(2.3, 0.1)
    assert m.wavelength_range_nm is None
    assert m.refractive_index_at(400) == m.refractive_index_at(800) == complex(2.3, 0.1)


def test_dispersive_material_returns_measured_values_at_points() -> None:
    m = _material((400, 2.5, 0.2), (500, 2.3, 0.0), (600, 2.2, 0.0))
    assert m.refractive_index_at(500) == complex(2.3, 0.0)
    assert m.wavelength_range_nm == (400, 600)


def test_dispersive_material_interpolates_n_and_k_linearly() -> None:
    m = _material((400, 2.5, 0.2), (500, 2.3, 0.0))
    value = m.refractive_index_at(425)
    assert value.real == pytest.approx(2.45)
    assert value.imag == pytest.approx(0.15)


def test_dispersive_material_clamps_outside_the_range() -> None:
    # 範囲外は計算条件で拒否する予定。Rayleigh 点回避の微小シフトでは端の値を使う。
    m = _material((400, 2.5, 0.2), (500, 2.3, 0.0))
    assert m.refractive_index_at(399.9) == complex(2.5, 0.2)
    assert m.refractive_index_at(500.1) == complex(2.3, 0.0)


@pytest.mark.parametrize(
    "points",
    [
        [(400, 2.5, 0.0)],
        [(500, 2.5, 0.0), (400, 2.3, 0.0)],
        [(400, 2.5, 0.0), (400, 2.3, 0.0)],
    ],
    ids=["single point", "decreasing", "duplicated wavelength"],
)
def test_dispersive_material_rejects_invalid_tables(
    points: list[tuple[float, float, float]],
) -> None:
    with pytest.raises(ValueError):
        _material(*points)


def test_dispersive_material_rejects_too_many_points() -> None:
    with pytest.raises(ValueError):
        _material(*((300 + i, 2.0, 0.0) for i in range(MAX_DISPERSION_POINTS + 1)))


@pytest.mark.parametrize("n, k", [(0.0, 0.0), (-1.0, 0.0), (1.5, -0.1)])
def test_dispersion_point_rejects_unphysical_values(n: float, k: float) -> None:
    with pytest.raises(ValueError):
        DispersionPoint(500, n, k)
