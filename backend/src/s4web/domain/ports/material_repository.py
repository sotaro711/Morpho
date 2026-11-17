from abc import ABC, abstractmethod

from s4web.domain.entities.saved_material import MaterialDraft, SavedMaterial


class DuplicateMaterialNameError(Exception): ...


class MaterialRepository(ABC):
    @abstractmethod
    def list_for(self, owner_id: str) -> tuple[SavedMaterial, ...]:
        raise NotImplementedError

    @abstractmethod
    def get(self, owner_id: str, material_id: str) -> SavedMaterial | None:
        raise NotImplementedError

    @abstractmethod
    def get_many(self, owner_id: str, material_ids: set[str]) -> dict[str, SavedMaterial]:
        raise NotImplementedError

    @abstractmethod
    def create(self, owner_id: str, draft: MaterialDraft) -> SavedMaterial:
        raise NotImplementedError

    @abstractmethod
    def rename(self, owner_id: str, material_id: str, name: str) -> SavedMaterial | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, owner_id: str, material_id: str) -> bool:
        raise NotImplementedError
