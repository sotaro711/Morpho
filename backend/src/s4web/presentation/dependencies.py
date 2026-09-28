"""DI（依存性注入）。SolverPort の実装をここで1か所だけ選ぶ。

テストでは app.dependency_overrides[get_solver] で差し替えられる。

S4 の import を関数内に閉じ込めることで、S4 未導入の環境（CI など）でも
アプリ本体や API は import できる（ソルバーを差し替えれば動作する）。
"""

from collections.abc import Iterator

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


def get_material_repository() -> Iterator[MaterialRepository]:
    # 接続はリクエストごとに開いて閉じる。プールは Supabase 側の Supavisor が担う。
    from s4web.infrastructure.repositories.postgres_material_repository import (
        PostgresMaterialRepository,
        connect,
    )

    with connect() as conn:
        yield PostgresMaterialRepository(conn)
