import pytest

from s4web.domain.entities.layer import CircleRegion, Layer, RectRegion, Region
from s4web.domain.entities.material import DispersionPoint, DispersiveMaterial, Material
from s4web.domain.entities.simulation import Polarization, SimulationCondition

AIR = Material(1.0)
SUBSTRATE = Material(1.71, 2.88)
SI = Material(4.0, 0.072)
MEASURED = DispersiveMaterial((DispersionPoint(400, 2.4), DispersionPoint(700, 2.2)))


def _condition(
    film: Layer,
    wl_min: float = 400,
    wl_max: float = 700,
    period_nm: float | None = None,
    period_y_nm: float | None = None,
) -> SimulationCondition:
    return SimulationCondition(
        wl_min_nm=wl_min,
        wl_max_nm=wl_max,
        wl_points=31,
        theta_deg=0.0,
        polarization=Polarization.S,
        layers=(Layer("air", 0, AIR), film, Layer("sub", 0, SUBSTRATE)),
        period_nm=period_nm,
        period_y_nm=period_y_nm,
        num_basis=5 if period_nm else 1,
    )


def test_circle_layer_with_both_periods_is_biperiodic() -> None:
    sliced = Layer("slice", 10, AIR, (CircleRegion(SI, 80, 80, 60),))
    condition = _condition(sliced, period_nm=160, period_y_nm=160)
    assert condition.is_patterned
    assert condition.is_biperiodic


def test_rectangle_layer_without_period_y_is_not_biperiodic() -> None:
    patterned = Layer("grating", 100, AIR, (Region(SI, 0, 200),))
    assert not _condition(patterned, period_nm=400).is_biperiodic


@pytest.mark.parametrize(
    "region",
    [CircleRegion(SI, 80, 80, 60), RectRegion(SI, 80, 80, 60, 60)],
    ids=["circle", "rect"],
)
def test_2d_region_layer_requires_period_y(region: CircleRegion | RectRegion) -> None:
    sliced = Layer("slice", 10, AIR, (region,))
    with pytest.raises(ValueError, match="period_y_nm is required for layers with circle or rect"):
        _condition(sliced, period_nm=160)


def test_azimuth_requires_a_biperiodic_structure() -> None:
    patterned = Layer("grating", 100, AIR, (Region(SI, 0, 200),))
    with pytest.raises(ValueError, match="azimuth_deg requires period_y_nm"):
        SimulationCondition(
            wl_min_nm=400,
            wl_max_nm=700,
            wl_points=31,
            theta_deg=0.0,
            polarization=Polarization.S,
            layers=(Layer("air", 0, AIR), patterned, Layer("sub", 0, SUBSTRATE)),
            period_nm=400,
            num_basis=5,
            azimuth_deg=90.0,
        )


def test_azimuth_must_be_in_range() -> None:
    sliced = Layer("slice", 10, AIR, (CircleRegion(SI, 80, 80, 60),))
    with pytest.raises(ValueError, match="azimuth_deg must be in"):
        SimulationCondition(
            wl_min_nm=400,
            wl_max_nm=700,
            wl_points=31,
            theta_deg=0.0,
            polarization=Polarization.S,
            layers=(Layer("air", 0, AIR), sliced, Layer("sub", 0, SUBSTRATE)),
            period_nm=160,
            period_y_nm=160,
            num_basis=9,
            azimuth_deg=360.0,
        )


def test_period_y_requires_period_x() -> None:
    with pytest.raises(ValueError, match="period_y_nm requires period_nm"):
        _condition(Layer("film", 100, AIR), period_y_nm=160)


def test_period_y_must_be_positive() -> None:
    with pytest.raises(ValueError, match="period_y_nm must be positive"):
        _condition(Layer("film", 100, AIR), period_nm=160, period_y_nm=0)


@pytest.mark.parametrize(
    "cx, cy, radius",
    [(80, 80, 90), (60, 80, 61), (80, 100, 61)],
    ids=["too-large", "crosses-x", "crosses-y"],
)
def test_circle_must_fit_in_the_unit_cell(cx: float, cy: float, radius: float) -> None:
    sliced = Layer("slice", 10, AIR, (CircleRegion(SI, cx, cy, radius),))
    with pytest.raises(ValueError, match="exceeds the unit cell 160 x 160"):
        _condition(sliced, period_nm=160, period_y_nm=160)


def test_circle_touching_the_cell_boundary_is_accepted() -> None:
    sliced = Layer("slice", 10, AIR, (CircleRegion(SI, 80, 80, 80),))
    _condition(sliced, period_nm=160, period_y_nm=160)


@pytest.mark.parametrize(
    "cx, cy, width, height",
    [(80, 80, 200, 100), (50, 80, 120, 100), (80, 100, 100, 140)],
    ids=["too-wide", "crosses-x", "crosses-y"],
)
def test_rect_must_fit_in_the_unit_cell(cx: float, cy: float, width: float, height: float) -> None:
    sliced = Layer("slice", 10, AIR, (RectRegion(SI, cx, cy, width, height),))
    with pytest.raises(ValueError, match="exceeds the unit cell 160 x 160"):
        _condition(sliced, period_nm=160, period_y_nm=160)


def test_rect_filling_the_whole_cell_is_accepted() -> None:
    sliced = Layer("slice", 10, AIR, (RectRegion(SI, 80, 80, 160, 160),))
    assert _condition(sliced, period_nm=160, period_y_nm=160).is_biperiodic


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
