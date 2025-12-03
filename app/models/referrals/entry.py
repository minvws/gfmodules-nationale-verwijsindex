from pydantic import BaseModel, field_serializer, field_validator

from app.db.models.referral import ReferralEntity
from app.models.data_domain import DataDomain
from app.models.pseudonym import Pseudonym
from app.models.ura import UraNumber


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

    @field_validator("pseudonym", mode="before")
    @classmethod
    def deserialize_pseudonym(cls, value: object) -> Pseudonym:
        if not isinstance(value, Pseudonym):
            return Pseudonym(value)
        return value

    @field_validator("data_domain", mode="before")
    @classmethod
    def deserialize_data_domain(cls, value: object) -> DataDomain:
        if not isinstance(value, DataDomain):
            return DataDomain(value)
        return value

    @field_validator("ura_number", mode="before")
    @classmethod
    def deserialize_ura_number(cls, value: object) -> UraNumber:
        if not isinstance(value, UraNumber):
            return UraNumber(value)
        return value

    @classmethod
    def from_entity(cls, entity: ReferralEntity) -> "ReferralEntry":
        return cls(
            ura_number=UraNumber(entity.ura_number),
            pseudonym=Pseudonym(value=entity.pseudonym),
            data_domain=DataDomain(value=entity.data_domain),
            encrypted_lmr_id=entity.encrypted_lmr_id,
            lmr_endpoint=entity.lmr_endpoint,
        )
