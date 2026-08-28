"""シミュレーション条件と結果スペクトルのエンティティ。"""

from dataclasses import dataclass
from enum import StrEnum

from s4web.domain.entities.color import ColorResult
from s4web.domain.entities.layer import Layer


class Polarization(StrEnum):
    """偏光。S=TE、P=TM。"""

    S = "s"
    P = "p"


# 基底数の上限。GUI の最大回折次数 ±30（2*30+1 = 61）に対応する。
# これ以上は計算時間（基底数のほぼ 3 乗）が実用範囲を超えるため受け付けない。
NUM_BASIS_LIMIT = 61


@dataclass(frozen=True)
class SimulationCondition:
    """多層膜シミュレーションの完全な指定。

    波長はすべて nm。層は入射側から基板側の順。
    ここを通過したインスタンスは「物理的に計算可能」であることが保証される。

    面内パターン（Layer.regions）を持つ層がある場合は面内周期 period_nm が
    必須になる。平面多層膜（パターンなし）では period_nm は不要で、
    num_basis=1 が厳密（回折は 0 次のみ）。

    波長は通常 [wl_min_nm, wl_max_nm] の等間隔 wl_points 点。等間隔で表せない
    サンプル（参照データとの突き合わせなど）は explicit_wavelengths_nm で
    明示リストを与える。指定時は wl_min/wl_max/wl_points を使わない。
    """

    wl_min_nm: float
    wl_max_nm: float
    wl_points: int
    theta_deg: float
    polarization: Polarization
    layers: tuple[Layer, ...]
    period_nm: float | None = None
    num_basis: int = 1
    explicit_wavelengths_nm: tuple[float, ...] | None = None

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
            raise ValueError(
                f"num_basis must be in [1, {NUM_BASIS_LIMIT}], got {self.num_basis}"
            )
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
        patterned = [layer for layer in self.layers if layer.is_patterned]
        if patterned:
            if self.period_nm is None:
                names = ", ".join(layer.name for layer in patterned)
                raise ValueError(f"period_nm is required for patterned layers ({names})")
            for layer in patterned:
                for region in layer.regions:
                    if region.end_nm > self.period_nm:
                        raise ValueError(
                            f"region [{region.x_nm}, {region.end_nm}) in layer "
                            f"'{layer.name}' exceeds period_nm={self.period_nm}"
                        )

    @property
    def is_patterned(self) -> bool:
        """面内パターンを持つ層を含むかどうか。"""
        return any(layer.is_patterned for layer in self.layers)

    def wavelengths_nm(self) -> list[float]:
        """計算する波長のリスト。

        explicit_wavelengths_nm があればそれをそのまま、無ければ
        [wl_min, wl_max] を wl_points 点で等間隔サンプルして返す。
        """
        if self.explicit_wavelengths_nm is not None:
            return list(self.explicit_wavelengths_nm)
        if self.wl_points == 1:
            return [self.wl_min_nm]
        step = (self.wl_max_nm - self.wl_min_nm) / (self.wl_points - 1)
        return [self.wl_min_nm + i * step for i in range(self.wl_points)]


@dataclass(frozen=True)
class Spectrum:
    """反射率 / 透過率スペクトル。各配列は波長ごとに 1 値。

    反射率・透過率は回折 0 次（正反射・直進透過）の成分。面内パターンを持つ
    構造では高次回折光は含まない（観測者が正反射方向で見る量に合わせる）。
    平面多層膜では回折が無いので全反射率と同じ。
    """

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


@dataclass(frozen=True)
class AngleSweepEntry:
    """入射角スイープの 1 角度分の結果。

    reflected_color は色変換を省略した場合（波長間隔が色変換に適さない粗い
    掃引など）に None になる。
    """

    theta_deg: float
    spectrum: Spectrum
    reflected_color: ColorResult | None
