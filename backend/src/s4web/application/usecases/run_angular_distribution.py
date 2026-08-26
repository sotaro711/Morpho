"""角度分布計算ユースケース。"""

from s4web.domain.entities.diffraction import AngularDistribution
from s4web.domain.entities.simulation import SimulationCondition
from s4web.domain.ports.solver_port import SolverPort


class RunAngularDistributionUseCase:
    """ソルバーで回折次数ごとの反射パワーと出射角を計算する。

    スペクトル計算（RunSimulationUseCase）と違い色変換は伴わない。
    """

    def __init__(self, solver: SolverPort) -> None:
        self._solver = solver

    def execute(self, condition: SimulationCondition) -> tuple[AngularDistribution, ...]:
        return self._solver.solve_orders(condition)
