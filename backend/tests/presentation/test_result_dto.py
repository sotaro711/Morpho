from datetime import UTC, datetime

from s4web.domain.entities.saved_result import ResultDraft, SavedResult
from s4web.presentation.schemas.result_dto import (
    ResultCreateRequest,
    ResultDTO,
    ResultSummaryDTO,
)

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
