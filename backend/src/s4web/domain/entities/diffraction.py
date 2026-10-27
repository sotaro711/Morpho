"""回折次数ごとの出力（角度分布）のエンティティ。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DiffractionOrder:
    """1 つの回折次数への反射パワーの配分。

    order: x 方向の回折次数 m（0 が正反射方向。格子方程式 sinθ_m = sinθ_in + mλ/L）
    angle_deg: 出射角（法線から測った角度。1D 格子では負は入射側と反対方向）
    reflectance: 入射パワーで規格化した反射パワー R_m
    order_y: y 方向の回折次数 n（1D 格子では常に 0）
    azimuth_deg: 出射方向の方位角（x 軸から。1D 格子では 0 で、向きは angle_deg の符号）。
        x, y の 2 方向に周期を持つ格子では angle_deg は極角（≥ 0）になる。
    """

    order: int
    angle_deg: float
    reflectance: float
    order_y: int = 0
    azimuth_deg: float = 0.0


@dataclass(frozen=True)
class AngularDistribution:
    """1 波長における反射光の角度分布。

    伝搬する（遠方まで届く）回折次数のみを持ち、出射角の昇順に並ぶ。
    数値異常から回復できなかった波長では orders が空になる。
    """

    wavelength_nm: float
    orders: tuple[DiffractionOrder, ...]
