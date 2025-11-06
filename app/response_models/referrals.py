from typing import Any, Optional

from pydantic import BaseModel, field_serializer, field_validator, model_validator

from app.data import DataDomain, Pseudonym, UraNumber


class ReferralRequest(BaseModel):
    oprf_jwe: str
    blind_factor: str
    data_domain: DataDomain

    @field_validator("data_domain", mode="before")
    @classmethod
    def serialize_data_domain(cls, val: str) -> DataDomain:
        return DataDomain(value=val)


class ReferralRequestHeader(BaseModel):
    authorization: str


class CreateReferralRequest(ReferralRequest):
    ura_number: UraNumber
    requesting_uzi_number: str
    encrypted_lmr_id: str
    lmr_endpoint: str

    @field_validator("ura_number", mode="before")
    @classmethod
    def serialize_ura(cls, val: str) -> UraNumber:
        return UraNumber(val)


class DeleteReferralRequest(CreateReferralRequest):
    pass


class ReferralEntry(BaseModel):
    pseudonym: Pseudonym
    data_domain: DataDomain
    ura_number: UraNumber
    encrypted_lmr_id: str
    lmr_endpoint: str

    @field_serializer("ura_number")
    def serialize_pi(self, ura_number: UraNumber) -> str:
        return str(ura_number)

    @field_serializer("pseudonym")
    def serialize_pseudonym(self, pseudonym: Pseudonym) -> str:
        return str(pseudonym)

    @field_serializer("data_domain")
    def serialize_data_domain(self, data_domain: DataDomain) -> str:
        return str(data_domain)


class ReferralQuery(BaseModel):
    oprf_jwe: Optional[str] = None
    blind_factor: Optional[str] = None
    data_domain: Optional[DataDomain] = None
    ura_number: UraNumber

    @model_validator(mode="after")
    @classmethod
    def both_or_none(cls, values: Any) -> Any:
        oprf_jwe = values.oprf_jwe
        blind_factor = values.blind_factor

        if (oprf_jwe is None) != (blind_factor is None):
            raise ValueError("Both 'oprf_jwe' and 'blind_factor' must be provided together or not at all.")
        return values

    @field_validator("data_domain", mode="before")
    @classmethod
    def serialize_data_domain(cls, val: Optional[str]) -> Optional[DataDomain]:
        return None if val is None else DataDomain(value=val)

    @field_validator("ura_number", mode="before")
    @classmethod
    def serialize_ura(cls, val: str) -> UraNumber:
        return UraNumber(val)
