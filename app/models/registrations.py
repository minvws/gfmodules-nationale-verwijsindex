from datetime import datetime
from typing import Any, List, Self, Sequence

from pydantic import BaseModel, field_validator

from app.db.models.referral import ReferralEntity
from app.models.ura import UraNumber


class RegistrationQueryParams(BaseModel):
    pseudonym: str
    oprf_key: str


class CreateRegistrationRequest(RegistrationQueryParams):
    pass


class LocalizeRequest(RegistrationQueryParams):
    pass


class Registration(BaseModel):
    ura_number: str
    source_id: str
    created_at: datetime

    @field_validator("ura_number")
    @classmethod
    def validate_ura_number(cls, value: Any) -> str:
        try:
            result = UraNumber(value)
        except ValueError as e:
            raise ValueError(f"Invalid UraNumber: {e}")

        return result.value

    @classmethod
    def from_entity(cls, referral: ReferralEntity) -> Self:
        return cls(
            ura_number=referral.ura_number,
            source_id=referral.source,
            created_at=referral.created_at,
        )


class RegistrationList(BaseModel):
    registrations: List[Registration]
    total: int

    @classmethod
    def from_entities(cls, refrrals: Sequence[ReferralEntity]) -> Self:
        data = [Registration.from_entity(r) for r in refrrals]
        total = len(refrrals)
        return cls(registrations=data, total=total)
