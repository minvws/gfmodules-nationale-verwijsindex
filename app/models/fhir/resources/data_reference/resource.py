from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator

from app.data import HCIM_2024_ZIBS, NVI_ORGANIZATION_TYPES
from app.db.models.referral import ReferralEntity
from app.models.data_domain import DataDomain
from app.models.fhir.elements import CodeableConcept, Coding, Identifier
from app.models.fhir.resources.data import (
    CARE_CONTEXT_SYSTEM,
    SOURCE_SYSTEM,
    SOURCE_TYPE_SYSTEM,
    SUBJECT_SYSTEM,
)
from app.models.fhir.resources.domain_resource import DomainResource, FhirBaseModel
from app.models.ura import UraNumber


class NVIDataReferenceBase(FhirBaseModel):
    resource_type: Literal["NVIDataReference"] = "NVIDataReference"
    source: Identifier
    source_type: CodeableConcept | None = Field(default=None)
    care_context: CodeableConcept

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, value: Any) -> Identifier:
        if value is None:
            raise ValueError("NVIDataReference.source is required")

        try:
            source = Identifier.model_validate(value)
        except ValidationError:
            raise ValueError("NVIDataReferece.source must be a valid `Identifier`")

        if source.system != SOURCE_SYSTEM:
            raise ValueError(f"NVIDataReferece.source.system unrecognized, system must be: {SOURCE_SYSTEM}")

        try:
            UraNumber(source.value)
        except ValueError as e:
            raise ValueError(f"Invalid UraNumber: {e}")

        return source

    @field_validator("source_type", mode="before")
    @classmethod
    def validate_source_type(cls, value: Any) -> CodeableConcept:
        if value is None:
            raise ValueError("NVIDataReference.sourceType is required")

        try:
            source_type = CodeableConcept.model_validate(value)
        except ValidationError:
            raise ValueError("NVIDataReferece.sourceType must be a valid `CodeableConcept`")

        if len(source_type.coding) != 1:
            raise ValueError("NVIDataReference.sourceType.coding must me of length `1`")

        coding = source_type.coding[0]

        if coding.system != SOURCE_TYPE_SYSTEM:
            raise ValueError(
                f"NVIDataReference.sourceType.coding.system urecognized, system must be: {SOURCE_TYPE_SYSTEM}"
            )
        if coding.code not in [types.code for types in NVI_ORGANIZATION_TYPES]:
            raise ValueError(f"Invalid SourceType code: '{coding.code}' is not in ValueSet nvi-organization-types")

        return source_type

    @field_validator("care_context", mode="before")
    @classmethod
    def validate_care_context(cls, value: Any) -> CodeableConcept:
        if value is None:
            raise ValueError("NVIDataReference.careContext is required")

        try:
            care_context = CodeableConcept.model_validate(value)
        except ValidationError:
            raise ValueError("NVIDataReference.careContext must be a valid `CodeableConcept`")

        if len(care_context.coding) != 1:
            raise ValueError("NVIDataReference.careContext.coding must me of length `1`")

        coding = care_context.coding[0]

        if coding.system != CARE_CONTEXT_SYSTEM:
            raise ValueError(
                f"NVIReferenceData.careContext.coding.system unrecognized, system must be: {CARE_CONTEXT_SYSTEM}"
            )

        if coding.code not in [zib.code for zib in HCIM_2024_ZIBS]:
            raise ValueError(f"Invalid ZIB code: '{coding.code}' is not in ValueSet hcim-2024-zibs")

        return care_context

    def get_ura_number(self) -> UraNumber:
        return UraNumber(self.source.value)

    def get_data_domain(self) -> DataDomain:
        return DataDomain(self.care_context.coding[0].code)

    def get_organization_type(self) -> str | None:
        return self.source_type.coding[0].code if self.source_type else None


class NVIDataRefrenceInput(NVIDataReferenceBase):
    subject: Identifier
    oprf_key: str

    @field_validator("subject", mode="before")
    @classmethod
    def validate_subject(cls, value: Any) -> Identifier:
        if value is None:
            raise ValueError("NVIDataReference.subject is required")

        try:
            subject = Identifier.model_validate(value)
        except ValidationError:
            raise ValueError("NVIDataReference.subject must be a valid `Identifier`")

        if subject.system != SUBJECT_SYSTEM:
            raise ValueError(f"NVIDataReference.subject.system unrecognized, system must be {SUBJECT_SYSTEM}")

        return subject


class NVIDataReferenceOutput(NVIDataReferenceBase, DomainResource):
    @classmethod
    def from_referral(cls, entity: ReferralEntity) -> "NVIDataReferenceOutput":
        results = cls(
            id=entity.id,
            source=Identifier(
                system=SOURCE_SYSTEM,
                value=entity.ura_number,
            ),
            care_context=CodeableConcept(
                coding=[
                    Coding(
                        code=entity.data_domain,
                        system=CARE_CONTEXT_SYSTEM,
                        display=next(
                            (zib.display for zib in HCIM_2024_ZIBS if zib.code == entity.data_domain),
                            None,
                        ),
                    )
                ]
            ),
        )
        if entity.organization_type:
            results.source_type = CodeableConcept(
                coding=[
                    Coding(
                        system=SOURCE_TYPE_SYSTEM,
                        code=entity.organization_type,
                        display=next(
                            (
                                types.display
                                for types in NVI_ORGANIZATION_TYPES
                                if types.code == entity.organization_type
                            ),
                            None,
                        ),
                    )
                ]
            )

        return results
