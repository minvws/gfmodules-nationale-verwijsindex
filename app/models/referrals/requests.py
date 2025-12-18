from typing import Any

from pydantic import BaseModel, field_serializer, field_validator, model_validator

from app.models.data_domain import DataDomain
from app.models.ura import UraNumber


class ReferralRequest(BaseModel):
    oprf_jwe: str
    blind_factor: str
    data_domain: DataDomain

    @field_validator("data_domain", mode="before")
    @classmethod
    def deserialize_data_domain(cls, val: str) -> DataDomain:
        return DataDomain(value=val)

    @field_serializer("data_domain")
    def serialize_data_domain(self, value: DataDomain) -> str:
        return str(value)


class CreateReferralRequest(ReferralRequest):
    ura_number: UraNumber
    requesting_uzi_number: str
    encrypted_lmr_id: str
    lmr_endpoint: str

    @field_validator("ura_number", mode="before")
    @classmethod
    def deserialize_ura(cls, val: object) -> UraNumber:
        if not isinstance(val, UraNumber):
            return UraNumber(val)
        return val

    @field_serializer("ura_number")
    def serialize_ura(self, ura_number: UraNumber) -> str:
        return str(ura_number)


class DeleteReferralRequest(CreateReferralRequest):
    pass


class ReferralQuery(BaseModel):
    oprf_jwe: str | None = None
    blind_factor: str | None = None
    data_domain: DataDomain | None = None
    ura_number: UraNumber

    @model_validator(mode="after")
    @classmethod
    def both_or_none(cls, values: Any) -> Any:
        oprf_jwe = values.oprf_jwe
        blind_factor = values.blind_factor

        if (oprf_jwe is None) != (blind_factor is None):
            raise ValueError("Both 'oprf_jwe' and 'blind_factor' must be provided together or not at all.")
        return values

    @field_validator("ura_number", mode="before")
    @classmethod
    def deserialize_ura(cls, val: object) -> UraNumber:
        if not isinstance(val, UraNumber):
            return UraNumber(val)
        return val

    @field_validator("data_domain", mode="before")
    def deserialize_data_domain(cls, val: object | None) -> DataDomain | None:
        if val is None:
            return None

        if not isinstance(val, DataDomain):
            return DataDomain(val)

        return val

    @field_serializer("ura_number")
    def serialize_ura_number(self, val: UraNumber) -> str:
        return str(val)

    @field_serializer("data_domain")
    def serialize_data_domain(self, val: DataDomain) -> str:
        return str(val)
