from typing import List, Literal, Self

from app.db.models.referral import ReferralEntity
from app.models.fhir.elements import Identifier
from app.models.fhir.resources.domain_resource import DomainResource


class Device(DomainResource):
    resource_type: Literal["Device"] = "Device"
    identifier: List[Identifier]

    @classmethod
    def from_referral(cls, referral: ReferralEntity) -> Self:
        return cls(id=referral.id, identifier=[Identifier(system="", value=referral.source)])
