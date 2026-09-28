"""保存した材料のリポジトリ（抽象）。

infrastructure 層のアダプタ（Postgres など）がこれを実装する。
すべての操作は所有者（ログイン中のユーザー）で絞り込み、他人の材料には触れない。
"""

from abc import ABC, abstractmethod

from s4web.domain.entities.saved_material import MaterialDraft, SavedMaterial


class DuplicateMaterialNameError(Exception):
    """同じ所有者のもとに同名の材料がすでにある。"""


class MaterialRepository(ABC):
    @abstractmethod
    def list_for(self, owner_id: str) -> tuple[SavedMaterial, ...]:
        """所有者の材料を名前順で返す。"""
        raise NotImplementedError

    @abstractmethod
    def get(self, owner_id: str, material_id: str) -> SavedMaterial | None:
        """所有者の材料を 1 つ返す。無ければ None。"""
        raise NotImplementedError

    @abstractmethod
    def get_many(self, owner_id: str, material_ids: set[str]) -> dict[str, SavedMaterial]:
        """所有者の材料をまとめて返す。見つからない id は結果に含めない。"""
        raise NotImplementedError

    @abstractmethod
    def create(self, owner_id: str, draft: MaterialDraft) -> SavedMaterial:
        """材料を保存して返す。同名があれば DuplicateMaterialNameError。"""
        raise NotImplementedError

    @abstractmethod
    def rename(self, owner_id: str, material_id: str, name: str) -> SavedMaterial | None:
        """材料の名前を変えて返す。無ければ None。同名があれば DuplicateMaterialNameError。"""
        raise NotImplementedError

    @abstractmethod
    def delete(self, owner_id: str, material_id: str) -> bool:
        """材料を削除する。所有者の材料として存在しなければ False。"""
        raise NotImplementedError
