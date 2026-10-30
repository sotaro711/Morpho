"""FirestoreResultRepository。サイズ計算はそのまま、読み書きはエミュレータがあるときだけ試す。

エミュレータ: gcloud emulators firestore start --host-port=localhost:8080
             export FIRESTORE_EMULATOR_HOST=localhost:8080
"""

import logging
import os
from uuid import uuid4

import pytest

from s4web.domain.entities.material import DispersionPoint, DispersiveMaterial
from s4web.domain.entities.saved_result import ResultDraft
from s4web.domain.ports.result_repository import ResultTooLargeError
from s4web.infrastructure.repositories.firestore_result_repository import (
    MAX_DOCUMENT_BYTES,
    FirestoreResultRepository,
    document_size,
)

_TABLE = DispersiveMaterial((DispersionPoint(300, 2.4, 0.1), DispersionPoint(900, 2.2)))


def _draft(points: int = 3) -> ResultDraft:
    return ResultDraft(
        request={"wlMin": 380, "layers": [{"name": "film", "materialId": "m1"}]},
        materials={"m1": _TABLE},
        colors={
            "wavelengths": [380.0] * points,
            "entries": [{"thetaDeg": 0, "R": [0.1] * points, "color": {"hex": "#010203"}}],
        },
        angles={"wavelengths": [400.0], "entries": []},
    )


def test_document_size_follows_firestore_rules() -> None:
    # 名前: "users"(6) + "u"(2) + "results"(8) + "r"(2) + 16 = 34
    # フィールド: "a"(2) + "xy"(3) / "b"(2) + 数値 2 つ(16) / "c"(2) + {"d"(2) + true(1)}
    assert document_size("users/u/results/r", {"a": "xy", "b": [1, 2.5], "c": {"d": True}}) == (
        34 + (2 + 3) + (2 + 16) + (2 + 2 + 1) + 32
    )


needs_emulator = pytest.mark.skipif(
    not os.environ.get("FIRESTORE_EMULATOR_HOST"), reason="Firestore エミュレータが無い"
)


@pytest.fixture
def repository() -> FirestoreResultRepository:
    from google.cloud import firestore

    return FirestoreResultRepository(firestore.Client(project="demo-morpho"))


@needs_emulator
def test_round_trip_and_newest_first(repository: FirestoreResultRepository) -> None:
    owner = str(uuid4())
    first = repository.add(owner, _draft())
    second = repository.add(owner, _draft())

    summaries = repository.list_for(owner, 10)
    assert [r.id for r in summaries] == [second.id, first.id]
    assert summaries[0].colors == ({"thetaDeg": 0, "color": {"hex": "#010203"}},)
    assert [r.id for r in repository.list_for(owner, 1)] == [second.id]
    loaded = repository.get(owner, first.id)
    assert loaded is not None
    assert loaded.draft == first.draft


@needs_emulator
def test_owner_cannot_see_others_results(repository: FirestoreResultRepository) -> None:
    saved = repository.add(str(uuid4()), _draft())
    other = str(uuid4())

    assert repository.get(other, saved.id) is None
    assert repository.list_for(other, 10) == ()
    assert repository.delete(other, saved.id) is False


@needs_emulator
def test_delete(repository: FirestoreResultRepository) -> None:
    owner = str(uuid4())
    saved = repository.add(owner, _draft())

    assert repository.delete(owner, saved.id) is True
    assert repository.get(owner, saved.id) is None
    assert repository.delete(owner, saved.id) is False


@needs_emulator
def test_rejects_documents_over_the_limit(repository: FirestoreResultRepository) -> None:
    owner = str(uuid4())
    with pytest.raises(ResultTooLargeError):
        repository.add(owner, _draft(points=MAX_DOCUMENT_BYTES // 8))
    assert repository.list_for(owner, 10) == ()


class _FakeRef:
    def __init__(self) -> None:
        self.id = "r1"
        self.path = "users/u/results/r1"
        self.data: dict | None = None

    def set(self, data: dict) -> None:
        self.data = data


class _FakeDb:
    """エミュレータなしで add() のログを確かめるための最小限の Client。"""

    def __init__(self) -> None:
        self.ref = _FakeRef()

    def collection(self, *_: str):
        return self

    def document(self) -> _FakeRef:
        return self.ref


def test_add_logs_size_and_duration(caplog: pytest.LogCaptureFixture) -> None:
    db = _FakeDb()
    with caplog.at_level(logging.INFO):
        saved = FirestoreResultRepository(db).add("user-1", _draft())  # type: ignore[arg-type]
    assert saved.id == "r1" and db.ref.data is not None
    messages = [r.getMessage() for r in caplog.records]
    assert len(messages) == 1
    assert messages[0].startswith("saved result r1: ")
    assert "bytes (0% of limit) in " in messages[0]


def test_too_large_result_is_logged_as_warning(caplog: pytest.LogCaptureFixture) -> None:
    db = _FakeDb()
    with caplog.at_level(logging.WARNING), pytest.raises(ResultTooLargeError):
        FirestoreResultRepository(db).add("user-1", _draft(points=200_000))  # type: ignore[arg-type]
    assert db.ref.data is None
    assert caplog.records[0].getMessage().startswith("result too large: ")
    assert caplog.records[0].getMessage().endswith("owner=user-1")
