"""材料エンティティ（値オブジェクト）。

材料は「波長を与えると複素屈折率 ñ = n + ik を返すもの」として扱う。
波長に依らない定数の Material と、測定値の表を持つ DispersiveMaterial の 2 種類がある。
"""

from bisect import bisect_left
from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    """波長に依らない複素屈折率 ñ = n + ik で定義される材料。

    n: 屈折率の実部（正）
    k: 消衰係数（虚部、非負。0 で無損失）
    """

    n: float
    k: float = 0.0

    def __post_init__(self) -> None:
        if self.n <= 0:
            raise ValueError(f"refractive index n must be positive, got {self.n}")
        if self.k < 0:
            raise ValueError(f"extinction coefficient k must be non-negative, got {self.k}")

    @property
    def refractive_index(self) -> complex:
        """複素屈折率 ñ = n + ik。"""
        return complex(self.n, self.k)

    @property
    def wavelength_range_nm(self) -> None:
        """定数の材料はどの波長でも使えるので範囲を持たない。"""
        return None

    def refractive_index_at(self, wavelength_nm: float) -> complex:
        return self.refractive_index


# 1 材料あたりの測定点の上限。エリプソメータの出力（例: 300〜900 nm を 1 nm 刻みで 601 点）に
# 十分な余裕を持たせつつ、リクエストや保存データが際限なく大きくならないようにする。
MAX_DISPERSION_POINTS = 5000


@dataclass(frozen=True)
class DispersionPoint:
    """ある波長での光学定数の測定値。"""

    wavelength_nm: float
    n: float
    k: float = 0.0

    def __post_init__(self) -> None:
        if self.wavelength_nm <= 0:
            raise ValueError(f"wavelength must be positive, got {self.wavelength_nm}")
        if self.n <= 0:
            raise ValueError(f"refractive index n must be positive, got {self.n}")
        if self.k < 0:
            raise ValueError(f"extinction coefficient k must be non-negative, got {self.k}")


@dataclass(frozen=True)
class DispersiveMaterial:
    """波長ごとの n, k の表（波長分散）で定義される材料。

    測定点の間は n と k をそれぞれ線形補間する。測定範囲の外は外挿せず、
    計算条件の段階で範囲外の波長を拒否する（SimulationCondition を参照）。
    """

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
        """測定されている波長の範囲 (最小, 最大)。"""
        return self.points[0].wavelength_nm, self.points[-1].wavelength_nm

    def refractive_index_at(self, wavelength_nm: float) -> complex:
        """指定波長の複素屈折率。

        範囲外は端の値を返す。計算条件は範囲内の波長しか通さないので、これが効くのは
        ソルバーが Rayleigh 点を避けるために波長を 1 nm 未満ずらした場合だけ。
        """
        first, last = self.points[0], self.points[-1]
        if wavelength_nm <= first.wavelength_nm:
            return complex(first.n, first.k)
        if wavelength_nm >= last.wavelength_nm:
            return complex(last.n, last.k)
        i = bisect_left(self.points, wavelength_nm, key=lambda p: p.wavelength_nm)
        lo, hi = self.points[i - 1], self.points[i]
        t = (wavelength_nm - lo.wavelength_nm) / (hi.wavelength_nm - lo.wavelength_nm)
        return complex(lo.n + t * (hi.n - lo.n), lo.k + t * (hi.k - lo.k))


# 層や領域が持てる材料。
OpticalMaterial = Material | DispersiveMaterial
