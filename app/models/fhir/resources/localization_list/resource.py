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
from app.models.fhir.resources.data import (
    DATA_DOMAIN_SYSTEM,
    DEVICE_SYSTEM,
    EMPTY_REASON_SYSTEM,
    PSEUDONYM_SYSTEM,
    URA_SYSTEM,
    URA_SYSTEM_EXTENSION,
)
from app.models.fhir.resources.domain_resource import DomainResource
from app.models.ura import UraNumber


class ReferenceExtension(Extension):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    value_reference: Reference


class LocalizationList(DomainResource):
    resource_type: Literal["List"] = "List"

    extension: List[ReferenceExtension]
    status: Literal["current", "retired", "entered-in-error"]
    mode: Literal["working", "snapshot", "changes"]
    subject: Reference | None = None
    source: Reference
    code: CodeableConcept
    empty_reason: CodeableConcept

    @classmethod
    def from_referral(cls, referral: ReferralEntity) -> "LocalizationList":
        reference_extension = ReferenceExtension(
            value_reference=Reference(
                identifier=Identifier(
                    system=URA_SYSTEM,
                    value=referral.ura_number,
                )
            ),
            url=URA_SYSTEM_EXTENSION,
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
                    system=DATA_DOMAIN_SYSTEM,
                    code=referral.data_domain,
                )
            ]
        )
        empty_reason = CodeableConcept(
            coding=[
                Coding(
                    system=EMPTY_REASON_SYSTEM,
                    code="withhled",
                )
            ]
        )
        return cls(
            id=referral.id,
            extension=[reference_extension],
            status="current",
            mode="working",
            source=source,
            code=code,
            empty_reason=empty_reason,
        )

    def get_ura(self) -> UraNumber:
        target_ura = next(
            (
                v.value_reference.identifier.value
                for v in self.extension
                if v.value_reference.identifier.system == URA_SYSTEM
            ),
            None,
        )
        if target_ura is None:
            raise ValueError(f"Missing identifier with naming system {URA_SYSTEM} in List.extension")

        return UraNumber(target_ura)

    def get_encoded_pseudonym(self) -> str:
        if self.subject is None:
            raise ValueError("List.subject is required")

        if self.subject.identifier.system != PSEUDONYM_SYSTEM:
            raise ValueError(f"List.subject.identifier.system must be {PSEUDONYM_SYSTEM}")

        return self.subject.identifier.value

    def get_data_domain(self) -> DataDomain:
        target = next((v.code for v in self.code.coding if v.system == DATA_DOMAIN_SYSTEM), None)
        if target is None:
            raise ValueError(f"Missing code with code system {DATA_DOMAIN_SYSTEM} in List.code.coding")

        return DataDomain(target)

    def get_device(self) -> str:
        if self.source.identifier.system != DEVICE_SYSTEM:
            raise ValueError(f"List.source.identifier should include system {DEVICE_SYSTEM}")
        return self.source.identifier.value
