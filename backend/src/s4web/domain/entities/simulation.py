from dataclasses import dataclass
from enum import StrEnum

from s4web.domain.entities.color import ColorResult
from s4web.domain.entities.layer import CircleRegion, Layer, Region
from s4web.domain.entities.material import OpticalMaterial


class Polarization(StrEnum):
    """偏光。S=TE、P=TM。"""

    S = "s"
    P = "p"


class DiffractionMode(StrEnum):
    ZEROTH = "zeroth"
    NON_ZEROTH = "non_zeroth"
    TOTAL = "total"


NUM_BASIS_LIMIT = 225
NUM_BASIS_LIMIT_1D = 61


@dataclass(frozen=True)
class SimulationCondition:
    wl_min_nm: float
    wl_max_nm: float
    wl_points: int
    theta_deg: float
    polarization: Polarization
    layers: tuple[Layer, ...]
    period_nm: float | None = None
    period_y_nm: float | None = None
    num_basis: int = 1
    explicit_wavelengths_nm: tuple[float, ...] | None = None
    azimuth_deg: float = 0.0

    def __post_init__(self) -> None:
        if self.wl_min_nm <= 0 or self.wl_max_nm <= 0:
            raise ValueError("wavelengths must be positive")
        if self.wl_min_nm > self.wl_max_nm:
            raise ValueError("wl_min_nm must be <= wl_max_nm")
        if self.wl_points < 1:
            raise ValueError("wl_points must be >= 1")
        if self.wl_points == 1 and self.wl_min_nm != self.wl_max_nm:
            raise ValueError("wl_points == 1 requires wl_min_nm == wl_max_nm")
        if not (-90.0 < self.theta_deg < 90.0):
            raise ValueError("theta_deg must be in (-90, 90)")
        if len(self.layers) < 2:
            raise ValueError("at least two layers are required (incident + substrate)")
        if not (1 <= self.num_basis <= NUM_BASIS_LIMIT):
            raise ValueError(f"num_basis must be in [1, {NUM_BASIS_LIMIT}], got {self.num_basis}")
        if self.explicit_wavelengths_nm is not None:
            if len(self.explicit_wavelengths_nm) == 0:
                raise ValueError("explicit_wavelengths_nm must not be empty")
            for wl in self.explicit_wavelengths_nm:
                if wl <= 0:
                    raise ValueError(f"explicit wavelengths must be positive, got {wl}")
            for prev, nxt in zip(
                self.explicit_wavelengths_nm, self.explicit_wavelengths_nm[1:], strict=False
            ):
                if nxt <= prev:
                    raise ValueError(
                        f"explicit_wavelengths_nm must be strictly increasing ({prev} -> {nxt})"
                    )
        if self.period_nm is not None and self.period_nm <= 0:
            raise ValueError(f"period_nm must be positive, got {self.period_nm}")
        if self.period_y_nm is not None:
            if self.period_y_nm <= 0:
                raise ValueError(f"period_y_nm must be positive, got {self.period_y_nm}")
            if self.period_nm is None:
                raise ValueError("period_y_nm requires period_nm")
        if not (0.0 <= self.azimuth_deg < 360.0):
            raise ValueError(f"azimuth_deg must be in [0, 360), got {self.azimuth_deg}")
        if self.azimuth_deg != 0.0 and self.period_y_nm is None:
            raise ValueError("azimuth_deg requires period_y_nm (biperiodic structure)")
        if self.period_y_nm is None and self.num_basis > NUM_BASIS_LIMIT_1D:
            raise ValueError(
                f"num_basis must be <= {NUM_BASIS_LIMIT_1D} unless period_y_nm is set "
                f"(biperiodic structure), got {self.num_basis}"
            )
        self._validate_regions()
        self._validate_dispersion_ranges()

    def _validate_regions(self) -> None:
        patterned = [layer for layer in self.layers if layer.is_patterned]
        if not patterned:
            return
        if self.period_nm is None:
            names = ", ".join(layer.name for layer in patterned)
            raise ValueError(f"period_nm is required for patterned layers ({names})")
        shaped = [layer for layer in patterned if layer.has_2d_regions]
        if shaped and self.period_y_nm is None:
            names = ", ".join(layer.name for layer in shaped)
            raise ValueError(
                f"period_y_nm is required for layers with circle or rect regions ({names})"
            )
        for layer in patterned:
            for region in layer.regions:
                if isinstance(region, Region):
                    if region.end_nm > self.period_nm:
                        raise ValueError(
                            f"region [{region.x_nm}, {region.end_nm}) in layer "
                            f"'{layer.name}' exceeds period_nm={self.period_nm}"
                        )
                    continue
                assert self.period_y_nm is not None
                if isinstance(region, CircleRegion):
                    hx = hy = region.radius_nm
                else:
                    hx, hy = region.width_nm / 2, region.height_nm / 2
                if not (
                    hx <= region.cx_nm <= self.period_nm - hx
                    and hy <= region.cy_nm <= self.period_y_nm - hy
                ):
                    raise ValueError(
                        f"{region} in layer '{layer.name}' exceeds the unit cell "
                        f"{self.period_nm} x {self.period_y_nm}"
                    )

    def _validate_dispersion_ranges(self) -> None:
        wls = self.wavelengths_nm()
        lo, hi = min(wls), max(wls)
        for layer, material in self._layer_materials():
            wl_range = material.wavelength_range_nm
            if wl_range is None:
                continue
            if lo < wl_range[0] or hi > wl_range[1]:
                raise ValueError(
                    f"wavelengths {lo:g}-{hi:g} nm are outside the dispersion data of layer "
                    f"'{layer.name}' ({wl_range[0]:g}-{wl_range[1]:g} nm)"
                )

    def _layer_materials(self) -> list[tuple[Layer, OpticalMaterial]]:
        return [
            (layer, material)
            for layer in self.layers
            for material in (layer.material, *(region.material for region in layer.regions))
        ]

    @property
    def is_dispersive(self) -> bool:
        return any(
            material.wavelength_range_nm is not None for _, material in self._layer_materials()
        )

    @property
    def is_patterned(self) -> bool:
        return any(layer.is_patterned for layer in self.layers)

    @property
    def is_biperiodic(self) -> bool:
        return self.period_y_nm is not None

    def wavelengths_nm(self) -> list[float]:
        if self.explicit_wavelengths_nm is not None:
            return list(self.explicit_wavelengths_nm)
        if self.wl_points == 1:
            return [self.wl_min_nm]
        step = (self.wl_max_nm - self.wl_min_nm) / (self.wl_points - 1)
        # wl_min + (n-1)*step は丸め誤差で wl_max をわずかに超えることがあり、
        # 分散データの上限ちょうどを指定した条件が範囲外扱いになる。末尾は wl_max に固定する。
        return [*(self.wl_min_nm + i * step for i in range(self.wl_points - 1)), self.wl_max_nm]


