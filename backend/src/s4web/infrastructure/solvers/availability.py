"""S4 を読み込めて、正しく計算できるかの確認。

s4_solver は先頭で S4 を import するため、S4 がない環境では読み込んだ時点で失敗する。
起動時の確認にはこのモジュールを使い、s4_solver は S4 を読み込めた後でだけ読み込む。
"""

import importlib
import math

from s4web.domain.entities.layer import Layer
from s4web.domain.entities.material import Material
from s4web.domain.entities.simulation import Polarization, SimulationCondition

# 空気からガラス(n=1.5)への垂直入射。フレネルの式から R = ((1 - 1.5) / (1 + 1.5))^2 = 0.04。
# 平坦な 2 層・1 波長なので、計算は 1 ms もかからない。
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
    """S4 を読み込めて、理論値の分かる条件を正しく解けるかを確かめる。だめなら RuntimeError。"""
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
    # NaN はどちらの比較も False になるので、ここで弾かれる。
    if not (
        math.isclose(r, _KNOWN_REFLECTANCE, abs_tol=_TOLERANCE)
        and math.isclose(r + t, 1.0, abs_tol=_TOLERANCE)
    ):
        raise RuntimeError(f"S4 の計算結果が理論値と一致しません（R={r}, T={t}）")
