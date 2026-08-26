"""S4 を用いた SolverPort の実装（infrastructure 層）。

S4 の C 拡張に依存する唯一の場所。domain / application はこのモジュールを知らない。
SimulationCondition を S4 の API 呼び出しに変換し、波長を掃引して R/T を得る。

単位: domain は nm。S4 は無次元（長さの単位を1つ選んで一貫すればよい）なので、
内部では μm に統一する（厚さ・波長・周期をすべて μm に換算）。

平面多層膜（パターンなし）は回折 0 次のみで NumBasis=1 で厳密。格子定数は
結果に影響しないので公称値を用いる。面内パターン（Layer.regions）を持つ条件では
実周期を格子に渡し、層ごとに矩形領域を重ねる。

数値安定化（面内パターン時のみ。Rayleigh 点 / Wood アノマリー対策）:
  - SetOptions(PolarizationDecomposition=True): 金属を含む格子の収束改善
  - 無損失材料に微小吸収 k=1e-4 を付与して固有値の縮退をほどく
  - それでも NaN / 範囲外の R,T になった波長は微小シフトして再計算する
検証の経緯は backend/scripts/stepped_grating_validation.py の docstring を参照。
"""

import math

import S4  # type: ignore[import-not-found]

from s4web.domain.entities.layer import Layer
from s4web.domain.entities.material import Material
from s4web.domain.entities.simulation import (
    Polarization,
    SimulationCondition,
    Spectrum,
)
from s4web.domain.ports.solver_port import SolverPort

_NM_PER_UM = 1000.0

# 平面多層膜では格子定数は計算結果に影響しない（0 次のみ）。S4.New が必要とするため
# 公称値（μm）だけ与える。
_NOMINAL_PERIOD_UM = 1.0

# 無損失材料に付与する微小吸収（面内パターン時のみ）。結果への影響は測定誤差以下。
_LOSS_K = 1e-4

# Rayleigh 点で異常値が出た波長の退避シフト量（nm）。特異点は孤立点なので微小でよい。
_WL_SHIFTS_NM = (0.11, -0.11, 0.31)


class S4Solver(SolverPort):
    def solve(self, condition: SimulationCondition) -> Spectrum:
        sim = self._build(condition)

        top_name = _layer_name(0, condition.layers[0])
        bottom_name = _layer_name(len(condition.layers) - 1, condition.layers[-1])

        wls = condition.wavelengths_nm()
        reflectance: list[float] = []
        transmittance: list[float] = []
        for wl_nm in wls:
            r, t = _solve_at(sim, top_name, bottom_name, wl_nm)
            if condition.is_patterned and _is_anomalous(r, t):
                # Rayleigh 点（回折次数の出没する特異波長）では固有値計算が縮退して
                # NaN や発散が出る。波長を微小にずらして解き直す。
                for shift in _WL_SHIFTS_NM:
                    r, t = _solve_at(sim, top_name, bottom_name, wl_nm + shift)
                    if not _is_anomalous(r, t):
                        break
                else:
                    # 回復不能な点は 0 埋め（colorimetry 側の NaN→0 と同じ最終防波堤）。
                    r, t = 0.0, 0.0
            reflectance.append(r)
            transmittance.append(t)

        return Spectrum(
            wavelengths_nm=tuple(wls),
            reflectance=tuple(reflectance),
            transmittance=tuple(transmittance),
        )

    def _build(self, condition: SimulationCondition):
        # 戻り値は S4 のシミュレーションオブジェクト（S4 の型は未公開なので注釈しない）。
        # RCWA の計算空間を作る。NumBasis = RCWA が保持するフーリエ次数（逆格子ベクトル G）
        # の数。面内パターンがあれば実周期を、無ければ公称値を格子に渡す。
        patterned = condition.is_patterned
        if condition.period_nm is not None:
            period_um = condition.period_nm / _NM_PER_UM
        else:
            period_um = _NOMINAL_PERIOD_UM
        sim = S4.New(
            Lattice=((period_um, 0.0), (0.0, 0.0)),  # 1D 格子（第2ベクトルは0）
            NumBasis=condition.num_basis,
        )
        if patterned:
            # 金属を含む格子の収束改善（Li の因子化）。平面多層膜では不要なので
            # 既存の計算経路を変えないよう、パターン時のみ有効化する。
            sim.SetOptions(PolarizationDecomposition=True)

        # 各材料の比誘電率 ε を登録する（RCWA はこの ε をフーリエ空間で扱う）。
        # 層が参照する前に存在している必要があるので先に登録する。
        # 微小吸収は入射側半無限層（i=0）には付与しない。入射媒質に吸収があると
        # 入射パワーの規格化がずれ、R/T の定義が曖昧になるため。
        for i, layer in enumerate(condition.layers):
            lossy = patterned and i > 0
            sim.SetMaterial(Name=_mat_name(i), Epsilon=_epsilon(layer.material, lossy))
            for j, region in enumerate(layer.regions):
                sim.SetMaterial(
                    Name=_region_mat_name(i, j),
                    Epsilon=_epsilon(region.material, lossy),
                )

        # 層を入射側から順に追加する。regions を持つ層は、層の材料を背景として
        # 矩形領域を重ねる（S4 の Center/Halfwidths は単位胞座標・μm）。
        for i, layer in enumerate(condition.layers):
            layer_name = _layer_name(i, layer)
            sim.AddLayer(
                Name=layer_name,
                Thickness=layer.thickness_nm / _NM_PER_UM,
                S4_Material=_mat_name(i),
            )
            for j, region in enumerate(layer.regions):
                sim.SetRegionRectangle(
                    S4_Layer=layer_name,
                    S4_Material=_region_mat_name(i, j),
                    Center=((region.x_nm + region.width_nm / 2.0) / _NM_PER_UM, 0.0),
                    Angle=0.0,
                    Halfwidths=(region.width_nm / 2.0 / _NM_PER_UM, 0.0),
                )

        # 入射する平面波（境界条件）を定義する。入射角 θ と偏光を与える。
        # s 偏光 → sAmplitude のみ、p 偏光 → pAmplitude のみ。
        if condition.polarization is Polarization.S:
            s_amp, p_amp = 1.0, 0.0
        else:
            s_amp, p_amp = 0.0, 1.0
        sim.SetExcitationPlanewave(
            IncidenceAngles=(condition.theta_deg, 0.0),  # (polar, azimuth) degrees
            sAmplitude=s_amp,
            pAmplitude=p_amp,
        )
        return sim


