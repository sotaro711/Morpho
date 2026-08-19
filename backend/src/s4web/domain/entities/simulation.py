"""シミュレーション条件と結果スペクトルのエンティティ。"""

from dataclasses import dataclass
from enum import StrEnum

from s4web.domain.entities.color import ColorResult
from s4web.domain.entities.layer import Layer


class Polarization(StrEnum):
    """偏光。S=TE、P=TM。"""

    S = "s"
    P = "p"


@dataclass(frozen=True)
class SimulationCondition:
    """平面多層膜シミュレーションの完全な指定。

    波長はすべて nm。層は入射側から基板側の順。
    ここを通過したインスタンスは「物理的に計算可能」であることが保証される。
    """

    wl_min_nm: float
    wl_max_nm: float
    wl_points: int
    theta_deg: float
    polarization: Polarization
    layers: tuple[Layer, ...]

    def __post_init__(self) -> None:
        if self.wl_min_nm <= 0 or self.wl_max_nm <= 0:
            raise ValueError("wavelengths must be positive")
        if self.wl_min_nm > self.wl_max_nm:
            raise ValueError("wl_min_nm must be <= wl_max_nm")
        if self.wl_points < 1:
            raise ValueError("wl_points must be >= 1")
        if self.wl_points == 1 and self.wl_min_nm != self.wl_max_nm:
            raise ValueError("wl_points == 1 requires wl_min_nm == wl_max_nm")
        if not (0.0 <= self.theta_deg < 90.0):
            raise ValueError("theta_deg must be in [0, 90)")
        if len(self.layers) < 2:
            raise ValueError("at least two layers are required (incident + substrate)")

    def wavelengths_nm(self) -> list[float]:
        """[wl_min, wl_max] を wl_points 点で等間隔サンプルした波長リスト。"""
        if self.wl_points == 1:
            return [self.wl_min_nm]
        step = (self.wl_max_nm - self.wl_min_nm) / (self.wl_points - 1)
        return [self.wl_min_nm + i * step for i in range(self.wl_points)]


@dataclass(frozen=True)
class Spectrum:
    """反射率 / 透過率スペクトル。各配列は波長ごとに 1 値。"""

    wavelengths_nm: tuple[float, ...]
    reflectance: tuple[float, ...]
    transmittance: tuple[float, ...]

    def __post_init__(self) -> None:
        n = len(self.wavelengths_nm)
        if len(self.reflectance) != n or len(self.transmittance) != n:
            raise ValueError("wavelengths, reflectance, transmittance must have equal length")


@dataclass(frozen=True)
class SimulationOutcome:
    """シミュレーション結果一式（スペクトル + 反射色）。"""

    spectrum: Spectrum
    reflected_color: ColorResult
