from typing import Any, Optional

from pydantic import BaseModel, field_serializer, field_validator

from app.data import Pseudonym, UraNumber


class ReferralRequest(BaseModel):
    pseudonym: Pseudonym
    data_domain: str

    @field_validator("pseudonym", mode="before")
    @classmethod
    def serialize_pseudonym(cls, val: str) -> Pseudonym:
        return Pseudonym(val)


class ReferralRequestHeader(BaseModel):
    authorization: str


class CreateReferralRequest(BaseModel):
    pseudonym: Pseudonym
    data_domain: str
    ura_number: UraNumber
    requesting_uzi_number: str

    @field_validator("pseudonym", mode="before")
    @classmethod
    def serialize_pseudo(cls, val: str) -> Pseudonym:
        return Pseudonym(val)

    @field_validator("ura_number", mode="before")
    @classmethod
    def serialize_ura(cls, val: str) -> UraNumber:
        return UraNumber(val)


class DeleteReferralRequest(CreateReferralRequest):
    pass


class ReferralEntry(BaseModel):
    pseudonym: Pseudonym
    data_domain: str
    ura_number: UraNumber

    @field_serializer("ura_number")
    def serialize_pi(self, ura_number: UraNumber) -> str:
        return str(ura_number)

    @field_serializer("pseudonym")
    def serialize_ps(self, pseudonym: Pseudonym, _info: Any) -> str:
        return str(pseudonym)


class ReferralQuery(BaseModel):
    pseudonym: Optional[Pseudonym] = None
    data_domain: Optional[str] = None
    ura_number: UraNumber

    @field_validator("pseudonym", mode="before")
    @classmethod
    def serialize_pseudo(cls, val: Optional[str]) -> Optional[Pseudonym]:
        return None if val is None else Pseudonym(val)

    @field_validator("ura_number", mode="before")
    @classmethod
    def serialize_ura(cls, val: str) -> UraNumber:
        return UraNumber(val)
