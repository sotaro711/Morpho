import pytest

from s4web.domain.entities.layer import CircleRegion, Layer, RectRegion, Region
from s4web.domain.entities.material import Material

AIR = Material(1.0)
SI = Material(4.0, 0.072)


def test_circle_radius_must_be_positive() -> None:
    with pytest.raises(ValueError, match="radius_nm must be positive"):
        CircleRegion(SI, 80, 80, 0)


@pytest.mark.parametrize("width, height", [(0, 10), (10, -1)], ids=["width", "height"])
def test_rect_sides_must_be_positive(width: float, height: float) -> None:
    with pytest.raises(ValueError, match="must be positive"):
        RectRegion(SI, 80, 80, width, height)


def test_non_overlapping_circles_are_accepted() -> None:
    layer = Layer("slice", 10, AIR, (CircleRegion(SI, 50, 50, 30), CircleRegion(SI, 150, 50, 30)))
    assert layer.is_patterned
    assert layer.has_2d_regions


def test_overlapping_circles_are_rejected() -> None:
    with pytest.raises(ValueError, match="regions in layer 'slice' must not overlap"):
        Layer("slice", 10, AIR, (CircleRegion(SI, 50, 50, 30), CircleRegion(SI, 100, 50, 30)))


def test_touching_circles_are_not_overlapping() -> None:
    Layer("slice", 10, AIR, (CircleRegion(SI, 50, 50, 30), CircleRegion(SI, 110, 50, 30)))


def test_overlapping_rects_are_rejected() -> None:
    with pytest.raises(ValueError, match="regions in layer 'slice' must not overlap"):
        Layer("slice", 10, AIR, (RectRegion(SI, 50, 50, 60, 60), RectRegion(SI, 100, 90, 60, 60)))


def test_touching_rects_are_not_overlapping() -> None:
    layer = Layer(
        "slice", 10, AIR, (RectRegion(SI, 50, 50, 60, 60), RectRegion(SI, 110, 50, 60, 60))
    )
    assert layer.has_2d_regions


@pytest.mark.parametrize(
    "regions",
    [
        (Region(SI, 0, 100), CircleRegion(SI, 50, 50, 30)),
        (Region(SI, 0, 100), RectRegion(SI, 50, 50, 30, 30)),
        (CircleRegion(SI, 50, 50, 30), RectRegion(SI, 150, 50, 30, 30)),
    ],
    ids=["stripe+circle", "stripe+rect", "circle+rect"],
)
def test_region_kinds_must_not_be_mixed(regions: tuple) -> None:
    with pytest.raises(ValueError, match="must not mix"):
        Layer("slice", 10, AIR, regions)


def test_stripe_layer_has_no_2d_regions() -> None:
    assert not Layer("grating", 10, AIR, (Region(SI, 0, 100),)).has_2d_regions
