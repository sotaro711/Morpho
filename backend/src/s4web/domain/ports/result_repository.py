"""保存した計算結果のリポジトリ（抽象）。

infrastructure 層のアダプタ（Firestore など）がこれを実装する。
すべての操作は所有者（ログイン中のユーザー）で絞り込み、他人の結果には触れない。
"""

from abc import ABC, abstractmethod

from s4web.domain.entities.saved_result import ResultDraft, ResultSummary, SavedResult


class ResultTooLargeError(Exception):
    """保存先の 1 件あたりの上限を超える。"""


class ResultRepository(ABC):
    @abstractmethod
    def list_for(self, owner_id: str, limit: int) -> tuple[ResultSummary, ...]:
        """所有者の結果の要約を、新しい順に limit 件まで返す。"""
        raise NotImplementedError

    @abstractmethod
    def get(self, owner_id: str, result_id: str) -> SavedResult | None:
        """所有者の結果を 1 つ返す。無ければ None。"""
        raise NotImplementedError

    @abstractmethod
    def add(self, owner_id: str, draft: ResultDraft) -> SavedResult:
        """結果を保存して返す。上限を超えれば ResultTooLargeError。"""
        raise NotImplementedError

    @abstractmethod
    def delete(self, owner_id: str, result_id: str) -> bool:
        """結果を削除する。所有者の結果として存在しなければ False。"""
        raise NotImplementedError
