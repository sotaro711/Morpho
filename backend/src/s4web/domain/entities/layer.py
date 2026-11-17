import math
from dataclasses import dataclass

from s4web.domain.entities.material import OpticalMaterial


@dataclass(frozen=True)
class Region:
    material: OpticalMaterial
    x_nm: float
    width_nm: float

    def __post_init__(self) -> None:
        if self.x_nm < 0:
            raise ValueError(f"region x_nm must be non-negative, got {self.x_nm}")
        if self.width_nm <= 0:
            raise ValueError(f"region width_nm must be positive, got {self.width_nm}")

    @property
    def end_nm(self) -> float:
        return self.x_nm + self.width_nm


@dataclass(frozen=True)
class CircleRegion:
    material: OpticalMaterial
    cx_nm: float
    cy_nm: float
    radius_nm: float

    def __post_init__(self) -> None:
        if self.radius_nm <= 0:
            raise ValueError(f"circle radius_nm must be positive, got {self.radius_nm}")

    def overlaps(self, other: CircleRegion) -> bool:
        return math.hypot(self.cx_nm - other.cx_nm, self.cy_nm - other.cy_nm) < (
            self.radius_nm + other.radius_nm
        )


@dataclass(frozen=True)
class RectRegion:
    material: OpticalMaterial
    cx_nm: float
    cy_nm: float
    width_nm: float
    height_nm: float

    def __post_init__(self) -> None:
        if self.width_nm <= 0:
            raise ValueError(f"rect width_nm must be positive, got {self.width_nm}")
        if self.height_nm <= 0:
            raise ValueError(f"rect height_nm must be positive, got {self.height_nm}")

    def overlaps(self, other: RectRegion) -> bool:
        return (
            abs(self.cx_nm - other.cx_nm) < (self.width_nm + other.width_nm) / 2
            and abs(self.cy_nm - other.cy_nm) < (self.height_nm + other.height_nm) / 2
        )


Region2D = CircleRegion | RectRegion


@dataclass(frozen=True)
class Layer:
    name: str
    thickness_nm: float
    material: OpticalMaterial
    regions: tuple[Region | Region2D, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("layer name must not be empty")
        if self.thickness_nm < 0:
            raise ValueError(f"thickness_nm must be non-negative, got {self.thickness_nm}")
        kinds = {type(r) for r in self.regions}
        if len(kinds) > 1:
            raise ValueError(f"layer '{self.name}' must not mix region kinds")
        stripes = [r for r in self.regions if isinstance(r, Region)]
        ordered = sorted(stripes, key=lambda r: r.x_nm)
        for prev, nxt in zip(ordered, ordered[1:], strict=False):
            if nxt.x_nm < prev.end_nm:
                raise ValueError(
                    f"regions in layer '{self.name}' must not overlap: "
                    f"[{prev.x_nm}, {prev.end_nm}) and [{nxt.x_nm}, {nxt.end_nm})"
                )
        circles = [r for r in self.regions if isinstance(r, CircleRegion)]
        rects = [r for r in self.regions if isinstance(r, RectRegion)]
        self._reject_overlaps(circles)
        self._reject_overlaps(rects)

    def _reject_overlaps[S: (CircleRegion, RectRegion)](self, shapes: list[S]) -> None:
        for i, a in enumerate(shapes):
            for b in shapes[i + 1 :]:
                if a.overlaps(b):
                    raise ValueError(
                        f"regions in layer '{self.name}' must not overlap: {a} and {b}"
                    )

    @property
    def is_patterned(self) -> bool:
        return len(self.regions) > 0

    @property
    def has_2d_regions(self) -> bool:
        return any(not isinstance(r, Region) for r in self.regions)
