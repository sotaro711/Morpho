"""シミュレーション API のルーター。"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from s4web.application.usecases.run_angle_sweep import RunAngleSweepUseCase
from s4web.application.usecases.run_angular_distribution import (
    RunAngularDistributionUseCase,
)
from s4web.application.usecases.run_simulation import RunSimulationUseCase
from s4web.domain.entities.material import DispersiveMaterial
from s4web.domain.entities.simulation import SimulationCondition
from s4web.domain.ports.colorimetry_port import ColorimetryPort
from s4web.domain.ports.solver_port import SolverPort
from s4web.presentation.auth import AuthenticatedUser, current_user
from s4web.presentation.dependencies import (
    MaterialRepositoryFactory,
    get_colorimetry,
    get_material_repository_factory,
    get_solver,
)
from s4web.presentation.schemas.simulation_dto import (
    OrdersResponse,
    SimulationRequest,
    SimulationResponse,
    SweepRequest,
    SweepResponse,
)

router = APIRouter()
_logger = logging.getLogger(__name__)


User = Annotated[AuthenticatedUser, Depends(current_user)]
Repositories = Annotated[MaterialRepositoryFactory, Depends(get_material_repository_factory)]


def _load_materials(
    request: SimulationRequest, user: AuthenticatedUser, open_repository: MaterialRepositoryFactory
) -> dict[str, DispersiveMaterial]:
    """リクエストが参照する登録済み材料を、ログイン中のユーザーのものから読む。"""
    ids = request.material_ids()
    if not ids:
        return {}
    with open_repository() as repository:
        found = repository.get_many(user.id, ids)
    return {material_id: saved.material for material_id, saved in found.items()}


def _to_condition(
    request: SimulationRequest, user: AuthenticatedUser, open_repository: MaterialRepositoryFactory
) -> SimulationCondition:
    # Pydantic で拾えない不変条件（波長範囲の逆転、見つからない材料など）は domain / DTO が
    # ValueError を出す。
    try:
        return request.to_condition(_load_materials(request, user, open_repository))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _describe(condition: SimulationCondition, user: AuthenticatedUser) -> str:
    """計算時間を左右する条件の要約（ログ用）。基底数と面内パターンの有無が主因。"""
    wls = condition.wavelengths_nm()
    structure = "planar"
    if condition.is_patterned:
        structure = "biperiodic" if condition.is_biperiodic else "grating"
    parts = [
        f"user={user.id[:8]}",
        structure,
        f"layers={len(condition.layers)}",
        f"basis={condition.num_basis}",
        f"wl={wls[0]:g}-{wls[-1]:g}nm/{len(wls)}",
        f"theta={condition.theta_deg:g}",
        f"pol={condition.polarization.value}",
    ]
    if condition.is_dispersive:
        parts.append("dispersive")
    return " ".join(parts)


@router.post("/simulate", response_model=SimulationResponse)
def simulate(
    request: SimulationRequest,
    user: User,
    open_repository: Repositories,
    solver: Annotated[SolverPort, Depends(get_solver)],
    colorimetry: Annotated[ColorimetryPort, Depends(get_colorimetry)],
) -> SimulationResponse:
    condition = _to_condition(request, user, open_repository)
    _logger.info("simulate %s", _describe(condition, user))
    outcome = RunSimulationUseCase(solver, colorimetry).execute(condition)
    return SimulationResponse.from_outcome(outcome)


@router.post("/simulate/orders", response_model=OrdersResponse)
def simulate_orders(
    request: SimulationRequest,
    user: User,
    open_repository: Repositories,
    solver: Annotated[SolverPort, Depends(get_solver)],
) -> OrdersResponse:
    """反射の回折次数ごとの角度分布を返す。平面多層膜では 0 次（正反射）のみ。"""
    condition = _to_condition(request, user, open_repository)
    _logger.info("orders %s", _describe(condition, user))
    distributions = RunAngularDistributionUseCase(solver).execute(condition)
    return OrdersResponse.from_distributions(distributions)


@router.post("/simulate/sweep", response_model=SweepResponse)
def simulate_sweep(
    request: SweepRequest,
    user: User,
    open_repository: Repositories,
    solver: Annotated[SolverPort, Depends(get_solver)],
    colorimetry: Annotated[ColorimetryPort, Depends(get_colorimetry)],
) -> SweepResponse:
    """入射角スイープ。角度ごとの R/T スペクトルと(任意で)反射色を返す。"""
    condition = _to_condition(request, user, open_repository)
    _logger.info(
        "sweep %s angles=%d colors=%s",
        _describe(condition, user),
        len(request.theta_degs),
        request.include_colors,
    )
    entries = RunAngleSweepUseCase(solver, colorimetry).execute(
        condition, tuple(request.theta_degs), request.include_colors
    )
    return SweepResponse.from_entries(entries)
