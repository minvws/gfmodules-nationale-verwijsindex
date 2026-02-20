from typing import List, Literal

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from app.db.models.referral import ReferralEntity
from app.models.data_domain import DataDomain
from app.models.fhir.elements import (
    CodeableConcept,
    Coding,
    Extension,
    Identifier,
    Reference,
)
from app.models.fhir.resources.domain_resource import DomainResource
from app.models.ura import UraNumber


# TODO: check add validations accordingly
class ReferenceExtension(Extension):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    value_reference: Reference


# TODO: check system values and add validations accordingly
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

    def get_ura(self) -> UraNumber:
        return UraNumber(self.extension[0].value_reference.identifier.value)

    def get_pseudonym_jwt(self) -> str:
        return self.subject.identifier.value

    def get_data_domain(self) -> DataDomain:
        return DataDomain(self.code.coding[0].code)

    def get_device(self) -> str:
        return self.source.identifier.value
