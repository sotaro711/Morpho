"""Rayleigh 点 / Wood アノマリー対策（面内パターン時のみ）:
  - SetOptions(PolarizationDecomposition=True) は 1D 格子だけで有効にする。誘電体の円領域を
    持つ 2 方向周期の格子では逆に収束を著しく悪くする。
  - 無損失材料に微小吸収 k=1e-4 を付与して固有値の縮退をほどく
  - それでも NaN / 範囲外の R,T になった波長は微小シフトして再計算する

S4 の SetMaterial は同名で呼ぶと ε を上書きし、直後の SetFrequency が層の固有モードと
解を破棄するので、新しい ε で解き直される。
"""

import logging
import math
import time

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

_LOSS_K = 1e-4

_WL_SHIFTS_NM = (0.11, -0.11, 0.31)

_logger = logging.getLogger(__name__)

_SLOW_SOLVE_SEC = 0.5


class S4Solver(SolverPort):
    def solve(self, condition: SimulationCondition) -> Spectrum:
        sim = self._build(condition)

        top_name = _layer_name(0, condition.layers[0])
        bottom_name = _layer_name(len(condition.layers) - 1, condition.layers[-1])

        wls = condition.wavelengths_nm()
        reflectance: list[float] = []
        transmittance: list[float] = []
        reflectance_total: list[float] = []
        for i, wl_nm in enumerate(wls, start=1):
            started = time.perf_counter()
            _update_materials(sim, condition, wl_nm)
            r, t, r_total = _solve_at(sim, top_name, bottom_name, wl_nm)
            if condition.is_patterned and _is_anomalous(r, t):
                _logger.warning(
                    "anomalous R=%.3g T=%.3g at %gnm theta=%g, retrying with shifted wavelength",
                    r,
                    t,
                    wl_nm,
                    condition.theta_deg,
                )
                for shift in _WL_SHIFTS_NM:
                    _update_materials(sim, condition, wl_nm + shift)
                    r, t, r_total = _solve_at(sim, top_name, bottom_name, wl_nm + shift)
                    if not _is_anomalous(r, t):
                        _logger.warning("recovered at %gnm (shift %+g)", wl_nm, shift)
                        break
                else:
                    _logger.warning("could not recover at %gnm, filling R=T=0", wl_nm)
                    r, t, r_total = 0.0, 0.0, 0.0
            _log_solve_time(wl_nm, i, len(wls), condition.theta_deg, started)
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
        sin_in = math.sin(math.radians(condition.theta_deg))
        phi = math.radians(condition.azimuth_deg)
        sin_in_xy = (sin_in * math.cos(phi), sin_in * math.sin(phi))

        distributions: list[AngularDistribution] = []
        wls = condition.wavelengths_nm()
        for i, wl_nm in enumerate(wls, start=1):
            started = time.perf_counter()
            _update_materials(sim, condition, wl_nm)
            orders = _orders_at(sim, top_name, wl_nm, sin_in_xy, periods_um)
            if orders is None and condition.is_patterned:
                _logger.warning(
                    "anomalous orders at %gnm theta=%g, retrying with shifted wavelength",
                    wl_nm,
                    condition.theta_deg,
                )
                for shift in _WL_SHIFTS_NM:
                    _update_materials(sim, condition, wl_nm + shift)
                    orders = _orders_at(sim, top_name, wl_nm + shift, sin_in_xy, periods_um)
                    if orders is not None:
                        _logger.warning("recovered at %gnm (shift %+g)", wl_nm, shift)
                        break
                else:
                    _logger.warning("could not recover at %gnm, returning no orders", wl_nm)
            _log_solve_time(wl_nm, i, len(wls), condition.theta_deg, started)
            distributions.append(AngularDistribution(wl_nm, orders or ()))
        return tuple(distributions)

    def _build(self, condition: SimulationCondition):
        patterned = condition.is_patterned
        period_um, period_y_um = _periods_um(condition)
        sim = S4.New(
            Lattice=((period_um, 0.0), (0.0, period_y_um)),
            NumBasis=condition.num_basis,
        )
        if patterned and not condition.is_biperiodic:
            sim.SetOptions(PolarizationDecomposition=True)
        _logger.debug(
            "S4.New lattice=(%g, %g)um basis=%d layers=%d regions=%d polarization_decomposition=%s",
            period_um,
            period_y_um,
            condition.num_basis,
            len(condition.layers),
            sum(len(layer.regions) for layer in condition.layers),
            patterned and not condition.is_biperiodic,
        )

        # 層が参照する前に存在している必要があるので先に登録する。
        _set_materials(sim, condition, condition.wavelengths_nm()[0])

        for i, layer in enumerate(condition.layers):
            layer_name = _layer_name(i, layer)
            sim.AddLayer(
                Name=layer_name,
                Thickness=layer.thickness_nm / _NM_PER_UM,
                S4_Material=_mat_name(i),
            )
            for j, region in enumerate(layer.regions):
                _set_region(sim, layer_name, _region_mat_name(i, j), region, period_y_um)

        if condition.polarization is Polarization.S:
            s_amp, p_amp = 1.0, 0.0
        else:
            s_amp, p_amp = 0.0, 1.0
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
    if condition.period_nm is None:
        return _NOMINAL_PERIOD_UM, 0.0
    period_y_um = condition.period_y_nm / _NM_PER_UM if condition.period_y_nm is not None else 0.0
    return condition.period_nm / _NM_PER_UM, period_y_um


