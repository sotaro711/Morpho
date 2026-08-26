"""材料エンティティ（値オブジェクト）。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    """複素屈折率 ñ = n + ik で定義される材料。

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
