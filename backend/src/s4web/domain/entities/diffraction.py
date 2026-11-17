from dataclasses import dataclass


@dataclass(frozen=True)
class DiffractionOrder:
    order: int
    angle_deg: float
    reflectance: float
    order_y: int = 0
    azimuth_deg: float = 0.0


@dataclass(frozen=True)
class AngularDistribution:
    wavelength_nm: float
    orders: tuple[DiffractionOrder, ...]
