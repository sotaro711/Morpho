"""S4 を用いた SolverPort の実装（infrastructure 層）。

S4 の C 拡張に依存する唯一の場所。domain / application はこのモジュールを知らない。
SimulationCondition を S4 の API 呼び出しに変換し、波長を掃引して R/T を得る。

単位: domain は nm。S4 は無次元（長さの単位を1つ選んで一貫すればよい）なので、
内部では μm に統一する（厚さ・波長をすべて μm に換算）。

対象は横方向に一様な平面多層膜。面内の周期構造を持たないため回折は 0 次のみで、
NumBasis=1 で厳密。格子定数は結果に影響しないので公称値を用いる。
"""

import S4  # type: ignore[import-not-found]

from s4web.domain.entities.layer import Layer
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


class S4Solver(SolverPort):
    def solve(self, condition: SimulationCondition) -> Spectrum:
        sim = self._build(condition)

        top_name = _layer_name(0, condition.layers[0])
        bottom_name = _layer_name(len(condition.layers) - 1, condition.layers[-1])

        wls = condition.wavelengths_nm()
        reflectance: list[float] = []
        transmittance: list[float] = []
        for wl_nm in wls:
            wl_um = wl_nm / _NM_PER_UM
            # 波長（周波数 = 1/λ）を設定。この時点で S4 はその波長について RCWA を解く:
            # 各層を固有モードに分解（SolveLayerEigensystem）し、層間を散乱行列（S 行列）で
            # 接続して全体の場を求める（S4 内部 rcwa.cpp の SolveAll）。
            sim.SetFrequency(1.0 / wl_um)
            # GetPowerFlux は層境界のポインティングフラックス（GetZPoyntingFlux）を返す。
            # 戻り値は (前進波パワー, 後退波パワー)。
            forw_top, back_top = sim.GetPowerFlux(S4_Layer=top_name)
            forw_bot, _ = sim.GetPowerFlux(S4_Layer=bottom_name)
            incident = forw_top.real
            if incident == 0.0:
                reflectance.append(0.0)
                transmittance.append(0.0)
                continue
            # 入射層の後退波 = 反射、基板層の前進波 = 透過。入射パワーで規格化。
            reflectance.append(-back_top.real / incident)
            transmittance.append(forw_bot.real / incident)

        return Spectrum(
            wavelengths_nm=tuple(wls),
            reflectance=tuple(reflectance),
            transmittance=tuple(transmittance),
        )

    def _build(self, condition: SimulationCondition):
        # 戻り値は S4 のシミュレーションオブジェクト（S4 の型は未公開なので注釈しない）。
        # RCWA の計算空間を作る。NumBasis = RCWA が保持するフーリエ次数（逆格子ベクトル G）
        # の数。面内に周期構造が無い平面多層膜では回折次数は 0 次のみなので 1 で厳密。
        # Lattice は次数の取り方を決めるが、0 次のみでは結果に効かないため公称値。
        sim = S4.New(
            Lattice=((_NOMINAL_PERIOD_UM, 0.0), (0.0, 0.0)),  # 1D 格子（第2ベクトルは0）
            NumBasis=1,  # 平面多層膜は 0 次のみ
        )

        # 各材料の比誘電率 ε を登録する（RCWA はこの ε をフーリエ空間で扱う）。
        # 層が参照する前に存在している必要があるので先に登録する。
        for i, layer in enumerate(condition.layers):
            sim.SetMaterial(Name=_mat_name(i), Epsilon=layer.material.epsilon)

        # 層を入射側から順に追加する。各層は厚さと材料（ε）を持ち、波長設定時に
        # S4 がこの層ごとに固有モードを解く（rcwa.cpp の SolveLayerEigensystem）。
        for i, layer in enumerate(condition.layers):
            sim.AddLayer(
                Name=_layer_name(i, layer),
                Thickness=layer.thickness_nm / _NM_PER_UM,
                S4_Material=_mat_name(i),
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


def _layer_name(index: int, layer: Layer) -> str:
    # 層名の一意性をインデックスで保証する（domain では層名の重複を許す）。
    return f"L{index}_{layer.name}"


def _mat_name(index: int) -> str:
    return f"mat_L{index}"
