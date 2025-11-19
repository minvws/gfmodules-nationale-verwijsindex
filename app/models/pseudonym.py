from dataclasses import dataclass
from typing import Any


@dataclass
class Pseudonym:
    def __init__(self, value: Any) -> None:
        self.value = str(value)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Pseudonym({self.value})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Pseudonym):
            return self.value == other.value
        return False
