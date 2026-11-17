"""構造によらず成り立つはずの物理的な性質。S4 が入っていない環境（CI）ではスキップする。

個々の値の正しさではなく、エネルギー保存や範囲のような「壊れたら必ずおかしい」条件を見る。
"""

import pytest

pytest.importorskip("S4")

from s4web.domain.entities.layer import Layer, Region  # noqa: E402
from s4web.domain.entities.material import Material  # noqa: E402
from s4web.domain.entities.simulation import Polarization, SimulationCondition  # noqa: E402
from s4web.infrastructure.solvers.s4_solver import S4Solver  # noqa: E402

AIR = Material(1.0)
GLASS = Material(1.52)
ZRO2 = Material(2.2)
SUS = Material(1.71, 2.88)
WAVELENGTHS = (380.0, 450.0, 530.0, 610.0, 700.0, 780.0)
POLARIZATIONS = (Polarization.S, Polarization.P)
ANGLES = (0.0, 30.0, 60.0)


def _condition(
    layers: tuple[Layer, ...],
    theta_deg: float,
    polarization: Polarization,
    period_nm: float | None = None,
) -> SimulationCondition:
    return SimulationCondition(
        wl_min_nm=min(WAVELENGTHS),
        wl_max_nm=max(WAVELENGTHS),
        wl_points=len(WAVELENGTHS),
        theta_deg=theta_deg,
        polarization=polarization,
        layers=layers,
        period_nm=period_nm,
        num_basis=11 if period_nm else 1,
        explicit_wavelengths_nm=WAVELENGTHS,
    )


def _lossless_stack() -> tuple[Layer, ...]:
    return (
        Layer("air", 0, AIR),
        Layer("zro2", 80, ZRO2),
        Layer("glass", 120, GLASS),
        Layer("zro2", 60, ZRO2),
        Layer("sub", 0, GLASS),
    )


def _absorbing_grating() -> tuple[Layer, ...]:
    return (
        Layer("air", 0, AIR),
        Layer("grating", 150, AIR, (Region(ZRO2, 0, 200),)),
        Layer("film", 50, ZRO2),
        Layer("sub", 0, SUS),
    )


@pytest.fixture(scope="module")
def solver() -> S4Solver:
    return S4Solver()


@pytest.mark.parametrize("polarization", POLARIZATIONS)
@pytest.mark.parametrize("theta_deg", ANGLES)
def test_lossless_flat_stack_conserves_energy(
    solver: S4Solver, theta_deg: float, polarization: Polarization
) -> None:
    spectrum = solver.solve(_condition(_lossless_stack(), theta_deg, polarization))
    for r, t in zip(spectrum.reflectance, spectrum.transmittance, strict=True):
        assert r + t == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("polarization", POLARIZATIONS)
def test_absorbing_film_loses_energy(solver: S4Solver, polarization: Polarization) -> None:
    # 有限厚の吸収層を挟むと吸収率 A = 1 − R − T が正になる。
    # 半無限の基板が吸収体でも、基板に入ったパワーは T に数えるので R + T = 1 のまま。
    layers = (Layer("air", 0, AIR), Layer("sus", 10, SUS), Layer("sub", 0, GLASS))
    spectrum = solver.solve(_condition(layers, 30.0, polarization))
    for r, t in zip(spectrum.reflectance, spectrum.transmittance, strict=True):
        assert 0.0 <= r and 0.0 <= t
        assert r + t < 1.0


@pytest.mark.parametrize("polarization", POLARIZATIONS)
@pytest.mark.parametrize("theta_deg", ANGLES)
def test_grating_powers_stay_physical(
    solver: S4Solver, theta_deg: float, polarization: Polarization
) -> None:
    spectrum = solver.solve(_condition(_absorbing_grating(), theta_deg, polarization, 400.0))
    assert spectrum.reflectance_total is not None
    for r0, r_all, t0 in zip(
        spectrum.reflectance, spectrum.reflectance_total, spectrum.transmittance, strict=True
    ):
        assert -1e-6 <= r0 <= r_all + 1e-6
        assert 0.0 <= t0 + 1e-6
        # 0 次の透過は全透過の一部なので、全反射と足しても入射を超えない。
        assert r_all + t0 <= 1.0 + 1e-6


@pytest.mark.parametrize("polarization", POLARIZATIONS)
def test_diffraction_orders_sum_to_total_reflectance(
    solver: S4Solver, polarization: Polarization
) -> None:
    condition = _condition(_absorbing_grating(), 20.0, polarization, 400.0)
    spectrum = solver.solve(condition)
    distributions = solver.solve_orders(condition)
    assert spectrum.reflectance_total is not None
    for dist, total in zip(distributions, spectrum.reflectance_total, strict=True):
        assert sum(o.reflectance for o in dist.orders) == pytest.approx(total, abs=1e-6)
