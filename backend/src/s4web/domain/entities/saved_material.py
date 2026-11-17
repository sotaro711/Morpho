from dataclasses import dataclass
from datetime import datetime

from s4web.domain.entities.material import DispersiveMaterial

MAX_MATERIAL_NAME_LENGTH = 100

REQUIRED_WAVELENGTH_RANGE_NM = (380.0, 780.0)


def validate_material_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("材料名を入力してください")
    if len(name) > MAX_MATERIAL_NAME_LENGTH:
        raise ValueError(f"材料名は {MAX_MATERIAL_NAME_LENGTH} 文字以内にしてください")
    return name


@dataclass(frozen=True)
class MaterialDraft:
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
    id: str
    name: str
    material: DispersiveMaterial
    created_at: datetime
