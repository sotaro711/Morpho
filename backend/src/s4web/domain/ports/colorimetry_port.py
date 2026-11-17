from abc import ABC, abstractmethod
from collections.abc import Sequence

from s4web.domain.entities.color import ColorResult


class ColorimetryPort(ABC):
    @abstractmethod
    def reflectance_to_srgb(
        self,
        wavelengths_nm: Sequence[float],
        reflectance: Sequence[float],
    ) -> ColorResult:
        raise NotImplementedError
