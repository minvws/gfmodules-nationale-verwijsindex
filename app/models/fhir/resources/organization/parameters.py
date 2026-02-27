from typing import Any, List, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
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


class SourceParameter(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Literal["source"] = "source"
    value_string: str


class CareContextParameter(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Literal["careContext"] = "careContext"
    value_coding: Coding

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any) -> Any:
        if isinstance(data, cls):
            return data

        if not isinstance(data, dict):
            raise ValueError("data must be a valid object")

        if "name" not in data:
            raise ValueError("careContext.name is missing")

        name = data["name"]
        if name != "careContext":
            raise ValueError("careContext.name must be `careContext`")

        value_coding_name = (
            "valueCoding" if "valueCoding" in data else "value_coding" if "value_coding" in data else None
        )
        if value_coding_name is None:
            raise ValueError("careContext.valueCoding is missing")

        value_coding = data[value_coding_name]
        try:
            coding = Coding.model_validate(value_coding)
        except ValueError as e:
            raise e

        if coding.system != CARE_CONTEXT_SYSTEM:
            raise ValueError(f"careContext.valueCoding.system must be {CARE_CONTEXT_SYSTEM}")
        return data


class OrganizationTypeParameter(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Literal["organizationType"] = "organizationType"
    value_code: str


class OrganizationLocalizationDto(BaseModel):
    oprf_jwe: str
    oprf_key: str
    data_domain: str
    source: str
    org_types: List[str] = []


class Parameters(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    resource_type: Literal["Parameters"] = "Parameters"
    parameter: List[
        PseudonymParamter | OprfKeyParameter | SourceParameter | CareContextParameter | OrganizationTypeParameter
    ]

    @field_validator("parameter", mode="before")
    @classmethod
    def validate_input(cls, value: Any) -> Any:
        if not isinstance(value, List):
            raise ValueError("Parameter.parameter must be a list")

        for param in value:
            if isinstance(
                param,
                (
                    PseudonymParamter,
                    OprfKeyParameter,
                    CareContextParameter,
                    SourceParameter,
                    OrganizationTypeParameter,
                ),
            ):
                continue

            if "name" not in param:
                continue

            name = param["name"]
            match name:
                case "oprfKey":
                    OprfKeyParameter.model_validate(param)

                case "pseudonym":
                    PseudonymParamter.model_validate(param)

                case "careContext":
                    CareContextParameter.model_validate(param)

                case "organizationType":
                    OrganizationTypeParameter.model_validate(param)

                case "source":
                    SourceParameter.model_validate(param)

                case _:
                    raise ValueError("Invalid property in Parameter.parameter")

        return value

    @model_validator(mode="after")
    def validate_paramters(self) -> Self:
        names = [param.name for param in self.parameter]

        field_counts = {"pseudonym": 0, "oprfKey": 0, "careContext": 0, "source": 0}

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
        source: str | None = None
        org_type = []

        for param in self.parameter:
            if isinstance(param, PseudonymParamter):
                pseduonym = param.value_string

            if isinstance(param, OprfKeyParameter):
                oprf_key = param.value_string

            if isinstance(param, CareContextParameter):
                data_domain = param.value_coding.code

            if isinstance(param, OrganizationTypeParameter):
                org_type.append(param.value_code)

            if isinstance(param, SourceParameter):
                source = param.value_string

        if pseduonym is None:
            raise ValueError("pseudonym.valueString is not accessible in Lokaliztation Parameters")

        if oprf_key is None:
            raise ValueError("OprfKey.valueString is not accessible in Lokalization Parameters")

        if data_domain is None:
            raise ValueError("careContext.valueString is not accessible in Lokaliztation Parameters")

        if source is None:
            raise ValueError("source.valueString is not accessible in Lokalization Parameters")

        return OrganizationLocalizationDto(
            oprf_jwe=pseduonym,
            oprf_key=oprf_key,
            data_domain=data_domain,
            source=source,
            org_types=org_type,
        )
