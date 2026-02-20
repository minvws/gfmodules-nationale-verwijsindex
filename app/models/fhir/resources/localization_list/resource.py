from typing import List, Literal

from app.db.models.referral import ReferralEntity
from app.models.fhir.elements import (
    CodeableConcept,
    Coding,
    Extension,
    Identifier,
    Reference,
)
from app.models.fhir.resources.domain_resource import DomainResource


class ReferenceExtension(Extension):
    value_reference: Reference


class LocalizationList(DomainResource):
    resource_type: Literal["List"] = "List"

    extension: List[ReferenceExtension]
    status: Literal["current", "retired", "entered-in-error"]
    mode: Literal["working", "snapshot", "changes"]
    subject: Reference
    source: Reference
    code: CodeableConcept
    empty_reason: CodeableConcept

    @classmethod
    def from_referral(cls, referral: ReferralEntity) -> "LocalizationList":
        reference_extension = ReferenceExtension(
            value_reference=Reference(
                identifier=Identifier(
                    system="http://fhir.nl/fhir/NamingSystem/ura",
                    value=referral.ura_number,
                )
            ),
            url="http://minvws.github.io/generiekefuncties-docs/StructureDefinition/nl-gf-localization-custodian",
        )
        subject = Reference(
            identifier=Identifier(
                system="http://fhir.nl/fhir/NamingSystem/pseudo-bsn",
                value=referral.pseudonym,
            )
        )
        source = Reference(
            identifier=Identifier(
                system="https://cp1-test.example.org/device-identifiers",
                value="EHR-SYS-2024-001",
            ),
            type="Device",
        )
        code = CodeableConcept(
            coding=[
                Coding(
                    display=referral.data_domain,
                    system="http://minvws.github.io/generiekefuncties-docs/CodeSystem/nl-gf-zorgcontext-cs",
                    code="TEST-CODE",
                )
            ]
        )
        empty_reason = CodeableConcept(
            coding=[
                Coding(
                    system="http://minvws.github.io/generiekefuncties-docs/CodeSystem/nl-gf-zorgcontext-cs",
                    code="withled",
                )
            ]
        )
        return cls(
            id=referral.id,
            extension=[reference_extension],
            status="current",
            mode="working",
            subject=subject,
            source=source,
            code=code,
            empty_reason=empty_reason,
        )
