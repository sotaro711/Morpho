import importlib
import math

from s4web.domain.entities.layer import Layer
from s4web.domain.entities.material import Material
from s4web.domain.entities.simulation import Polarization, SimulationCondition

_KNOWN_CONDITION = SimulationCondition(
    wl_min_nm=550,
    wl_max_nm=550,
    wl_points=1,
    theta_deg=0.0,
    polarization=Polarization.S,
    layers=(Layer("air", 0, Material(1.0)), Layer("glass", 0, Material(1.5))),
)
_KNOWN_REFLECTANCE = 0.04
_TOLERANCE = 1e-6


def ensure_solver_available() -> None:
    try:
        importlib.import_module("S4")
    except ImportError as e:
        raise RuntimeError("S4 を読み込めません") from e
    _check_known_answer()


def _check_known_answer() -> None:
    # import できても、ライブラリの不整合などで計算結果だけが壊れることがあるので、実際に解く。
    from s4web.infrastructure.solvers.s4_solver import S4Solver

    try:
        spectrum = S4Solver().solve(_KNOWN_CONDITION)
    except Exception as e:
        raise RuntimeError("S4 の計算に失敗しました") from e

    r, t = spectrum.reflectance[0], spectrum.transmittance[0]
    if not (
        math.isclose(r, _KNOWN_REFLECTANCE, abs_tol=_TOLERANCE)
        and math.isclose(r + t, 1.0, abs_tol=_TOLERANCE)
    ):
        raise RuntimeError(f"S4 の計算結果が理論値と一致しません（R={r}, T={t}）")
