from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager

from s4web.domain.ports.colorimetry_port import ColorimetryPort
from s4web.domain.ports.material_repository import MaterialRepository
from s4web.domain.ports.result_repository import ResultRepository
from s4web.domain.ports.solver_port import SolverPort


def get_solver() -> SolverPort:
    from s4web.infrastructure.solvers.s4_solver import S4Solver

    return S4Solver()


def get_colorimetry() -> ColorimetryPort:
    from s4web.infrastructure.colorimetry.colour_science import (
        ColourScienceColorimetry,
    )

    return ColourScienceColorimetry()


MaterialRepositoryFactory = Callable[[], AbstractContextManager[MaterialRepository]]


def get_material_repository_factory() -> MaterialRepositoryFactory:
    from s4web.infrastructure.repositories.postgres_material_repository import (
        PostgresMaterialRepository,
        connect,
    )

    @contextmanager
    def open_repository() -> Iterator[MaterialRepository]:
        with connect() as conn:
            yield PostgresMaterialRepository(conn)

    return open_repository


def get_material_repository() -> Iterator[MaterialRepository]:
    with get_material_repository_factory()() as repository:
        yield repository


def get_result_repository() -> ResultRepository:
    from s4web.infrastructure.repositories.firestore_result_repository import (
        FirestoreResultRepository,
        client,
    )

    return FirestoreResultRepository(client())
