from typing import Any

from pydantic import BaseModel, field_validator, field_serializer

from app.data import UraNumber, Pseudonym, DataDomain

class ReferralRequest(BaseModel):
    pseudonym: Pseudonym
    data_domain: DataDomain

    @field_validator('pseudonym', mode='before')
    @classmethod
    def serialize_pseudonym(cls, val: str) -> Pseudonym:
        return Pseudonym(val)

    @field_validator('data_domain', mode='before')
    @classmethod
    def serialize_dd(cls, val: str) -> DataDomain:
        return DataDomain(val)


class CreateReferralRequest(BaseModel):
    pseudonym: Pseudonym
    data_domain: DataDomain
    ura_number: UraNumber

    @field_validator('pseudonym', mode='before')
    @classmethod
    def serialize_pseudo(cls, val: str) -> Pseudonym:
        return Pseudonym(val)

    @field_validator('data_domain', mode='before')
    @classmethod
    def serialize_dd(cls, val: str) -> DataDomain:
        return DataDomain(val)

    @field_validator('ura_number', mode='before')
    @classmethod
    def serialize_ura(cls, val: str) -> UraNumber:
        return UraNumber(val)
    
class UpdateReferralRequest(BaseModel):
    pseudonym: Pseudonym
    data_domain: DataDomain
    ura_number: UraNumber

    @field_validator('pseudonym', mode='before')
    @classmethod
    def serialize_pseudo(cls, val: str) -> Pseudonym:
        return Pseudonym(val)

    @field_validator('data_domain', mode='before')
    @classmethod
    def serialize_dd(cls, val: str) -> DataDomain:
        return DataDomain(val)

    @field_validator('ura_number', mode='before')
    @classmethod
    def serialize_ura(cls, val: str) -> UraNumber:
        return UraNumber(val)



class ReferralEntry(BaseModel):
    ura_number: UraNumber
    pseudonym: Pseudonym
    data_domain: DataDomain

    @field_serializer('ura_number')
    def serialize_pi(self, ura_number: UraNumber) -> str:
        return str(ura_number)

    @field_serializer('data_domain')
    def serialize_dd(self, data_domain: DataDomain, _info: Any) -> str:
        return str(data_domain)

    @field_serializer('pseudonym')
    def serialize_ps(self, pseudonym: Pseudonym, _info: Any) -> str:
        return str(pseudonym)
