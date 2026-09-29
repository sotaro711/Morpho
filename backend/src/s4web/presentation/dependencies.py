"""DI（依存性注入）。SolverPort の実装をここで1か所だけ選ぶ。

テストでは app.dependency_overrides[get_solver] で差し替えられる。

S4 の import を関数内に閉じ込めることで、S4 未導入の環境（CI など）でも
アプリ本体や API は import できる（ソルバーを差し替えれば動作する）。
"""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager

from s4web.domain.ports.colorimetry_port import ColorimetryPort
from s4web.domain.ports.material_repository import MaterialRepository
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
    """必要なときだけ DB 接続を開くための工場。

    計算 API は登録した材料を参照しないリクエストが大半なので、依存解決の時点では
    接続を開かず、材料 id があるときにだけ呼び出し側が開く。
    """
    from s4web.infrastructure.repositories.postgres_material_repository import (
        PostgresMaterialRepository,
        connect,
    )

    @contextmanager
    def open_repository() -> Iterator[MaterialRepository]:
        # 接続はリクエストごとに開いて閉じる。プールは Supabase 側の Supavisor が担う。
        with connect() as conn:
            yield PostgresMaterialRepository(conn)

    return open_repository


def get_material_repository() -> Iterator[MaterialRepository]:
    with get_material_repository_factory()() as repository:
        yield repository
