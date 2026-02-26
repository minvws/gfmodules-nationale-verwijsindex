from typing import List, Literal

from app.db.models.referral import ReferralEntity
from app.models.fhir.elements import CodeableConcept, Coding, Identifier
from app.models.fhir.resources.data import SOURCE_SYSTEM, SOURCE_TYPE_SYSTEM
from app.models.fhir.resources.domain_resource import DomainResource


class Organization(DomainResource):
    resource_type: Literal["Organization"] = "Organization"
    identifier: List[Identifier]
    type: List[CodeableConcept] | None = None

    @classmethod
    def from_referral(cls, referral: ReferralEntity) -> "Organization":
        identifier = Identifier(system=SOURCE_SYSTEM, value=referral.ura_number)

        results = cls(id=referral.ura_number, identifier=[identifier])
        if referral.organization_type:
            org_type = CodeableConcept(
                coding=[
                    Coding(
                        system=SOURCE_TYPE_SYSTEM,
                        code=referral.organization_type,
                        display=referral.organization_type.capitalize(),
                    )
                ]
            )
            results.type = [org_type]

        return results
