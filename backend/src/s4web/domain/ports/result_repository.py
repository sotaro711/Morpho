from abc import ABC, abstractmethod

from s4web.domain.entities.saved_result import ResultDraft, ResultSummary, SavedResult


class ResultTooLargeError(Exception): ...


class ResultRepository(ABC):
    @abstractmethod
    def list_for(self, owner_id: str, limit: int) -> tuple[ResultSummary, ...]:
        raise NotImplementedError

    @abstractmethod
    def get(self, owner_id: str, result_id: str) -> SavedResult | None:
        raise NotImplementedError

    @abstractmethod
    def add(self, owner_id: str, draft: ResultDraft) -> SavedResult:
        raise NotImplementedError

    @abstractmethod
    def delete(self, owner_id: str, result_id: str) -> bool:
        raise NotImplementedError
