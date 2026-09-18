"""シミュレーション実行ユースケース。"""

from s4web.domain.entities.simulation import (
    DiffractionMode,
    SimulationCondition,
    SimulationOutcome,
)
from s4web.domain.ports.colorimetry_port import ColorimetryPort
from s4web.domain.ports.solver_port import SolverPort


class RunSimulationUseCase:
    """ソルバーで R/T を計算し、反射スペクトルから色を求める。"""

    def __init__(self, solver: SolverPort, colorimetry: ColorimetryPort) -> None:
        self._solver = solver
        self._colorimetry = colorimetry

    def execute(self, condition: SimulationCondition) -> SimulationOutcome:
        spectrum = self._solver.solve(condition)
        if len(spectrum.wavelengths_nm) != condition.wl_points:
            raise RuntimeError(
                "solver returned a spectrum whose length "
                f"({len(spectrum.wavelengths_nm)}) does not match the "
                f"requested wl_points ({condition.wl_points})"
            )
        wls = spectrum.wavelengths_nm
        reflected_color = self._colorimetry.reflectance_to_srgb(wls, spectrum.reflectance)
        if spectrum.reflectance_total is None:
            return SimulationOutcome(spectrum=spectrum, reflected_color=reflected_color)
        return SimulationOutcome(
            spectrum=spectrum,
            reflected_color=reflected_color,
            non_zeroth_color=self._colorimetry.reflectance_to_srgb(
                wls, spectrum.reflectance_for(DiffractionMode.NON_ZEROTH)
            ),
            total_color=self._colorimetry.reflectance_to_srgb(
                wls, spectrum.reflectance_for(DiffractionMode.TOTAL)
            ),
        )
