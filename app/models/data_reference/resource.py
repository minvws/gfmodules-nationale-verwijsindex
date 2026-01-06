from typing import Any, Final, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic.alias_generators import to_camel

from app.db.models.referral import ReferralEntity
from app.models.data_domain import DataDomain
from app.models.ura import UraNumber

SOURCE_SYSTEM: Final[str] = "urn:oid:2.16.528.1.1007.3.3"  # NOSONAR
SOURCE_TYPE_SYSTEM: Final[str] = "http://vws.nl/fhir/CodeSystem/nvi-organization-types"  # NOSONAR
SUBJECT_SYSTEM: Final[str] = "http://vws.nl/fhir/NamingSystem/nvi-pseudonym"  # NOSONAR
CARE_CONTEXT_SYSTEM: Final[str] = "http://nictiz.nl/fhir/hcim-2024"  # NOSONAR


class Coding(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)

    system: str
    code: str


class CodeableConcept(BaseModel):
    coding: List[Coding]


class Identifier(BaseModel):
    system: str
    value: str


class NVIDataReferenceBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    source: Identifier
    source_type: CodeableConcept
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
                f"NVIDataReference.systemType.coding.system urecognized, system must be: {SOURCE_TYPE_SYSTEM}"
            )

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

        return care_context

    def get_ura_number(self) -> UraNumber:
        return UraNumber(self.source.value)

    def get_data_domain(self) -> DataDomain:
        return DataDomain(self.care_context.coding[0].code)

    def get_organization_type(self) -> str:
        return self.source_type.coding[0].code


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


class NVIDataReferenceOutput(NVIDataReferenceBase):
    @classmethod
    def from_referral(cls, entity: ReferralEntity) -> "NVIDataReferenceOutput":
        return cls(
            id=entity.id,
            source=Identifier(
                system=SOURCE_SYSTEM,
                value=entity.ura_number,
            ),
            source_type=CodeableConcept(
                coding=[
                    Coding(
                        system=SOURCE_TYPE_SYSTEM,
                        code=entity.organization_type or "",
                    )
                ]
            ),
            care_context=CodeableConcept(
                coding=[
                    Coding(
                        code=entity.data_domain,
                        system=CARE_CONTEXT_SYSTEM,
                    )
                ]
            ),
        )
