"""回折次数ごとの出力（角度分布）のエンティティ。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DiffractionOrder:
    """1 つの回折次数への反射パワーの配分。

    order: 回折次数 m（0 が正反射方向。格子方程式 sinθ_m = sinθ_in + mλ/L）
    angle_deg: 出射角（法線から測った角度。負は入射側と反対方向）
    reflectance: 入射パワーで規格化した反射パワー R_m
    """

    order: int
    angle_deg: float
    reflectance: float


@dataclass(frozen=True)
class AngularDistribution:
    """1 波長における反射光の角度分布。

    伝搬する（遠方まで届く）回折次数のみを持ち、出射角の昇順に並ぶ。
    数値異常から回復できなかった波長では orders が空になる。
    """

    wavelength_nm: float
    orders: tuple[DiffractionOrder, ...]
