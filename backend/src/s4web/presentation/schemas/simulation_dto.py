"""API の入出力 DTO（Pydantic）と domain エンティティへの変換。

JSON は camelCase（TypeScript フロントの慣習）、Python 側は snake_case。
alias_generator でこのギャップを吸収する。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from s4web.domain.entities.color import ColorResult
from s4web.domain.entities.diffraction import AngularDistribution
from s4web.domain.entities.layer import Layer, Region
from s4web.domain.entities.material import Material
from s4web.domain.entities.simulation import (
    Polarization,
    SimulationCondition,
    SimulationOutcome,
)


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RegionDTO(_CamelModel):
    """層内の矩形領域（面内パターン）。単位胞左端を 0 とする nm 座標。"""

    x_nm: float
    width_nm: float
    n: float
    k: float = 0.0

    def to_entity(self) -> Region:
        return Region(
            material=Material(n=self.n, k=self.k),
            x_nm=self.x_nm,
            width_nm=self.width_nm,
        )


class LayerDTO(_CamelModel):
    name: str
    thickness_nm: float
    n: float
    k: float = 0.0
    regions: list[RegionDTO] = []

    def to_entity(self) -> Layer:
        return Layer(
            name=self.name,
            thickness_nm=self.thickness_nm,
            material=Material(n=self.n, k=self.k),
            regions=tuple(region.to_entity() for region in self.regions),
        )


class SimulationRequest(_CamelModel):
    wl_min: float = Field(gt=0)
    wl_max: float = Field(gt=0)
    wl_points: int = Field(ge=1)
    theta_deg: float = 0.0
    pol: Polarization = Polarization.S
    layers: list[LayerDTO] = Field(min_length=2)
    # 面内パターンを使う場合のみ指定する（平面多層膜では省略 = 従来どおり）。
    period_nm: float | None = None
    num_basis: int = Field(ge=1, default=1)

    def to_condition(self) -> SimulationCondition:
        return SimulationCondition(
            wl_min_nm=self.wl_min,
            wl_max_nm=self.wl_max,
            wl_points=self.wl_points,
            theta_deg=self.theta_deg,
            polarization=self.pol,
            layers=tuple(layer.to_entity() for layer in self.layers),
            period_nm=self.period_nm,
            num_basis=self.num_basis,
        )


class ColorDTO(BaseModel):
    r: int
    g: int
    b: int
    hex: str

    @classmethod
    def from_color(cls, c: ColorResult) -> ColorDTO:
        return cls(r=c.r, g=c.g, b=c.b, hex=c.hex)


class DiffractionOrderDTO(_CamelModel):
    """1 つの回折次数への反射パワーの配分。"""

    order: int
    angle_deg: float
    reflectance: float


class AngularDistributionDTO(_CamelModel):
    """1 波長の角度分布。orders は出射角の昇順（伝搬する次数のみ）。"""

    wavelength_nm: float
    orders: list[DiffractionOrderDTO]


class OrdersResponse(BaseModel):
    distributions: list[AngularDistributionDTO]

    @classmethod
    def from_distributions(cls, distributions: tuple[AngularDistribution, ...]) -> OrdersResponse:
        return cls(
            distributions=[
                AngularDistributionDTO(
                    wavelength_nm=d.wavelength_nm,
                    orders=[
                        DiffractionOrderDTO(
                            order=o.order,
                            angle_deg=o.angle_deg,
                            reflectance=o.reflectance,
                        )
                        for o in d.orders
                    ],
                )
                for d in distributions
            ]
        )


class SimulationResponse(BaseModel):
    # フロントのグラフがそのまま使えるよう、キーは wavelengths / R / T。
    wavelengths: list[float]
    R: list[float]
    T: list[float]
    reflected_color: ColorDTO = Field(serialization_alias="reflectedColor")

    @classmethod
    def from_outcome(cls, outcome: SimulationOutcome) -> SimulationResponse:
        return cls(
            wavelengths=list(outcome.spectrum.wavelengths_nm),
            R=list(outcome.spectrum.reflectance),
            T=list(outcome.spectrum.transmittance),
            reflected_color=ColorDTO.from_color(outcome.reflected_color),
        )
