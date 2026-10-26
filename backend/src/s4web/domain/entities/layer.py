"""層エンティティ。"""

import math
from dataclasses import dataclass

from s4web.domain.entities.material import OpticalMaterial


@dataclass(frozen=True)
class Region:
    """層の中の矩形領域（面内パターンの構成要素）。

    層の背景材料の上に、単位胞内の区間 [x_nm, x_nm + width_nm) を
    この領域の材料で置き換える。位置は単位胞の左端を 0 とする nm 座標。
    x 方向にだけ周期を持つ 1D 格子向け（y 方向には単位胞いっぱいに伸びる）。
    """

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
        """領域の右端位置。"""
        return self.x_nm + self.width_nm


@dataclass(frozen=True)
class CircleRegion:
    """層の中の円形領域（x, y の 2 方向に周期を持つ構造向け）。

    層の背景材料の上に、中心 (cx_nm, cy_nm)・半径 radius_nm の円を
    この領域の材料で置き換える。座標は単位胞の左下隅を原点とする nm。
    球や円柱を輪切りにした各層はこの領域 1 つで表す。
    """

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
    """層の中の矩形領域（x, y の 2 方向に周期を持つ構造向け）。

    層の背景材料の上に、中心 (cx_nm, cy_nm)・幅 width_nm（x）・高さ height_nm（y）の
    矩形をこの領域の材料で置き換える。座標は単位胞の左下隅を原点とする nm。
    角柱やその上に成膜した多層膜を輪切りにした各層はこの領域 1 つで表す。
    x 方向だけの区間で y 方向に単位胞いっぱいに伸びる 1D 格子用は Region。
    """

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


# x, y の 2 方向に周期を持つ構造の領域。層に含まれていれば period_y_nm が必要になる。
Region2D = CircleRegion | RectRegion


@dataclass(frozen=True)
class Layer:
    """スタック中の 1 層。

    厚さは nm。最初（入射側）と最後（基板側）の層は半無限媒質を表すため、
    通常は厚さ 0 で指定する。

    regions が空なら面内一様な層（従来どおり）。regions を持つ層は、
    material を背景として領域を重ねた面内パターンを表す。領域は 1D 格子用の
    区間（Region）か、2 方向周期用の円・矩形（CircleRegion / RectRegion）で、
    1 つの層には同じ種類の領域だけを置ける（重なりの検証を単純に保つため）。
    パターン層を含む条件は SimulationCondition の period_nm（2 方向周期用の
    領域があれば period_y_nm も）が必須になる（領域と周期の整合はそちらで検証する）。
    """

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
        shapes = [r for r in self.regions if not isinstance(r, Region)]
        for i, a in enumerate(shapes):
            for b in shapes[i + 1 :]:
                # 種類は揃っているので、円どうし・矩形どうしの判定になる。
                if a.overlaps(b):  # type: ignore[arg-type]
                    raise ValueError(
                        f"regions in layer '{self.name}' must not overlap: {a} and {b}"
                    )

    @property
    def is_patterned(self) -> bool:
        """面内パターンを持つ層かどうか。"""
        return len(self.regions) > 0

    @property
    def has_2d_regions(self) -> bool:
        """円・矩形（2 方向周期用）の領域を持つ層かどうか。period_y_nm が必要になる。"""
        return any(not isinstance(r, Region) for r in self.regions)
