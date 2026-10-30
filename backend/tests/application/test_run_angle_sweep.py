"""RunAngleSweepUseCase。角度ごとに結果を積み、進捗をログに出すことを確かめる。"""

import logging
from collections.abc import Sequence

import pytest

from s4web.application.usecases.run_angle_sweep import RunAngleSweepUseCase
from s4web.domain.entities.color import ColorResult
from s4web.domain.entities.diffraction import AngularDistribution
from s4web.domain.entities.layer import Layer
from s4web.domain.entities.material import Material
from s4web.domain.entities.simulation import Polarization, SimulationCondition, Spectrum
from s4web.domain.ports.colorimetry_port import ColorimetryPort
from s4web.domain.ports.solver_port import SolverPort


class _FixedSolver(SolverPort):
    def __init__(self) -> None:
        self.thetas: list[float] = []

    def solve(self, condition: SimulationCondition) -> Spectrum:
        self.thetas.append(condition.theta_deg)
        wls = tuple(condition.wavelengths_nm())
        return Spectrum(wls, (0.5,) * len(wls), (0.5,) * len(wls), (0.6,) * len(wls))

    def solve_orders(self, condition: SimulationCondition) -> tuple[AngularDistribution, ...]:
        raise NotImplementedError


class _GrayColorimetry(ColorimetryPort):
    def reflectance_to_srgb(
        self, wavelengths_nm: Sequence[float], reflectance: Sequence[float]
    ) -> ColorResult:
        return ColorResult(128, 128, 128)


_CONDITION = SimulationCondition(
    wl_min_nm=400,
    wl_max_nm=700,
    wl_points=4,
    theta_deg=0.0,
    polarization=Polarization.S,
    layers=(Layer("air", 0, Material(1.0)), Layer("sub", 0, Material(1.5))),
)


def test_sweeps_each_angle_and_logs_progress(caplog: pytest.LogCaptureFixture) -> None:
    solver = _FixedSolver()
    with caplog.at_level(logging.INFO):
        entries = RunAngleSweepUseCase(solver, _GrayColorimetry()).execute(
            _CONDITION, (0.0, 30.0, 60.0), include_colors=True
        )

    assert solver.thetas == [0.0, 30.0, 60.0]
    assert [e.theta_deg for e in entries] == [0.0, 30.0, 60.0]
    assert entries[0].reflected_color == ColorResult(128, 128, 128)
    assert entries[0].total_color == ColorResult(128, 128, 128)

    messages = [r.getMessage() for r in caplog.records]
    assert len(messages) == 3
    assert messages[0].startswith("sweep theta=0 done 1/3 in ")
    assert messages[2].startswith("sweep theta=60 done 3/3 in ")


def test_colors_are_omitted_when_not_requested() -> None:
    entries = RunAngleSweepUseCase(_FixedSolver(), _GrayColorimetry()).execute(
        _CONDITION, (10.0,), include_colors=False
    )
    assert entries[0].reflected_color is None
    assert entries[0].total_color is None
