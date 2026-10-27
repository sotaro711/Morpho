"""S4 を用いた SolverPort の実装（infrastructure 層）。

S4 の C 拡張に依存する唯一の場所。domain / application はこのモジュールを知らない。
SimulationCondition を S4 の API 呼び出しに変換し、波長を掃引して R/T を得る。
R/T は回折 0 次（正反射・直進透過）の成分（詳細は _solve_at の docstring）。
反射は全次数の合計も併せて返す（0 次以外 = 合計 − 0 次 は domain 側で取り出す）。

単位: domain は nm。S4 は無次元（長さの単位を1つ選んで一貫すればよい）なので、
内部では μm に統一する（厚さ・波長・周期をすべて μm に換算）。

平面多層膜（パターンなし）は回折 0 次のみで NumBasis=1 で厳密。格子定数は
結果に影響しないので公称値を用いる。面内パターン（Layer.regions）を持つ条件では
実周期を格子に渡し、層ごとに領域を重ねる。period_y_nm がある条件は x, y の
2 方向に周期を持つ格子（Lattice の第 2 ベクトルが (0, Py)）で、円・矩形の領域を
置ける。回折次数は (m, n) の 2 つになる。

数値安定化（面内パターン時のみ。Rayleigh 点 / Wood アノマリー対策）:
  - SetOptions(PolarizationDecomposition=True): 金属を含む格子の収束改善。
    1D 格子だけで有効にする。誘電体の円領域を持つ 2 方向周期の格子では逆に収束を
    著しく悪くした（backend/scripts/mie_sphere_validation.py の docstring）。
    金属を含む 2 方向周期の構造（SUS 基板の角柱）では、有効・無効のどちらも基底数に
    対して収束するが互いに 0.03 ほど違う値に落ち着き、どちらが正しいかは参照解が
    ないため未確定（backend/scripts/pillar_multilayer_validation.py の docstring）。
    金属を含む 2 方向周期の反射率には ±0.03 程度の不確かさがあるものとして扱う。
  - 無損失材料に微小吸収 k=1e-4 を付与して固有値の縮退をほどく
  - それでも NaN / 範囲外の R,T になった波長は微小シフトして再計算する
検証の経緯は backend/scripts/stepped_grating_validation.py の docstring を参照。

波長分散する材料（DispersiveMaterial）を含む条件では、波長ごとに全材料の ε を
登録し直してから解く。S4 の SetMaterial は同名で呼ぶと ε を上書きし、直後の
SetFrequency が層の固有モードと解を破棄するので、新しい ε で解き直される。
"""

import math

import S4  # type: ignore[import-not-found]