def _log_solve_time(wl_nm: float, index: int, count: int, theta_deg: float, started: float) -> None:
    elapsed = time.perf_counter() - started
    level = logging.INFO if elapsed >= _SLOW_SOLVE_SEC else logging.DEBUG
    _logger.log(
        level, "wl=%gnm %d/%d theta=%g solved in %.2fs", wl_nm, index, count, theta_deg, elapsed
    )


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
    wl_um = wl_nm / _NM_PER_UM
    sim.SetFrequency(1.0 / wl_um)
    # GetPowerFluxByOrder は層境界のポインティングフラックスを基底（次数）ごとに
    # 返す。各要素は (前進波パワー, 後退波パワー)。
    fluxes_top = sim.GetPowerFluxByOrder(S4_Layer=top_name)
    fluxes_bot = sim.GetPowerFluxByOrder(S4_Layer=bottom_name)
    i0 = sim.GetBasisSet().index((0, 0))
    incident = sum(f.real for f, _ in fluxes_top)
    if incident == 0.0:
        return 0.0, 0.0, 0.0
    # Rayleigh 点の発散は高次側に出て 0 次だけ正常に見えることがあるため、
    # 全次数の合計が異常ならそれを返して呼び出し側の _is_anomalous に検出させる。
    total_r = sum(-b.real for _, b in fluxes_top) / incident
    total_t = sum(f.real for f, _ in fluxes_bot) / incident
    if _is_anomalous(total_r, total_t):
        return total_r, total_t, total_r
    return -fluxes_top[i0][1].real / incident, fluxes_bot[i0][0].real / incident, total_r


def _orders_at(
    sim,
    top_name: str,
    wl_nm: float,
    sin_in_xy: tuple[float, float],
    periods_um: tuple[float, float],
) -> tuple[DiffractionOrder, ...] | None:
    wl_um = wl_nm / _NM_PER_UM
    period_um, period_y_um = periods_um
    sin_in, sin_in_y = sin_in_xy
    sim.SetFrequency(1.0 / wl_um)
    fluxes = sim.GetPowerFluxByOrder(S4_Layer=top_name)
    basis = sim.GetBasisSet()
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
    for v in (r, t):
        if math.isnan(v) or v < -0.01 or v > 1.05:
            return True
    return r + t > 1.05


def _set_materials(sim, condition: SimulationCondition, wl_nm: float) -> None:
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
    if condition.is_dispersive:
        _set_materials(sim, condition, wl_nm)


def _epsilon(material: OpticalMaterial, lossy: bool, wl_nm: float) -> complex:
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
