"""ユーザーが保存する計算結果。

計算条件と結果は API の JSON（camelCase）のまま持つ。画面に読み込み直して再計算できるよう、
条件はリクエストの形を崩さない。保存先は中身を解釈せず、そのまま書き込んで返す。
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from s4web.domain.entities.material import DispersiveMaterial

# 計算結果の型として、presantation層にSweepResponseがあるが、domainからpresantation層に依存させないようにしている（依存の向きが逆になってしまう）
# 二重管理にもなってしまう
Json = Mapping[str, Any]


# フロントから届いたJSONを辞書 -> その中からmaterualIdを集めている
def referenced_material_ids(request: Json) -> set[str]:
    """リクエストの層・領域が参照している材料の id。"""
    return {
        str(material_id)
        for layer in request.get("layers", [])
        for material_id in (
            layer.get("materialId"),
            *(region.get("materialId") for region in layer.get("regions", [])),
        )
        if material_id is not None
    }


@dataclass(frozen=True)
class ResultDraft:
    """これから保存する計算結果。

    request: 計算条件（SimulationRequest の JSON）
    materials: request が参照する材料の、保存時点のデータ。キーは材料の id。
        材料はあとで編集・削除されうるので、id だけでは何で計算したか分からなくなる。
    colors / angles: 色スイープ・角度スイープの結果（SweepResponse の JSON）
    """

    request: Json
    materials: Mapping[str, DispersiveMaterial]
    colors: Json
    angles: Json

    def __post_init__(self) -> None:
        missing = referenced_material_ids(self.request) - set(self.materials)
        if missing:
            raise ValueError(f"参照している材料のデータがありません: {', '.join(sorted(missing))}")


@dataclass(frozen=True)
class SavedResult:
    """保存済みの計算結果。id は保存先が振る。"""

    id: str
    draft: ResultDraft
    created_at: datetime
