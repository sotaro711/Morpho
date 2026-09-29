import pytest
from pydantic import ValidationError

from s4web.domain.entities.material import DispersionPoint, DispersiveMaterial, Material
from s4web.presentation.schemas.simulation_dto import SimulationRequest

MATERIAL_ID = "0f6d1a4e-6d8e-4d1c-9a3b-2c5f7e8a9b01"
MEASURED = DispersiveMaterial((DispersionPoint(380, 2.5, 0.1), DispersionPoint(780, 2.2)))


def _request(**overrides: object) -> SimulationRequest:
    body: dict[str, object] = {
        "wlMin": 380,
        "wlMax": 780,
        "wlPoints": 41,
        "layers": [
            {"name": "air", "thicknessNm": 0, "n": 1.0},
            {"name": "film", "thicknessNm": 100, "n": 2.3},
            {"name": "sub", "thicknessNm": 0, "n": 1.71, "k": 2.88},
        ],
    }
    body.update(overrides)
    return SimulationRequest.model_validate(body)


def test_request_without_material_ids_uses_constant_materials() -> None:
    request = _request()
    assert request.material_ids() == set()
    condition = request.to_condition({})
    assert condition.layers[1].material == Material(2.3)
    assert not condition.is_dispersive


def test_material_id_resolves_to_the_registered_material_for_layers_and_regions() -> None:
    request = _request(
        layers=[
            {"name": "air", "thicknessNm": 0, "n": 1.0},
            {
                "name": "grating",
                "thicknessNm": 100,
                "n": 1.0,
                "regions": [{"xNm": 0, "widthNm": 200, "materialId": MATERIAL_ID}],
            },
            {"name": "film", "thicknessNm": 100, "materialId": MATERIAL_ID},
            {"name": "sub", "thicknessNm": 0, "n": 1.71, "k": 2.88},
        ],
        periodNm=400,
        numBasis=5,
    )
    assert request.material_ids() == {MATERIAL_ID}
    condition = request.to_condition({MATERIAL_ID: MEASURED})
    assert condition.layers[2].material is MEASURED
    assert condition.layers[1].regions[0].material is MEASURED


def test_unknown_material_id_is_rejected() -> None:
    request = _request(
        layers=[
            {"name": "air", "thicknessNm": 0, "n": 1.0},
            {"name": "sub", "thicknessNm": 0, "materialId": MATERIAL_ID},
        ]
    )
    with pytest.raises(ValueError, match="選択した材料が見つかりません"):
        request.to_condition({})


def test_material_id_must_be_a_uuid() -> None:
    # UUID でない id をそのまま DB に渡すと Postgres の型エラー（500）になるので、入口で弾く。
    with pytest.raises(ValidationError):
        _request(
            layers=[
                {"name": "air", "thicknessNm": 0, "n": 1.0},
                {"name": "sub", "thicknessNm": 0, "materialId": "missing"},
            ]
        )


def test_layer_without_n_or_material_id_is_rejected() -> None:
    request = _request(
        layers=[
            {"name": "air", "thicknessNm": 0, "n": 1.0},
            {"name": "sub", "thicknessNm": 0},
        ]
    )
    with pytest.raises(ValueError, match="materialId"):
        request.to_condition({})
