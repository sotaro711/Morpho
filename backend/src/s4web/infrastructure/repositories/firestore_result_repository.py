"""Firestore の users/{owner}/results/{id} を使う ResultRepository の実装。

所有者ごとのサブコレクションに置くので、他人の結果はパスの時点で届かない。
Cloud Run ではサービスアカウントの権限で、ローカルでは FIRESTORE_EMULATOR_HOST の
エミュレータか gcloud の Application Default Credentials で接続する。
"""

import os
from collections.abc import Mapping
from datetime import UTC, datetime
from functools import cache
from typing import Any

from google.cloud import firestore

from s4web.domain.entities.material import DispersionPoint, DispersiveMaterial
from s4web.domain.entities.saved_result import ResultDraft, SavedResult
from s4web.domain.ports.result_repository import ResultRepository, ResultTooLargeError

# Firestore の 1 ドキュメントの上限。
# https://firebase.google.com/docs/firestore/quotas#collections_documents_and_fields
MAX_DOCUMENT_BYTES = 1_048_576


def ensure_firestore_configured() -> None:
    """GOOGLE_CLOUD_PROJECT が設定されているかを確かめる。未設定なら RuntimeError。"""
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        raise RuntimeError("GOOGLE_CLOUD_PROJECT が設定されていません")


@cache
def client() -> firestore.Client:
    # クライアントは接続を内部で使い回すので、リクエストごとに作らず 1 つを共有する。
    ensure_firestore_configured()
    return firestore.Client(project=os.environ["GOOGLE_CLOUD_PROJECT"])


class FirestoreResultRepository(ResultRepository):
    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def _results(self, owner_id: str) -> firestore.CollectionReference:
        return self._db.collection("users", owner_id, "results")

    def list_for(self, owner_id: str) -> tuple[SavedResult, ...]:
        query = self._results(owner_id).order_by("createdAt", direction=firestore.Query.DESCENDING)
        return tuple(_to_entity(doc.id, doc.to_dict() or {}) for doc in query.stream())

    def get(self, owner_id: str, result_id: str) -> SavedResult | None:
        doc = self._results(owner_id).document(result_id).get()
        return _to_entity(doc.id, doc.to_dict() or {}) if doc.exists else None

    def add(self, owner_id: str, draft: ResultDraft) -> SavedResult:
        ref = self._results(owner_id).document()
        data = _to_document(draft, datetime.now(UTC))
        size = document_size(ref.path, data)
        if size > MAX_DOCUMENT_BYTES:
            raise ResultTooLargeError(f"{size} bytes > {MAX_DOCUMENT_BYTES} bytes")
        ref.set(data)
        return SavedResult(id=ref.id, draft=draft, created_at=data["createdAt"])

    def delete(self, owner_id: str, result_id: str) -> bool:
        ref = self._results(owner_id).document(result_id)
        # delete は存在しなくても成功するので、有無は先に読んで確かめる。
        if not ref.get().exists:
            return False
        ref.delete()
        return True


def _to_document(draft: ResultDraft, created_at: datetime) -> dict[str, Any]:
    return {
        "createdAt": created_at,
        "request": dict(draft.request),
        "materials": {
            material_id: {
                "wavelengthsNm": [p.wavelength_nm for p in material.points],
                "n": [p.n for p in material.points],
                "k": [p.k for p in material.points],
            }
            for material_id, material in draft.materials.items()
        },
        "colors": dict(draft.colors),
        "angles": dict(draft.angles),
    }


def _to_entity(result_id: str, data: Mapping[str, Any]) -> SavedResult:
    materials = {
        material_id: DispersiveMaterial(
            tuple(
                DispersionPoint(w, n, k)
                for w, n, k in zip(table["wavelengthsNm"], table["n"], table["k"], strict=True)
            )
        )
        for material_id, table in data["materials"].items()
    }
    draft = ResultDraft(
        request=data["request"], materials=materials, colors=data["colors"], angles=data["angles"]
    )
    return SavedResult(id=result_id, draft=draft, created_at=data["createdAt"])


def document_size(path: str, data: Mapping[str, Any]) -> int:
    """Firestore の計算方法でのドキュメントのサイズ（バイト）。

    https://firebase.google.com/docs/firestore/storage-size
    数値は 8 バイトなので、同じ中身でも JSON の文字数よりかなり小さくなる。
    """
    name = sum(_string_size(segment) for segment in path.split("/")) + 16
    return name + _map_size(data) + 32


def _string_size(value: str) -> int:
    return len(value.encode()) + 1


def _map_size(value: Mapping[str, Any]) -> int:
    return sum(_string_size(key) + _value_size(v) for key, v in value.items())


def _value_size(value: Any) -> int:
    if isinstance(value, str):
        return _string_size(value)
    if isinstance(value, Mapping):
        return _map_size(value)
    if isinstance(value, list | tuple):
        return sum(_value_size(v) for v in value)
    if value is None or isinstance(value, bool):
        return 1
    # int / float / datetime
    return 8