from s4web.domain.entities.diffraction import AngularDistribution, DiffractionOrder
from s4web.domain.entities.layer import CircleRegion, Layer, RectRegion, Region
from s4web.domain.entities.material import OpticalMaterial
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
        reflectance_total: list[float] = []
        for wl_nm in wls:
            _update_materials(sim, condition, wl_nm)
            r, t, r_total = _solve_at(sim, top_name, bottom_name, wl_nm)
            if condition.is_patterned and _is_anomalous(r, t):
                # Rayleigh 点（回折次数の出没する特異波長）では固有値計算が縮退して
                # NaN や発散が出る。波長を微小にずらして解き直す。
                for shift in _WL_SHIFTS_NM:
                    _update_materials(sim, condition, wl_nm + shift)
                    r, t, r_total = _solve_at(sim, top_name, bottom_name, wl_nm + shift)
                    if not _is_anomalous(r, t):
                        break
                else:
                    # 回復不能な点は 0 埋め（colorimetry 側の NaN→0 と同じ最終防波堤）。
                    r, t, r_total = 0.0, 0.0, 0.0
            reflectance.append(r)
            transmittance.append(t)
            reflectance_total.append(r_total)

        return Spectrum(
            wavelengths_nm=tuple(wls),
            reflectance=tuple(reflectance),
            transmittance=tuple(transmittance),
            reflectance_total=tuple(reflectance_total),
        )

    def solve_orders(self, condition: SimulationCondition) -> tuple[AngularDistribution, ...]:
        sim = self._build(condition)

        top_name = _layer_name(0, condition.layers[0])
        periods_um = _periods_um(condition)
        # 入射波の面内方向（sinθ を方位角 φ で x, y に分ける）。
        sin_in = math.sin(math.radians(condition.theta_deg))
        phi = math.radians(condition.azimuth_deg)
        sin_in_xy = (sin_in * math.cos(phi), sin_in * math.sin(phi))

        distributions: list[AngularDistribution] = []
        for wl_nm in condition.wavelengths_nm():
            _update_materials(sim, condition, wl_nm)
            orders = _orders_at(sim, top_name, wl_nm, sin_in_xy, periods_um)
            if orders is None and condition.is_patterned:
                # スペクトル計算と同じ Rayleigh 点対策（波長微小シフトで解き直す）。
                for shift in _WL_SHIFTS_NM:
                    _update_materials(sim, condition, wl_nm + shift)
                    orders = _orders_at(sim, top_name, wl_nm + shift, sin_in_xy, periods_um)
                    if orders is not None:
                        break
            # 回復不能な波長は空の分布（呼び出し側は「データなし」として扱える）。
            distributions.append(AngularDistribution(wl_nm, orders or ()))
        return tuple(distributions)

    def _build(self, condition: SimulationCondition):
        # 戻り値は S4 のシミュレーションオブジェクト（S4 の型は未公開なので注釈しない）。
        # RCWA の計算空間を作る。NumBasis = RCWA が保持するフーリエ次数（逆格子ベクトル G）
        # の数。面内パターンがあれば実周期を、無ければ公称値を格子に渡す。
        # 1D 格子は第 2 ベクトルを 0 にし、2 方向周期なら (0, Py) にする。
        patterned = condition.is_patterned
        period_um, period_y_um = _periods_um(condition)
        sim = S4.New(
            Lattice=((period_um, 0.0), (0.0, period_y_um)),
            NumBasis=condition.num_basis,
        )
        if patterned and not condition.is_biperiodic:
            # 金属を含む格子の収束改善（Li の因子化）。平面多層膜では不要なので
            # 既存の計算経路を変えないよう、パターン時のみ有効化する。2 方向周期では
            # 誘電体の円領域で収束が著しく悪くなるため使わない（モジュール docstring）。
            sim.SetOptions(PolarizationDecomposition=True)

        # 各材料の比誘電率 ε を登録する（RCWA はこの ε をフーリエ空間で扱う）。
        # 層が参照する前に存在している必要があるので先に登録する。分散材料の値は
        # 最初の波長のもので、各波長を解く前に _update_materials が登録し直す。
        _set_materials(sim, condition, condition.wavelengths_nm()[0])

        # 層を入射側から順に追加する。regions を持つ層は、層の材料を背景として
        # 領域を重ねる（S4 の Center/Halfwidths/Radius は単位胞座標・μm）。
        for i, layer in enumerate(condition.layers):
            layer_name = _layer_name(i, layer)
            sim.AddLayer(
                Name=layer_name,
                Thickness=layer.thickness_nm / _NM_PER_UM,
                S4_Material=_mat_name(i),
            )
            for j, region in enumerate(layer.regions):
                _set_region(sim, layer_name, _region_mat_name(i, j), region, period_y_um)

        # 入射する平面波（境界条件）を定義する。入射角 θ と偏光を与える。
        # s 偏光 → sAmplitude のみ、p 偏光 → pAmplitude のみ。
        if condition.polarization is Polarization.S:
            s_amp, p_amp = 1.0, 0.0
        else:
            s_amp, p_amp = 0.0, 1.0
        # 負の入射角(角度スイープ用)は「極角 |θ|・方位角 +180°」= 反対側からの
        # 入射として S4 に渡す。方位角は入射面の向き（0 = xz 面、90 = yz 面）。
        theta = condition.theta_deg
        azimuth = condition.azimuth_deg
        incidence = (theta, azimuth) if theta >= 0 else (-theta, (azimuth + 180.0) % 360.0)
        sim.SetExcitationPlanewave(
            IncidenceAngles=incidence,  # (polar, azimuth) degrees
            sAmplitude=s_amp,
            pAmplitude=p_amp,
        )
        return sim


