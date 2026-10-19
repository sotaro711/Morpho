from datetime import UTC, datetime

from s4web.domain.entities.saved_result import ResultDraft, SavedResult, referenced_material_ids
from s4web.presentation.schemas.result_dto import (
    ResultCreateRequest,
    ResultDTO,
    ResultSummaryDTO,
)
from s4web.presentation.schemas.simulation_dto import SimulationRequest

_SWEEP = {
    "wavelengths": [380.0, 390.0],
    "entries": [
        {
            "thetaDeg": 0,
            "R": [0.1, 0.2],
            "T": [0.9, 0.8],
            "color": {"r": 1, "g": 2, "b": 3, "hex": "#010203"},
        },
        {"thetaDeg": 30, "R": [0.1, 0.2], "T": [0.9, 0.8]},
    ],
}
_BODY = {
    "request": {
        "wlMin": 380,
        "wlMax": 780,
        "wlPoints": 41,
        "layers": [
            {"name": "air", "thicknessNm": 0, "n": 1},
            {"name": "sub", "thicknessNm": 0, "n": 1.5},
        ],
    },
    "colors": _SWEEP,
    "angles": _SWEEP,
}


def _saved() -> SavedResult:
    request, colors, angles = ResultCreateRequest.model_validate(_BODY).to_json()
    draft = ResultDraft(request=request, materials={}, colors=colors, angles=angles)
    return SavedResult("r1", draft, datetime(2026, 10, 19, tzinfo=UTC))


def test_saved_json_keeps_the_api_shape() -> None:
    request, colors, _ = ResultCreateRequest.model_validate(_BODY).to_json()
    assert request["wlMin"] == 380
    assert colors["entries"][0]["thetaDeg"] == 0


def test_detail_reads_back_what_was_saved() -> None:
    dto = ResultDTO.from_entity(_saved())
    assert dto.colors.entries[1].theta_deg == 30
    assert dto.request.layers[1].n == 1.5


def test_summary_lists_only_entries_with_colors() -> None:
    dto = ResultSummaryDTO.from_entity(_saved())
    assert [(c.theta_deg, c.color.hex) for c in dto.colors] == [(0, "#010203")]


def test_referenced_material_ids_matches_simulation_request() -> None:
    # domain は presentation に依存できないので同じ処理を 2 か所に持っている。食い違うと
    # 計算に使った材料が保存されないので、同じ request で結果がそろうことを確かめる。
    id_a = "0f6d1a4e-6d8e-4d1c-9a3b-2c5f7e8a9b01"
    id_b = "0f6d1a4e-6d8e-4d1c-9a3b-2c5f7e8a9b02"
    id_c = "0f6d1a4e-6d8e-4d1c-9a3b-2c5f7e8a9b03"
    body = {
        "wlMin": 380,
        "wlMax": 780,
        "wlPoints": 41,
        "layers": [
            {"name": "air", "thicknessNm": 0, "n": 1},
            {
                "name": "grating",
                "thicknessNm": 100,
                "materialId": id_a,
                "regions": [
                    {"xNm": 0, "widthNm": 100, "materialId": id_b},
                    {"xNm": 100, "widthNm": 100, "n": 1.5},
                ],
            },
            {"name": "sub", "thicknessNm": 0, "materialId": id_c},
        ],
    }
    request = SimulationRequest.model_validate(body)
    dumped = request.model_dump(mode="json", by_alias=True)
    assert referenced_material_ids(dumped) == request.material_ids() == {id_a, id_b, id_c}
