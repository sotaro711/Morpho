"""S4Solver の分散材料対応。S4 が入っていない環境（CI）ではスキップする。"""

import pytest

pytest.importorskip("S4")

from s4web.domain.entities.layer import Layer, Region  # noqa: E402
from s4web.domain.entities.material import (  # noqa: E402
    DispersionPoint,
    DispersiveMaterial,
    Material,
    OpticalMaterial,
)
from s4web.domain.entities.simulation import Polarization, SimulationCondition  # noqa: E402
from s4web.infrastructure.solvers.s4_solver import S4Solver  # noqa: E402

AIR = Material(1.0)
SIO2 = Material(1.45)
SUS = Material(1.71, 2.88)
# 測定点ちょうどの波長で比べ、補間の誤差が入らないようにする。
WAVELENGTHS = (400.0, 460.0, 520.0, 610.0, 700.0)


def _nk(wl: float) -> tuple[float, float]:
    """TiO2 風の正常分散と、短波長側の吸収。"""
    return 2.2 + 30000 / wl**2, max(0.0, 0.02 * (450 - wl) / 100)


MEASURED = DispersiveMaterial(tuple(DispersionPoint(w, *_nk(w)) for w in range(300, 901)))


def _flat(material: OpticalMaterial, wls: tuple[float, ...]) -> SimulationCondition:
    return SimulationCondition(
        wl_min_nm=min(wls),
        wl_max_nm=max(wls),
        wl_points=len(wls),
        theta_deg=30.0,
        polarization=Polarization.S,
        layers=(
            Layer("air", 0, AIR),
            Layer("a", 51, material),
            Layer("b", 81, SIO2),
            Layer("sub", 0, SUS),
        ),
        explicit_wavelengths_nm=wls,
    )


def _patterned(material: OpticalMaterial, wls: tuple[float, ...]) -> SimulationCondition:
    return SimulationCondition(
        wl_min_nm=min(wls),
        wl_max_nm=max(wls),
        wl_points=len(wls),
        theta_deg=10.0,
        polarization=Polarization.P,
        layers=(
            Layer("air", 0, AIR),
            Layer("grating", 120, AIR, (Region(material, 0, 300),)),
            Layer("film", 60, material),
            Layer("sub", 0, SUS),
        ),
        period_nm=600,
        num_basis=7,
        explicit_wavelengths_nm=wls,
    )


@pytest.fixture(scope="module")
def solver() -> S4Solver:
    return S4Solver()


def test_flat_dispersive_table_matches_the_same_constant_material(solver: S4Solver) -> None:
    constant_table = DispersiveMaterial((DispersionPoint(300, 2.3), DispersionPoint(900, 2.3)))
    got = solver.solve(_flat(constant_table, WAVELENGTHS))
    want = solver.solve(_flat(Material(2.3), WAVELENGTHS))
    assert got.reflectance == want.reflectance
    assert got.transmittance == want.transmittance


@pytest.mark.parametrize("build", [_flat, _patterned], ids=["flat", "patterned"])
def test_dispersive_sweep_matches_per_wavelength_constant_solves(solver: S4Solver, build) -> None:
    sweep = solver.solve(build(MEASURED, WAVELENGTHS))
    for i, wl in enumerate(WAVELENGTHS):
        single = solver.solve(build(Material(*_nk(wl)), (wl,)))
        assert sweep.reflectance[i] == pytest.approx(single.reflectance[0], abs=1e-9)
        assert sweep.transmittance[i] == pytest.approx(single.transmittance[0], abs=1e-9)
        assert sweep.reflectance_total is not None and single.reflectance_total is not None
        assert sweep.reflectance_total[i] == pytest.approx(single.reflectance_total[0], abs=1e-9)


def test_dispersive_orders_match_per_wavelength_constant_solves(solver: S4Solver) -> None:
    sweep = solver.solve_orders(_patterned(MEASURED, WAVELENGTHS))
    for dist, wl in zip(sweep, WAVELENGTHS, strict=True):
        (single,) = solver.solve_orders(_patterned(Material(*_nk(wl)), (wl,)))
        assert [o.order for o in dist.orders] == [o.order for o in single.orders]
        for got, want in zip(dist.orders, single.orders, strict=True):
            assert got.reflectance == pytest.approx(want.reflectance, abs=1e-9)


def test_dispersion_changes_the_result(solver: S4Solver) -> None:
    # 分散が実際に効いていること（同じ n の定数材料とは結果が変わる）。
    dispersive = solver.solve(_flat(MEASURED, WAVELENGTHS)).reflectance
    constant = solver.solve(_flat(Material(2.3), WAVELENGTHS)).reflectance
    assert max(abs(a - b) for a, b in zip(dispersive, constant, strict=True)) > 1e-3
