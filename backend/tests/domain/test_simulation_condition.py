from s4web.domain.entities.layer import Layer, Region
from s4web.domain.entities.material import DispersionPoint, DispersiveMaterial, Material
from s4web.domain.entities.simulation import Polarization, SimulationCondition

AIR = Material(1.0)
SUBSTRATE = Material(1.71, 2.88)
MEASURED = DispersiveMaterial((DispersionPoint(400, 2.4), DispersionPoint(700, 2.2)))


def _condition(film: Layer, period_nm: float | None = None) -> SimulationCondition:
    return SimulationCondition(
        wl_min_nm=400,
        wl_max_nm=700,
        wl_points=31,
        theta_deg=0.0,
        polarization=Polarization.S,
        layers=(Layer("air", 0, AIR), film, Layer("sub", 0, SUBSTRATE)),
        period_nm=period_nm,
        num_basis=5 if period_nm else 1,
    )


def test_constant_materials_are_not_dispersive() -> None:
    assert not _condition(Layer("film", 100, Material(2.3))).is_dispersive


def test_dispersive_layer_makes_the_condition_dispersive() -> None:
    assert _condition(Layer("film", 100, MEASURED)).is_dispersive


def test_dispersive_region_makes_the_condition_dispersive() -> None:
    patterned = Layer("grating", 100, AIR, (Region(MEASURED, 0, 200),))
    assert _condition(patterned, period_nm=400).is_dispersive
