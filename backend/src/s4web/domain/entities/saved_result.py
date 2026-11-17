from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from s4web.domain.entities.material import DispersiveMaterial

Json = Mapping[str, Any]


def referenced_material_ids(request: Json) -> set[str]:
    return {
        str(material_id)
        for layer in request.get("layers", [])
        for material_id in (
            layer.get("materialId"),
            *(region.get("materialId") for region in layer.get("regions", [])),
        )
        if material_id is not None
    }


class MissingMaterialError(ValueError): ...


@dataclass(frozen=True)
class ResultDraft:
    request: Json
    materials: Mapping[str, DispersiveMaterial]
    colors: Json
    angles: Json

    def __post_init__(self) -> None:
        missing = referenced_material_ids(self.request) - set(self.materials)
        if missing:
            raise MissingMaterialError(
                f"参照している材料のデータがありません: {', '.join(sorted(missing))}"
            )

    def summary_colors(self) -> tuple[Json, ...]:
        return tuple(
            {"thetaDeg": entry["thetaDeg"], "color": entry["color"]}
            for entry in self.colors.get("entries", [])
            if entry.get("color") is not None
        )


@dataclass(frozen=True)
class SavedResult:
    id: str
    draft: ResultDraft
    created_at: datetime

    def summary(self) -> ResultSummary:
        return ResultSummary(self.id, self.created_at, self.draft.summary_colors())


@dataclass(frozen=True)
class ResultSummary:
    id: str
    created_at: datetime
    colors: tuple[Json, ...]
