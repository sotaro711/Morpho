"""入射角スイープユースケース。"""

from dataclasses import replace

from s4web.domain.entities.simulation import (
    AngleSweepEntry,
    DiffractionMode,
    SimulationCondition,
)
from s4web.domain.ports.colorimetry_port import ColorimetryPort
from s4web.domain.ports.solver_port import SolverPort


class RunAngleSweepUseCase:
    """入射角を掃引し、角度ごとの R/T スペクトル(と任意で反射色)を計算する。

    研究スライドの「見た目の色(0/30/60°)」「角度スイープ」「角度別スペクトル」は
    すべてこの結果から描ける。include_colors=False は、波長間隔が色変換に
    適さない粗い掃引(角度スイープチャート用)のためにある。
    """

    def __init__(self, solver: SolverPort, colorimetry: ColorimetryPort) -> None:
        self._solver = solver
        self._colorimetry = colorimetry

    def execute(
        self,
        condition: SimulationCondition,
        theta_degs: tuple[float, ...],
        include_colors: bool,
    ) -> tuple[AngleSweepEntry, ...]:
        entries: list[AngleSweepEntry] = []
        for theta in theta_degs:
            # frozen な条件は replace で角度だけ差し替える(検証も再実行される)。
            cond = replace(condition, theta_deg=theta)
            spectrum = self._solver.solve(cond)
            if not include_colors:
                entries.append(
                    AngleSweepEntry(theta_deg=theta, spectrum=spectrum, reflected_color=None)
                )
                continue
            wls = spectrum.wavelengths_nm
            color = self._colorimetry.reflectance_to_srgb(wls, spectrum.reflectance)
            non_zeroth_color = total_color = None
            if spectrum.reflectance_total is not None:
                non_zeroth_color = self._colorimetry.reflectance_to_srgb(
                    wls, spectrum.reflectance_for(DiffractionMode.NON_ZEROTH)
                )
                total_color = self._colorimetry.reflectance_to_srgb(
                    wls, spectrum.reflectance_for(DiffractionMode.TOTAL)
                )
            entries.append(
                AngleSweepEntry(
                    theta_deg=theta,
                    spectrum=spectrum,
                    reflected_color=color,
                    non_zeroth_color=non_zeroth_color,
                    total_color=total_color,
                )
            )
        return tuple(entries)
