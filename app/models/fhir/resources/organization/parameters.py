from typing import Any, List, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

from app.models.fhir.elements import Coding
from app.models.fhir.resources.data import CARE_CONTEXT_SYSTEM


class PseudonymParamter(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Literal["pseudonym"] = "pseudonym"
    value_string: str


class OprfKeyParameter(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Literal["oprfKey"] = "oprfKey"
    value_string: str


class CareContextValueCoding(Coding):
    system: str = CARE_CONTEXT_SYSTEM


class CareContextParameter(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Literal["careContext"] = "careContext"
    value_coding: CareContextValueCoding

    @field_validator("value_coding", mode="before")
    @classmethod
    def validate_value_coding(cls, value: Any) -> Any:
        try:
            data = Coding.model_validate(value)
        except ValidationError:
            raise ValueError("parameters.careContext must be a valid `coding`")

        if data.system != CARE_CONTEXT_SYSTEM:
            raise ValueError(f"valueCoding.system unrecognized, system must be {CARE_CONTEXT_SYSTEM}")

        return value


class SourceTypeParameter(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Literal["sourceType"] = "sourceType"
    value_code: str


class OrganizationLocalizationDto(BaseModel):
    oprf_jwe: str
    oprf_key: str
    data_domain: str
    org_types: List[str] = []


class Parameters(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    resource_type: Literal["Parameters"] = "Parameters"
    parameter: List[PseudonymParamter | OprfKeyParameter | CareContextParameter | SourceTypeParameter]

    @model_validator(mode="after")
    def validate_paramters(self) -> Self:
        names = [param.name for param in self.parameter]

        field_counts = {
            "pseudonym": 0,
            "oprfKey": 0,
            "careContext": 0,
        }

        while len(names) > 0:
            field_name = names.pop(0)
            field_exceed_maximum = any(c > 1 for c in field_counts.values())

            if field_exceed_maximum is True:
                broken_field = next(k for k, v in field_counts.items() if v > 1)
                raise ValueError(f"field {broken_field} is has a maximum of 1")

            if field_name in field_counts.keys():
                field_counts[field_name] += 1

        missing_field = next(iter(k for k, v in field_counts.items() if v == 0), None)
        if missing_field:
            raise ValueError(f"parameter {missing_field} is required")

        return self

    def get_org_lokalization_dto(self) -> OrganizationLocalizationDto:
        pseduonym: str | None = None
        oprf_key: str | None = None
        data_domain: str | None = None
        org_type = []

        for param in self.parameter:
            if isinstance(param, PseudonymParamter):
                pseduonym = param.value_string

            if isinstance(param, OprfKeyParameter):
                oprf_key = param.value_string

            if isinstance(param, CareContextParameter):
                data_domain = param.value_coding.code

            if isinstance(param, SourceTypeParameter):
                org_type.append(param.value_code)

        if pseduonym is None:
            raise ValueError("pseudonym.valueString is not accessible in Lokaliztation Parameters")

        if oprf_key is None:
            raise ValueError("OprfKey.valueString is not accessible in Lokalization Parameters")

        if data_domain is None:
            raise ValueError("careContext.valueString is not accessible in Lokaliztation Parameters")

        return OrganizationLocalizationDto(
            oprf_jwe=pseduonym,
            oprf_key=oprf_key,
            data_domain=data_domain,
            org_types=org_type,
        )
