from abc import ABC, abstractmethod

from s4web.domain.entities.diffraction import AngularDistribution
from s4web.domain.entities.simulation import SimulationCondition, Spectrum


class SolverPort(ABC):
    @abstractmethod
    def solve(self, condition: SimulationCondition) -> Spectrum:
        raise NotImplementedError

    @abstractmethod
    def solve_orders(self, condition: SimulationCondition) -> tuple[AngularDistribution, ...]:
        raise NotImplementedError
