"""S4Solver の分散材料対応と 2 方向周期の格子。S4 が入っていない環境（CI）ではスキップする。"""

import math

import pytest

pytest.importorskip("S4")

from s4web.domain.entities.layer import CircleRegion, Layer, RectRegion, Region  # noqa: E402
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
SI = Material(4.0, 0.072)
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


# ---- x, y の 2 方向に周期を持つ格子 ----


def _sphere_array(num_slices: int, num_basis: int) -> SimulationCondition:
    """Si 球（直径 120nm）の正方配列（周期 160nm）。scripts/mie_sphere_validation.py と同じ構造。"""
    diameter, period = 120.0, 160.0
    height = diameter / num_slices
    slices = []
    for i in range(num_slices):
        z_mid = diameter - (i + 0.5) * height
        radius = math.sqrt((diameter / 2) ** 2 - (z_mid - diameter / 2) ** 2)
        slices.append(
            Layer(f"s{i}", height, AIR, (CircleRegion(SI, period / 2, period / 2, radius),))
        )
    return SimulationCondition(
        wl_min_nm=470,
        wl_max_nm=470,
        wl_points=1,
        theta_deg=0.0,
        polarization=Polarization.S,
        layers=(Layer("air", 0, AIR), *slices, Layer("sub", 0, Material(1.5))),
        period_nm=period,
        period_y_nm=period,
        num_basis=num_basis,
    )


def _grating_2d(region: Region | RectRegion, azimuth_deg: float = 0.0) -> SimulationCondition:
    return SimulationCondition(
        wl_min_nm=450,
        wl_max_nm=550,
        wl_points=2,
        theta_deg=10.0,
        polarization=Polarization.P,
        layers=(
            Layer("air", 0, AIR),
            Layer("grating", 120, AIR, (region,)),
            Layer("film", 60, Material(2.3)),
            Layer("sub", 0, SUS),
        ),
        period_nm=600,
        period_y_nm=600,
        num_basis=49,
        azimuth_deg=azimuth_deg,
    )


def test_sphere_array_matches_the_validation_script(solver: S4Solver) -> None:
    # mie_sphere_validation.py の収束表（8 スライス・基底 49）の値 R=0.493。
    spectrum = solver.solve(_sphere_array(8, 49))
    assert spectrum.reflectance_total is not None
    assert spectrum.reflectance_total[0] == pytest.approx(0.493, abs=0.002)
    # 160nm 周期では可視域に高次回折が無いので、0 次と全次数は一致する。
    assert spectrum.reflectance[0] == pytest.approx(spectrum.reflectance_total[0], abs=1e-9)


def test_rect_spanning_the_cell_equals_a_stripe_on_the_same_lattice(solver: S4Solver) -> None:
    stripe = solver.solve(_grating_2d(Region(Material(2.3), 0, 300)))
    rect = solver.solve(_grating_2d(RectRegion(Material(2.3), 150, 300, 300, 600)))
    assert rect.reflectance == pytest.approx(stripe.reflectance, abs=1e-9)
    assert rect.transmittance == pytest.approx(stripe.transmittance, abs=1e-9)


def test_orders_on_a_biperiodic_lattice_carry_both_indices(solver: S4Solver) -> None:
    condition = _grating_2d(RectRegion(Material(2.3), 150, 300, 300, 600))
    spectrum = solver.solve(condition)
    (dist, _) = solver.solve_orders(condition)
    indices = {(o.order, o.order_y) for o in dist.orders}
    # 450nm・周期 600nm・θ=10° で伝搬する次数（sin_x² + sin_y² ≤ 1）。
    assert indices == {(0, 0), (-1, 0), (1, 0), (0, 1), (0, -1), (-1, 1), (-1, -1)}
    by_index = {(o.order, o.order_y): o for o in dist.orders}
    assert by_index[(0, 0)].angle_deg == pytest.approx(10.0)
    assert by_index[(0, 0)].azimuth_deg == 0.0
    assert by_index[(-1, 0)].azimuth_deg == pytest.approx(180.0)
    # y 方向に一様な構造なので n ≠ 0 の次数にはパワーが行かない。
    assert all(abs(o.reflectance) < 1e-9 for o in dist.orders if o.order_y != 0)
    assert spectrum.reflectance_total is not None
    assert sum(o.reflectance for o in dist.orders) == pytest.approx(
        spectrum.reflectance_total[0], abs=1e-6
    )


def test_square_pillar_is_symmetric_between_x_and_y_incidence(solver: S4Solver) -> None:
    # 正方格子の中央に正方形の柱: xz 面入射（φ=0）と yz 面入射（φ=90）は対称で一致する。
    square = RectRegion(Material(2.3), 300, 300, 300, 300)
    along_x = solver.solve(_grating_2d(square, azimuth_deg=0.0))
    along_y = solver.solve(_grating_2d(square, azimuth_deg=90.0))
    assert along_y.reflectance == pytest.approx(along_x.reflectance, abs=1e-6)
    # 長方形の柱では対称性が崩れ、入射面の向きで結果が変わる。
    oblong = RectRegion(Material(2.3), 300, 300, 300, 150)
    assert solver.solve(_grating_2d(oblong, azimuth_deg=90.0)).reflectance != pytest.approx(
        solver.solve(_grating_2d(oblong, azimuth_deg=0.0)).reflectance, abs=1e-3
    )


def test_orders_follow_the_incidence_plane(solver: S4Solver) -> None:
    # yz 面入射では 0 次の方位角が 90°、x 方向の次数 (±1, 0) は入射の y 成分を持つ。
    square = RectRegion(Material(2.3), 300, 300, 300, 300)
    (dist, _) = solver.solve_orders(_grating_2d(square, azimuth_deg=90.0))
    by_index = {(o.order, o.order_y): o for o in dist.orders}
    assert by_index[(0, 0)].angle_deg == pytest.approx(10.0)
    assert by_index[(0, 0)].azimuth_deg == pytest.approx(90.0)
    assert by_index[(0, -1)].azimuth_deg == pytest.approx(-90.0)
