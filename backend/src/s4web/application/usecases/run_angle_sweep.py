import logging
import time
from dataclasses import replace

from s4web.domain.entities.simulation import (
    AngleSweepEntry,
    DiffractionMode,
    SimulationCondition,
)
from s4web.domain.ports.colorimetry_port import ColorimetryPort
from s4web.domain.ports.solver_port import SolverPort

_logger = logging.getLogger(__name__)


class RunAngleSweepUseCase:
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
        started = time.perf_counter()
        for i, theta in enumerate(theta_degs, start=1):
            cond = replace(condition, theta_deg=theta)
            angle_started = time.perf_counter()
            spectrum = self._solver.solve(cond)
            now = time.perf_counter()
            _logger.info(
                "sweep theta=%g done %d/%d in %.1fs (total %.1fs)",
                theta,
                i,
                len(theta_degs),
                now - angle_started,
                now - started,
            )
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
