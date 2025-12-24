from typing import Any, Final, List

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic.alias_generators import to_camel

from app.db.models.referral import ReferralEntity
from app.models.data_domain import DataDomain
from app.models.ura import UraNumber

SOURCE_SYSTEM: Final[str] = "urn:oid:2.16.528.1.1007.3.3"  # NO SONAR (S5322)
SOURCE_TYPE_SYSTEM: Final[str] = "http://vws.nl/fhir/CodeSystem/nvi-organization-types"  # NO SONAR (S5322)
SUBJECT_SYSTEM: Final[str] = "http://vws.nl/fhir/NamingSystem/nvi-pseudonym"  # NO SONAR (S5322)
CARE_CONTEXT_SYSTEM: Final[str] = "http://nictiz.nl/fhir/hcim-2024"  # NO SONAR (S5322)


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

    source: Identifier
    source_type: CodeableConcept
    care_context: CodeableConcept

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, value: Any) -> Identifier:
        if value is None:
            raise ValidationError("NVIDataReference.source is required")

        if not isinstance(value, Identifier):
            raise ValidationError("NVIDataReferece.source must be of type `Identifier`")

        if value.system != SOURCE_SYSTEM:
            raise ValidationError(f"NVIDataReferece.source.system unrecoginzed, system must be: {SOURCE_SYSTEM}")

        return value

    @field_validator("source_type", mode="before")
    @classmethod
    def validate_source_type(cls, value: Any) -> CodeableConcept:
        if value is None:
            raise ValidationError("NVIDataReference.sourceType is required")

        if not isinstance(value, CodeableConcept):
            raise ValidationError("NVIDataReferece.sourceType must be of type `CodeableConcept`")

        if len(value.coding) != 1:
            raise ValidationError("NVIDataReference.sourceType.coding must me of length `1`")

        coding = value.coding[0]

        if not isinstance(coding, Coding):
            raise ValidationError("NVIReference.sourceType.coding must be of type `Coding`")

        if coding.system != SOURCE_TYPE_SYSTEM:
            raise ValidationError(
                f"NVIDataReference.systemType.coding.system urecognized, system must be: {SOURCE_TYPE_SYSTEM}"
            )

        return value

    @field_validator("care_context", mode="before")
    @classmethod
    def validate_care_context(cls, value: Any) -> CodeableConcept:
        if value is None:
            raise ValidationError("NVIDataReference.careContext is required")

        if not isinstance(value, CodeableConcept):
            raise ValidationError("NVIDataReference.careContext must be of type `CodeableConcept`")

        if len(value.coding) != 1:
            raise ValidationError("NVIDataReference.careContext.coding must me of length `1`")

        coding = value.coding[0]
        if not isinstance(coding, Coding):
            raise ValidationError("NVIReference.careContext.coding must be of type `Coding`")

        if coding.system != CARE_CONTEXT_SYSTEM:
            raise ValidationError(
                f"NVIReferenceData.careContext.coding.system unrecoginzed, system must be: {CARE_CONTEXT_SYSTEM}"
            )

        return value

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
            raise ValidationError("NVIDataReference.subject is required")

        if not isinstance(value, Identifier):
            raise ValidationError("NVIDataReference.subject must be of type `Identifier`")

        if value.system != SUBJECT_SYSTEM:
            raise ValidationError(
                f"NVIDataReference.subject.system unrecoginzed, ssssssssystem must be {SUBJECT_SYSTEM}"
            )

        return value


class NVIDataReferenceOutput(NVIDataReferenceBase):
    pass

    @classmethod
    def from_referral(cls, entity: ReferralEntity) -> "NVIDataReferenceOutput":
        return cls(
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