def _periods_um(condition: SimulationCondition) -> tuple[float, float]:
    """格子に渡す周期 (Px, Py)（μm）。パターンなしは公称値、1D 格子は Py=0。"""
    if condition.period_nm is None:
        return _NOMINAL_PERIOD_UM, 0.0
    period_y_um = condition.period_y_nm / _NM_PER_UM if condition.period_y_nm is not None else 0.0
    return condition.period_nm / _NM_PER_UM, period_y_um


def _set_region(
    sim,
    layer_name: str,
    material_name: str,
    region: Region | CircleRegion | RectRegion,
    period_y_um: float,
) -> None:
    if isinstance(region, CircleRegion):
        sim.SetRegionCircle(
            S4_Layer=layer_name,
            S4_Material=material_name,
            Center=(region.cx_nm / _NM_PER_UM, region.cy_nm / _NM_PER_UM),
            Radius=region.radius_nm / _NM_PER_UM,
        )
        return
    if isinstance(region, RectRegion):
        center = (region.cx_nm / _NM_PER_UM, region.cy_nm / _NM_PER_UM)
        halfwidths = (region.width_nm / 2.0 / _NM_PER_UM, region.height_nm / 2.0 / _NM_PER_UM)
    else:
        # x 方向の区間。2 方向周期の格子に置くときは y 方向に単位胞いっぱいに伸ばす
        # （1D 格子では y 方向の半幅 0 で S4 が一様と解釈する）。
        center = ((region.x_nm + region.width_nm / 2.0) / _NM_PER_UM, period_y_um / 2.0)
        halfwidths = (region.width_nm / 2.0 / _NM_PER_UM, period_y_um / 2.0)
    sim.SetRegionRectangle(
        S4_Layer=layer_name,
        S4_Material=material_name,
        Center=center,
        Angle=0.0,
        Halfwidths=halfwidths,
    )


def _solve_at(sim, top_name: str, bottom_name: str, wl_nm: float) -> tuple[float, float, float]:
    """1 波長を解いて (0 次反射率, 0 次透過率, 全次数の反射率) を返す。

    波長（周波数 = 1/λ）を設定した時点で S4 はその波長について RCWA を解く:
    各層を固有モードに分解（SolveLayerEigensystem）し、層間を散乱行列（S 行列）で
    接続して全体の場を求める（S4 内部 rcwa.cpp の SolveAll）。

    面内パターンがある場合、反射光は回折次数 m = 0, ±1, ±2, … に分かれる。
    観測者が正反射方向で見る量は m = 0 成分なので、それを反射率とする
    （全次数の合計は「反射側に戻った総エネルギー」であり、見え方とは別の量）。
    平面多層膜は次数が (0,0) の 1 つだけなので従来の全パワー計算と一致する。
    全次数の反射率は「反射側に戻った総エネルギー」として別に返し、0 次以外
    （高次回折光）の量は呼び出し側で 合計 − 0 次 として求める。
    """
    wl_um = wl_nm / _NM_PER_UM
    sim.SetFrequency(1.0 / wl_um)
    # GetPowerFluxByOrder は層境界のポインティングフラックスを基底（次数）ごとに
    # 返す。各要素は (前進波パワー, 後退波パワー)。
    fluxes_top = sim.GetPowerFluxByOrder(S4_Layer=top_name)
    fluxes_bot = sim.GetPowerFluxByOrder(S4_Layer=bottom_name)
    i0 = sim.GetBasisSet().index((0, 0))
    # 入射波は 0 次のみだが、規格化は前進波の合計で行う（_orders_at と同じ規約）。
    incident = sum(f.real for f, _ in fluxes_top)
    if incident == 0.0:
        return 0.0, 0.0, 0.0
    # Rayleigh 点の発散は高次側に出て 0 次だけ正常に見えることがあるため、
    # 全次数の合計が異常ならそれを返して呼び出し側の _is_anomalous に検出させる。
    total_r = sum(-b.real for _, b in fluxes_top) / incident
    total_t = sum(f.real for f, _ in fluxes_bot) / incident
    if _is_anomalous(total_r, total_t):
        return total_r, total_t, total_r
    # 入射層の後退波 = 反射、基板層の前進波 = 透過。入射パワーで規格化。
    return -fluxes_top[i0][1].real / incident, fluxes_bot[i0][0].real / incident, total_r


