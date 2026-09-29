import pytest

from s4web.domain.entities.layer import Layer, Region
from s4web.domain.entities.material import DispersionPoint, DispersiveMaterial, Material
from s4web.domain.entities.simulation import Polarization, SimulationCondition

AIR = Material(1.0)
SUBSTRATE = Material(1.71, 2.88)
MEASURED = DispersiveMaterial((DispersionPoint(400, 2.4), DispersionPoint(700, 2.2)))


def _condition(
    film: Layer, wl_min: float = 400, wl_max: float = 700, period_nm: float | None = None
) -> SimulationCondition:
    return SimulationCondition(
        wl_min_nm=wl_min,
        wl_max_nm=wl_max,
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


def test_wavelengths_within_the_dispersion_data_are_accepted() -> None:
    # 範囲の両端ちょうどは範囲内として扱う。
    _condition(Layer("film", 100, MEASURED), wl_min=400, wl_max=700)


def test_last_sample_is_exactly_wl_max_despite_rounding() -> None:
    # 300 + 19 * ((915 - 300) / 19) は浮動小数点では 915 をわずかに超える。
    condition = SimulationCondition(
        wl_min_nm=300,
        wl_max_nm=915,
        wl_points=20,
        theta_deg=0.0,
        polarization=Polarization.S,
        layers=(
            Layer("air", 0, AIR),
            Layer(
                "film",
                100,
                DispersiveMaterial((DispersionPoint(300, 2.4), DispersionPoint(915, 2.2))),
            ),
            Layer("sub", 0, SUBSTRATE),
        ),
    )
    assert condition.wavelengths_nm()[-1] == 915


@pytest.mark.parametrize("wl_min, wl_max", [(380, 700), (400, 780)], ids=["below", "above"])
def test_wavelengths_outside_the_dispersion_data_are_rejected(wl_min: float, wl_max: float) -> None:
    with pytest.raises(ValueError, match="outside the dispersion data of layer 'film'"):
        _condition(Layer("film", 100, MEASURED), wl_min=wl_min, wl_max=wl_max)


def test_dispersive_region_range_is_also_checked() -> None:
    patterned = Layer("grating", 100, AIR, (Region(MEASURED, 0, 200),))
    with pytest.raises(ValueError, match="layer 'grating'"):
        _condition(patterned, wl_max=780, period_nm=400)


def test_explicit_wavelengths_are_checked() -> None:
    with pytest.raises(ValueError, match="outside the dispersion data"):
        SimulationCondition(
            wl_min_nm=400,
            wl_max_nm=700,
            wl_points=3,
            theta_deg=0.0,
            polarization=Polarization.S,
            layers=(Layer("air", 0, AIR), Layer("film", 100, MEASURED), Layer("sub", 0, SUBSTRATE)),
            explicit_wavelengths_nm=(450.0, 550.0, 750.0),
        )
