from dataclasses import dataclass


@dataclass(frozen=True)
class ColorResult:
    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        for c in (self.r, self.g, self.b):
            if not (0 <= c <= 255):
                raise ValueError(f"sRGB component must be in [0, 255], got {c}")

    @property
    def hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
