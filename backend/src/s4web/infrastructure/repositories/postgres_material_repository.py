"""Supabase Postgres の materials テーブルを使う MaterialRepository の実装。

接続は Supavisor（Supabase の接続プーラー）のトランザクションモードを想定する。
このモードは接続を文ごとに使い回すため、サーバー側のプリペアドステートメントを使えない
（prepare_threshold=None で無効にする）。
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import psycopg

from s4web.domain.entities.material import DispersionPoint, DispersiveMaterial
from s4web.domain.entities.saved_material import MaterialDraft, SavedMaterial
from s4web.domain.ports.material_repository import (
    DuplicateMaterialNameError,
    MaterialRepository,
)

_COLUMNS = "id, name, wavelengths_nm, n, k, created_at"


def ensure_database_configured() -> None:
    """DATABASE_URL が設定されているかを確かめる。未設定なら RuntimeError。"""
    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL が設定されていません")


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    ensure_database_configured()
    with psycopg.connect(
        os.environ["DATABASE_URL"], autocommit=True, prepare_threshold=None
    ) as conn:
        yield conn


class PostgresMaterialRepository(MaterialRepository):
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def list_for(self, owner_id: str) -> tuple[SavedMaterial, ...]:
        rows = self._conn.execute(
            f"select {_COLUMNS} from public.materials where owner = %s order by name",
            (owner_id,),
        ).fetchall()
        return tuple(_to_entity(*row) for row in rows)

    def get(self, owner_id: str, material_id: str) -> SavedMaterial | None:
        row = self._conn.execute(
            f"select {_COLUMNS} from public.materials where owner = %s and id = %s",
            (owner_id, material_id),
        ).fetchone()
        return _to_entity(*row) if row else None

    def get_many(self, owner_id: str, material_ids: set[str]) -> dict[str, SavedMaterial]:
        if not material_ids:
            return {}
        rows = self._conn.execute(
            f"select {_COLUMNS} from public.materials where owner = %s and id = any(%s)",
            (owner_id, list(material_ids)),
        ).fetchall()
        return {str(row[0]): _to_entity(*row) for row in rows}

    def create(self, owner_id: str, draft: MaterialDraft) -> SavedMaterial:
        wavelengths, n, k = _columns(draft.material)
        try:
            row = self._conn.execute(
                "insert into public.materials (owner, name, wavelengths_nm, n, k)"
                " values (%s, %s, %s, %s, %s) returning id, created_at",
                (owner_id, draft.name, wavelengths, n, k),
            ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise DuplicateMaterialNameError(draft.name) from exc
        assert row is not None  # insert ... returning は必ず 1 行返す
        material_id, created_at = row
        return SavedMaterial(
            id=str(material_id), name=draft.name, material=draft.material, created_at=created_at
        )

    def rename(self, owner_id: str, material_id: str, name: str) -> SavedMaterial | None:
        try:
            row = self._conn.execute(
                "update public.materials set name = %s where owner = %s and id = %s"
                f" returning {_COLUMNS}",
                (name, owner_id, material_id),
            ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise DuplicateMaterialNameError(name) from exc
        return _to_entity(*row) if row else None

    def delete(self, owner_id: str, material_id: str) -> bool:
        cur = self._conn.execute(
            "delete from public.materials where owner = %s and id = %s",
            (owner_id, material_id),
        )
        return cur.rowcount > 0


def _columns(material: DispersiveMaterial) -> tuple[list[float], list[float], list[float]]:
    points = material.points
    return (
        [p.wavelength_nm for p in points],
        [p.n for p in points],
        [p.k for p in points],
    )


def _to_entity(
    material_id: Any,
    name: str,
    wavelengths: list[float],
    n: list[float],
    k: list[float],
    created_at: datetime,
) -> SavedMaterial:
    points = tuple(DispersionPoint(w, nn, kk) for w, nn, kk in zip(wavelengths, n, k, strict=True))
    return SavedMaterial(
        id=str(material_id), name=name, material=DispersiveMaterial(points), created_at=created_at
    )
