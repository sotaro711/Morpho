"""ユーザーが登録して保存する材料。"""

from dataclasses import dataclass
from datetime import datetime

from s4web.domain.entities.material import DispersiveMaterial

MAX_MATERIAL_NAME_LENGTH = 100

# 登録する材料が必ず含んでいなければならない波長範囲（nm）。
# 画面の計算は色・スペクトルに 380〜780 nm を使うので、これを含まない材料は
# 登録しても計算に使えない。計算のたびに失敗させるより、登録時に案内する。
REQUIRED_WAVELENGTH_RANGE_NM = (380.0, 780.0)


def validate_material_name(name: str) -> str:
    """材料名を検証し、前後の空白を除いた名前を返す。"""
    name = name.strip()
    if not name:
        raise ValueError("材料名を入力してください")
    if len(name) > MAX_MATERIAL_NAME_LENGTH:
        raise ValueError(f"材料名は {MAX_MATERIAL_NAME_LENGTH} 文字以内にしてください")
    return name


@dataclass(frozen=True)
class MaterialDraft:
    """これから保存する材料。名前と波長範囲を検証済みであることを保証する。"""

    name: str
    material: DispersiveMaterial

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", validate_material_name(self.name))
        lo, hi = self.material.wavelength_range_nm
        req_lo, req_hi = REQUIRED_WAVELENGTH_RANGE_NM
        if lo > req_lo or hi < req_hi:
            raise ValueError(
                f"データの波長範囲（{lo:g}〜{hi:g} nm）が、計算に必要な "
                f"{req_lo:g}〜{req_hi:g} nm を含んでいません"
            )


@dataclass(frozen=True)
class SavedMaterial:
    """保存済みの材料。id は保存先が振る。"""

    id: str
    name: str
    material: DispersiveMaterial
    created_at: datetime
