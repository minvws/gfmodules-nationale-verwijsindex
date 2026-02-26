from typing import List, Literal

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from app.db.models.referral import ReferralEntity
from app.models.fhir.elements import CodeableConcept, Coding, Identifier
from app.models.fhir.resources.data import ORG_TYPE_SYSTEM, SOURCE_SYSTEM
from app.models.fhir.resources.domain_resource import DomainResource


class Organization(DomainResource):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    resource_type: Literal["Organization"] = "Organization"
    identifier: List[Identifier]
    type: List[CodeableConcept] | None = None

    @classmethod
    def from_referral(cls, referral: ReferralEntity) -> "Organization":
        identifier = Identifier(system=SOURCE_SYSTEM, value=referral.ura_number)
        org_type = CodeableConcept(
            coding=[
                Coding(
                    system=ORG_TYPE_SYSTEM,
                    code=referral.organization_type,
                    display=referral.organization_type.capitalize(),
                )
            ]
        )
        return cls(id=referral.ura_number, identifier=[identifier], type=[org_type])
