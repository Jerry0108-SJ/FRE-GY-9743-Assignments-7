"""Long and short product directions."""

from enum import Enum

__all__ = ["LongOrShort", "PayOrReceive"]


class LongOrShort(Enum):
    LONG = "long"
    SHORT = "short"

    @classmethod
    def from_string(cls, value: str) -> "LongOrShort":
        return cls(value.lower())

    def to_string(self) -> str:
        return self.value


class PayOrReceive(Enum):
    """Direction of the fixed leg, or leg 1 of a basis swap (template convention)."""

    PAY = "pay"
    RECEIVE = "receive"

    @classmethod
    def from_string(cls, value: str) -> "PayOrReceive":
        return cls(value.lower())

    def to_string(self) -> str:
        return self.value
