import pytest
from pydantic import ValidationError

from s4web.domain.entities.layer import CircleRegion, RectRegion, Region
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


def test_region_without_shape_is_a_stripe() -> None:
    # 1D 格子の従来 JSON（shape なし）はそのまま受け付ける。
    request = _request(
        layers=[
            {"name": "air", "thicknessNm": 0, "n": 1.0},
            {
                "name": "g",
                "thicknessNm": 100,
                "n": 1.0,
                "regions": [{"xNm": 0, "widthNm": 200, "n": 2.3}],
            },
            {"name": "sub", "thicknessNm": 0, "n": 1.5},
        ],
        periodNm=400,
        numBasis=5,
    )
    condition = request.to_condition({})
    assert condition.layers[1].regions == (Region(Material(2.3), 0, 200),)
    assert not condition.is_biperiodic


def test_rect_and_circle_regions_with_period_y() -> None:
    request = _request(
        layers=[
            {"name": "air", "thicknessNm": 0, "n": 1.0},
            {
                "name": "pillar",
                "thicknessNm": 100,
                "n": 1.0,
                "regions": [
                    {
                        "shape": "rect",
                        "cxNm": 300,
                        "cyNm": 300,
                        "widthNm": 300,
                        "heightNm": 300,
                        "n": 2.3,
                    }
                ],
            },
            {
                "name": "slice",
                "thicknessNm": 10,
                "n": 1.0,
                "regions": [
                    {
                        "shape": "circle",
                        "cxNm": 300,
                        "cyNm": 300,
                        "radiusNm": 60,
                        "materialId": MATERIAL_ID,
                    }
                ],
            },
            {"name": "sub", "thicknessNm": 0, "n": 1.5},
        ],
        periodNm=600,
        periodYNm=600,
        numBasis=81,
    )
    assert request.material_ids() == {MATERIAL_ID}
    condition = request.to_condition({MATERIAL_ID: MEASURED})
    assert condition.is_biperiodic
    assert condition.layers[1].regions == (RectRegion(Material(2.3), 300, 300, 300, 300),)
    assert condition.layers[2].regions == (CircleRegion(MEASURED, 300, 300, 60),)


def test_region_with_unknown_shape_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _request(
            layers=[
                {"name": "air", "thicknessNm": 0, "n": 1.0},
                {
                    "name": "g",
                    "thicknessNm": 100,
                    "n": 1.0,
                    "regions": [{"shape": "hexagon", "cxNm": 0, "cyNm": 0, "radiusNm": 10}],
                },
                {"name": "sub", "thicknessNm": 0, "n": 1.5},
            ],
            periodNm=400,
            periodYNm=400,
        )


def test_phi_deg_becomes_the_azimuth() -> None:
    request = _request(
        layers=[
            {"name": "air", "thicknessNm": 0, "n": 1.0},
            {
                "name": "slice",
                "thicknessNm": 10,
                "n": 1.0,
                "regions": [{"shape": "circle", "cxNm": 80, "cyNm": 80, "radiusNm": 60, "n": 4.0}],
            },
            {"name": "sub", "thicknessNm": 0, "n": 1.5},
        ],
        periodNm=160,
        periodYNm=160,
        numBasis=9,
        phiDeg=90,
    )
    assert request.to_condition({}).azimuth_deg == 90.0


def test_num_basis_up_to_the_domain_limit_is_accepted() -> None:
    assert _request(numBasis=225).num_basis == 225
    with pytest.raises(ValidationError):
        _request(numBasis=226)