def _solve_at(sim, top_name: str, bottom_name: str, wl_nm: float) -> tuple[float, float]:
    """1 波長を解いて (反射率, 透過率) を返す。

    波長（周波数 = 1/λ）を設定した時点で S4 はその波長について RCWA を解く:
    各層を固有モードに分解（SolveLayerEigensystem）し、層間を散乱行列（S 行列）で
    接続して全体の場を求める（S4 内部 rcwa.cpp の SolveAll）。
    """
    wl_um = wl_nm / _NM_PER_UM
    sim.SetFrequency(1.0 / wl_um)
    # GetPowerFlux は層境界のポインティングフラックス（GetZPoyntingFlux）を返す。
    # 戻り値は (前進波パワー, 後退波パワー)。
    forw_top, back_top = sim.GetPowerFlux(S4_Layer=top_name)
    forw_bot, _ = sim.GetPowerFlux(S4_Layer=bottom_name)
    incident = forw_top.real
    if incident == 0.0:
        return 0.0, 0.0
    # 入射層の後退波 = 反射、基板層の前進波 = 透過。入射パワーで規格化。
    return -back_top.real / incident, forw_bot.real / incident


def _is_anomalous(r: float, t: float) -> bool:
    """NaN、または物理的にありえない値（発散の前兆）を異常とみなす。"""
    for v in (r, t):
        if math.isnan(v) or v < -0.01 or v > 1.05:
            return True
    return False


def _epsilon(material: Material, lossy: bool) -> complex:
    """材料の比誘電率。lossy 指定時は無損失材料に微小吸収を付与する。"""
    nc = material.refractive_index
    if lossy and nc.imag == 0.0:
        nc = complex(nc.real, _LOSS_K)
    return nc * nc


def _layer_name(index: int, layer: Layer) -> str:
    # 層名の一意性をインデックスで保証する（domain では層名の重複を許す）。
    return f"L{index}_{layer.name}"


def _mat_name(index: int) -> str:
    return f"mat_L{index}"


def _region_mat_name(layer_index: int, region_index: int) -> str:
    return f"mat_L{layer_index}_r{region_index}"