def _orders_at(
    sim,
    top_name: str,
    wl_nm: float,
    sin_in_xy: tuple[float, float],
    periods_um: tuple[float, float],
) -> tuple[DiffractionOrder, ...] | None:
    """1 波長の回折次数ごとの反射パワーと出射角。数値異常なら None を返す。

    GetPowerFluxByOrder は入射側層のフラックスを基底（次数）ごとに返す。
    各次数の後退波が R_m。出射方向は格子方程式 sinθ_x = sinθ_in,x + mλ/Px、
    sinθ_y = sinθ_in,y + nλ/Py から求め、面内成分の大きさが 1 を超える次数は
    伝搬しない（遠方に届かない）ので除外する。1D 格子では入射面が xz 面で n = 0 だけ、
    出射角は符号付き（負は入射側と反対方向）。2 方向周期では極角（≥ 0）と方位角で表す。
    """
    wl_um = wl_nm / _NM_PER_UM
    period_um, period_y_um = periods_um
    sin_in, sin_in_y = sin_in_xy
    sim.SetFrequency(1.0 / wl_um)
    fluxes = sim.GetPowerFluxByOrder(S4_Layer=top_name)
    basis = sim.GetBasisSet()  # ((m, n), ...)。1D 格子では n は常に 0
    incident = sum(f.real for f, _ in fluxes)
    if incident == 0.0 or math.isnan(incident):
        return None

    orders: list[DiffractionOrder] = []
    total_r = 0.0
    for (m, n), flux in zip(basis, fluxes, strict=True):
        r_m = -flux[1].real / incident
        total_r += r_m
        sin_x = sin_in + m * wl_um / period_um
        if period_y_um == 0.0:
            if abs(sin_x) <= 1.0:
                orders.append(DiffractionOrder(m, math.degrees(math.asin(sin_x)), r_m))
            continue
        sin_y = sin_in_y + n * wl_um / period_y_um
        sin_polar = math.hypot(sin_x, sin_y)
        if sin_polar <= 1.0:
            orders.append(
                DiffractionOrder(
                    m,
                    math.degrees(math.asin(sin_polar)),
                    r_m,
                    order_y=n,
                    azimuth_deg=math.degrees(math.atan2(sin_y, sin_x)),
                )
            )
    if math.isnan(total_r) or total_r < -0.01 or total_r > 1.05:
        return None
    orders.sort(key=lambda o: (o.angle_deg, o.azimuth_deg))
    return tuple(orders)


def _is_anomalous(r: float, t: float) -> bool:
    """NaN、または物理的にありえない値（発散の前兆）を異常とみなす。"""
    for v in (r, t):
        if math.isnan(v) or v < -0.01 or v > 1.05:
            return True
    # エネルギー保存: 反射 + 透過が入射を超えることはない（吸収があれば 1 未満）。
    return r + t > 1.05


def _set_materials(sim, condition: SimulationCondition, wl_nm: float) -> None:
    """全層・全領域の材料の ε を、指定波長の値で登録（同名なら上書き）する。

    微小吸収は入射側半無限層（i=0）には付与しない。入射媒質に吸収があると
    入射パワーの規格化がずれ、R/T の定義が曖昧になるため。
    """
    patterned = condition.is_patterned
    for i, layer in enumerate(condition.layers):
        lossy = patterned and i > 0
        sim.SetMaterial(Name=_mat_name(i), Epsilon=_epsilon(layer.material, lossy, wl_nm))
        for j, region in enumerate(layer.regions):
            sim.SetMaterial(
                Name=_region_mat_name(i, j),
                Epsilon=_epsilon(region.material, lossy, wl_nm),
            )


def _update_materials(sim, condition: SimulationCondition, wl_nm: float) -> None:
    """分散材料を含む条件なら、解く直前にその波長の ε で登録し直す。

    定数の材料だけの条件では何もしない（従来の計算経路を変えない）。
    """
    if condition.is_dispersive:
        _set_materials(sim, condition, wl_nm)


def _epsilon(material: OpticalMaterial, lossy: bool, wl_nm: float) -> complex:
    """指定波長での材料の比誘電率。lossy 指定時は無損失材料に微小吸収を付与する。"""
    nc = material.refractive_index_at(wl_nm)
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
