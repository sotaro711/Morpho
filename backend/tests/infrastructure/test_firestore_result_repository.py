"""FirestoreResultRepository。サイズ計算はそのまま、読み書きはエミュレータがあるときだけ試す。

エミュレータ: gcloud emulators firestore start --host-port=localhost:8080
             export FIRESTORE_EMULATOR_HOST=localhost:8080
"""

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
        colors={"wavelengths": [380.0] * points, "entries": [{"thetaDeg": 0, "R": [0.1] * points}]},
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

    assert [r.id for r in repository.list_for(owner)] == [second.id, first.id]
    loaded = repository.get(owner, first.id)
    assert loaded is not None
    assert loaded.draft == first.draft


@needs_emulator
def test_owner_cannot_see_others_results(repository: FirestoreResultRepository) -> None:
    saved = repository.add(str(uuid4()), _draft())
    other = str(uuid4())

    assert repository.get(other, saved.id) is None
    assert repository.list_for(other) == ()
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
    assert repository.list_for(owner) == ()
