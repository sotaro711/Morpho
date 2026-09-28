"""材料 API の入出力 DTO。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from s4web.domain.entities.saved_material import MAX_MATERIAL_NAME_LENGTH, SavedMaterial

# アップロードされるファイルの上限（文字数）。601 点のファイルで約 21 KB なので十分な余裕がある。
MAX_FILE_CHARS = 1_048_576


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MaterialSummaryDTO(BaseModel):
    """一覧用。層の材料選択に必要なのは id と名前だけ。"""

    id: str
    name: str

    @classmethod
    def from_entity(cls, saved: SavedMaterial) -> MaterialSummaryDTO:
        return cls(id=saved.id, name=saved.name)


class DispersionPointDTO(_CamelModel):
    wavelength_nm: float
    n: float
    k: float


class MaterialDTO(_CamelModel):
    """詳細用。n, k の表を含む（グラフ表示に使う）。"""

    id: str
    name: str
    points: list[DispersionPointDTO]
    created_at: datetime

    @classmethod
    def from_entity(cls, saved: SavedMaterial) -> MaterialDTO:
        return cls(
            id=saved.id,
            name=saved.name,
            points=[
                DispersionPointDTO(wavelength_nm=p.wavelength_nm, n=p.n, k=p.k)
                for p in saved.material.points
            ],
            created_at=saved.created_at,
        )


class MaterialCreateRequest(_CamelModel):
    """材料の登録。content はファイルの中身の文字列（読み取りはバックエンドで行う）。"""

    name: str = Field(max_length=MAX_MATERIAL_NAME_LENGTH)
    content: str = Field(max_length=MAX_FILE_CHARS)


class MaterialRenameRequest(_CamelModel):
    name: str = Field(max_length=MAX_MATERIAL_NAME_LENGTH)
