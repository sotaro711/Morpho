"""層エンティティ。"""

from dataclasses import dataclass

from s4web.domain.entities.material import Material


@dataclass(frozen=True)
class Region:
    """層の中の矩形領域（面内パターンの構成要素）。

    層の背景材料の上に、単位胞内の区間 [x_nm, x_nm + width_nm) を
    この領域の材料で置き換える。位置は単位胞の左端を 0 とする nm 座標。
    面内は 1 次元（x 方向のみ）を対象とする。
    """

    material: Material
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
class Layer:
    """スタック中の 1 層。

    厚さは nm。最初（入射側）と最後（基板側）の層は半無限媒質を表すため、
    通常は厚さ 0 で指定する。

    regions が空なら面内一様な層（従来どおり）。regions を持つ層は、
    material を背景として矩形領域を重ねた面内パターンを表す。
    パターン層を含む条件は SimulationCondition の period_nm が必須になる
    （領域と周期の整合はそちらで検証する）。
    """

    name: str
    thickness_nm: float
    material: Material
    regions: tuple[Region, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("layer name must not be empty")
        if self.thickness_nm < 0:
            raise ValueError(f"thickness_nm must be non-negative, got {self.thickness_nm}")
        ordered = sorted(self.regions, key=lambda r: r.x_nm)
        for prev, nxt in zip(ordered, ordered[1:], strict=False):
            if nxt.x_nm < prev.end_nm:
                raise ValueError(
                    f"regions in layer '{self.name}' must not overlap: "
                    f"[{prev.x_nm}, {prev.end_nm}) and [{nxt.x_nm}, {nxt.end_nm})"
                )

    @property
    def is_patterned(self) -> bool:
        """面内パターンを持つ層かどうか。"""
        return len(self.regions) > 0