@dataclass(frozen=True)
class Spectrum:
    wavelengths_nm: tuple[float, ...]
    reflectance: tuple[float, ...]
    transmittance: tuple[float, ...]
    reflectance_total: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        n = len(self.wavelengths_nm)
        if len(self.reflectance) != n or len(self.transmittance) != n:
            raise ValueError("wavelengths, reflectance, transmittance must have equal length")
        if self.reflectance_total is not None and len(self.reflectance_total) != n:
            raise ValueError("reflectance_total must have the same length as wavelengths")

    def reflectance_for(self, mode: DiffractionMode) -> tuple[float, ...]:
        if mode is DiffractionMode.ZEROTH:
            return self.reflectance
        if self.reflectance_total is None:
            raise ValueError("spectrum has no total reflectance")
        if mode is DiffractionMode.TOTAL:
            return self.reflectance_total
        return tuple(
            max(total - zeroth, 0.0)
            for total, zeroth in zip(self.reflectance_total, self.reflectance, strict=True)
        )


@dataclass(frozen=True)
class SimulationOutcome:
    spectrum: Spectrum
    reflected_color: ColorResult
    non_zeroth_color: ColorResult | None = None
    total_color: ColorResult | None = None


@dataclass(frozen=True)
class AngleSweepEntry:
    theta_deg: float
    spectrum: Spectrum
    reflected_color: ColorResult | None
    non_zeroth_color: ColorResult | None = None
    total_color: ColorResult | None = None
