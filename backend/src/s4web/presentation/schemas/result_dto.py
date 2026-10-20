"""保存した計算結果 API の入出力 DTO。

条件と結果は計算 API の DTO で検証してから保存する。保存先は JSON をそのまま持つので、
読み出すときも同じ DTO に通せば計算 API のレスポンスと同じ形で返せる。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from s4web.domain.entities.saved_result import ResultSummary, SavedResult
from s4web.presentation.schemas.material_dto import DispersionPointDTO
from s4web.presentation.schemas.simulation_dto import (
    ColorDTO,
    SimulationRequest,
    SweepResponse,
)


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


def _dump(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json", by_alias=True)


class ResultCreateRequest(_CamelModel):
    """保存する結果。request は計算条件、colors / angles は 2 つの sweep のレスポンス。"""

    request: SimulationRequest
    colors: SweepResponse
    angles: SweepResponse

    def to_json(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        return _dump(self.request), _dump(self.colors), _dump(self.angles)


class ResultColorDTO(_CamelModel):
    """一覧に出す、入射角ごとの反射色。"""

    theta_deg: float
    color: ColorDTO


class ResultSummaryDTO(_CamelModel):
    """一覧用。条件やスペクトルは含めず、日時と色だけを返す。"""

    id: str
    created_at: datetime
    colors: list[ResultColorDTO]

    @classmethod
    def from_entity(cls, summary: ResultSummary) -> ResultSummaryDTO:
        return cls(
            id=summary.id,
            created_at=summary.created_at,
            colors=[ResultColorDTO.model_validate(c) for c in summary.colors],
        )


class ResultDTO(_CamelModel):
    """詳細用。materials は計算時点の材料のデータ（キーは材料の id）。"""

    id: str
    created_at: datetime
    request: SimulationRequest
    materials: dict[str, list[DispersionPointDTO]]
    colors: SweepResponse
    angles: SweepResponse

    @classmethod
    def from_entity(cls, saved: SavedResult) -> ResultDTO:
        draft = saved.draft
        return cls(
            id=saved.id,
            created_at=saved.created_at,
            request=SimulationRequest.model_validate(draft.request),
            materials={
                material_id: [
                    DispersionPointDTO(wavelength_nm=p.wavelength_nm, n=p.n, k=p.k)
                    for p in material.points
                ]
                for material_id, material in draft.materials.items()
            },
            colors=SweepResponse.model_validate(draft.colors),
            angles=SweepResponse.model_validate(draft.angles),
        )
