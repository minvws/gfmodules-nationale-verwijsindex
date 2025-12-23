from typing import Final, List

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.db.models.referral import ReferralEntity
from app.models.pseudonym import Pseudonym

SOURCE_SYSTEM: Final[str] = "urn:oid:2.16.528.1.1007.3.3"
SOURCE_TYPE_SYSTEM: Final[str] = "http://vws.nl/fhir/CodeSystem/nvi-organization-types"
SUBJECT_SYSTEM: Final[str] = "http://vws.nl/fhir/NamingSystem/nvi-pseudonym"
CARE_CONTEXT_SYSTEM: Final[str] = "http://nictiz.nl/fhir/hcim-2024"


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


class NVIDataRefrenceInput(NVIDataReferenceBase):
    subject: Identifier
    oprf_key: str

    @classmethod
    def to_referral(cls, pseudonym: Pseudonym) -> ReferralEntity:
        ura_number = cls.source.value
        data_domain = cls.care_context.coding[0].code
        organization_type = cls.source_type.coding[0].code

        return ReferralEntity(
            ura_number=ura_number,
            pseudonym=pseudonym,
            data_domain=data_domain,
            organization_type=organization_type,
        )


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
