"""シミュレーション API のルーター。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from s4web.application.usecases.run_angular_distribution import (
    RunAngularDistributionUseCase,
)
from s4web.application.usecases.run_simulation import RunSimulationUseCase
from s4web.domain.entities.simulation import SimulationCondition
from s4web.domain.ports.colorimetry_port import ColorimetryPort
from s4web.domain.ports.solver_port import SolverPort
from s4web.presentation.dependencies import get_colorimetry, get_solver
from s4web.presentation.schemas.simulation_dto import (
    OrdersResponse,
    SimulationRequest,
    SimulationResponse,
)

router = APIRouter()


def _to_condition(request: SimulationRequest) -> SimulationCondition:
    # Pydantic で拾えない不変条件（波長範囲の逆転など）は domain が ValueError を出す。
    try:
        return request.to_condition()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/simulate", response_model=SimulationResponse)
def simulate(
    request: SimulationRequest,
    solver: Annotated[SolverPort, Depends(get_solver)],
    colorimetry: Annotated[ColorimetryPort, Depends(get_colorimetry)],
) -> SimulationResponse:
    outcome = RunSimulationUseCase(solver, colorimetry).execute(_to_condition(request))
    return SimulationResponse.from_outcome(outcome)


@router.post("/simulate/orders", response_model=OrdersResponse)
def simulate_orders(
    request: SimulationRequest,
    solver: Annotated[SolverPort, Depends(get_solver)],
) -> OrdersResponse:
    """反射の回折次数ごとの角度分布を返す。平面多層膜では 0 次（正反射）のみ。"""
    distributions = RunAngularDistributionUseCase(solver).execute(_to_condition(request))
    return OrdersResponse.from_distributions(distributions)
