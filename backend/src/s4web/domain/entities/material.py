from bisect import bisect_left
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Material:
    n: float
    k: float = 0.0

    def __post_init__(self) -> None:
        if self.n <= 0:
            raise ValueError(f"refractive index n must be positive, got {self.n}")
        if self.k < 0:
            raise ValueError(f"extinction coefficient k must be non-negative, got {self.k}")

    @property
    def refractive_index(self) -> complex:
        return complex(self.n, self.k)

    @property
    def wavelength_range_nm(self) -> None:
        return None

    def refractive_index_at(self, wavelength_nm: float) -> complex:
        return self.refractive_index


MAX_DISPERSION_POINTS = 5000


@dataclass(frozen=True)
class DispersionPoint:
    wavelength_nm: float
    n: float
    k: float = 0.0

    def __post_init__(self) -> None:
        if not all(map(isfinite, (self.wavelength_nm, self.n, self.k))):
            raise ValueError(
                f"dispersion point must be finite, got ({self.wavelength_nm}, {self.n}, {self.k})"
            )
        if self.wavelength_nm <= 0:
            raise ValueError(f"wavelength must be positive, got {self.wavelength_nm}")
        if self.n <= 0:
            raise ValueError(f"refractive index n must be positive, got {self.n}")
        if self.k < 0:
            raise ValueError(f"extinction coefficient k must be non-negative, got {self.k}")


@dataclass(frozen=True)
class DispersiveMaterial:
    points: tuple[DispersionPoint, ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("dispersive material needs at least 2 points")
        if len(self.points) > MAX_DISPERSION_POINTS:
            raise ValueError(
                f"dispersive material allows at most {MAX_DISPERSION_POINTS} points, "
                f"got {len(self.points)}"
            )
        for prev, nxt in zip(self.points, self.points[1:], strict=False):
            if nxt.wavelength_nm <= prev.wavelength_nm:
                raise ValueError(
                    "dispersion points must be strictly increasing in wavelength "
                    f"({prev.wavelength_nm} -> {nxt.wavelength_nm})"
                )

    @property
    def wavelength_range_nm(self) -> tuple[float, float]:
        return self.points[0].wavelength_nm, self.points[-1].wavelength_nm

    def refractive_index_at(self, wavelength_nm: float) -> complex:
        first, last = self.points[0], self.points[-1]
        if wavelength_nm <= first.wavelength_nm:
            return complex(first.n, first.k)
        if wavelength_nm >= last.wavelength_nm:
            return complex(last.n, last.k)
        i = bisect_left(self.points, wavelength_nm, key=lambda p: p.wavelength_nm)
        lo, hi = self.points[i - 1], self.points[i]
        t = (wavelength_nm - lo.wavelength_nm) / (hi.wavelength_nm - lo.wavelength_nm)
        return complex(lo.n + t * (hi.n - lo.n), lo.k + t * (hi.k - lo.k))


OpticalMaterial = Material | DispersiveMaterial
