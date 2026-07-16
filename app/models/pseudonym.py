from dataclasses import dataclass
from typing import Any, Self

from pydantic import BaseModel


class PseudonymResponse(BaseModel):
    encrypted_pseudonym: str
    iv: str


@dataclass
class EncryptedPseudonym:
    """
    An encrypted Pseudoym that consists of the encrypted data and the iv used to create this encryption.
    The iv is always 16 byte.

    Returned value is always: iv + encrypted_data.
    """

    def __init__(self, encrypted_data: Any, iv: Any) -> None:
        self.encrypted_data = str(encrypted_data)
        self.iv = str(iv)
        # value consists of iv (16 byte) + encrypted pseudonym
        self.value = self.iv + self.encrypted_data

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"EncryptedPseudonym({self.value})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, EncryptedPseudonym):
            return self.value == other.value
        return False

    @classmethod
    def from_response(cls, resp: PseudonymResponse) -> Self:
        return cls(encrypted_data=resp.encrypted_pseudonym, iv=resp.iv)
