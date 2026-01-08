from typing import Any, List, Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic.alias_generators import to_camel

from app.models.fhir.elements import Coding
from app.models.fhir.resources.data import CARE_CONTEXT_SYSTEM


class PseudonymParamter(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Literal["pseudonym"]
    value_string: str


class OprfKeyParameter(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Literal["oprfKey"]
    value_string: str


class CareContextParameter(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Literal["careContext"]
    value_conding: Coding

    @field_validator("value_condition", mode="before")
    @classmethod
    def validate_value_coding(cls, value: Any) -> Any:
        if not isinstance(value, Coding):
            raise ValueError("valueConding must be a valid `Coding`")

        if value.system != CARE_CONTEXT_SYSTEM:
            raise ValueError(f"valueCoding.system unrecognized, system must be {CARE_CONTEXT_SYSTEM}")

        return value


class CareContextTypeParamter(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Literal["careContextType"]
    value_conding: Coding

    @field_validator("value_condition", mode="before")
    @classmethod
    def validate_value_coding(cls, value: Any) -> Any:
        if not isinstance(value, Coding):
            raise ValueError("valueConding must be a valid `Coding`")

        if value.system != CARE_CONTEXT_SYSTEM:
            raise ValueError(f"valueCoding.system unrecognized, system must be {CARE_CONTEXT_SYSTEM}")

        return value


class filterOrgTypeParamter(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Literal["filterOrgType"]
    # TODO: This should be validated against the a set of code once the implementation
    # of ZIB is in place
    value_code: str


class Parameters(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    resource_type: Literal["Parameters"] = "Parameters"
    parameter: List[
        PseudonymParamter
        | OprfKeyParameter
        | OprfKeyParameter
        | CareContextParameter
        | CareContextParameter
        | CareContextTypeParamter
        | filterOrgTypeParamter
    ]

    @model_validator(mode="after")
    def validate_paramters(self) -> Self:
        names = [param.name for param in self.parameter]

        field_counts = {
            "pseudonym": 0,
            "oprfKey": 0,
            "careContext": 0,
            "careContextType": 0,
        }

        while len(names) > 0:
            field_name = names.pop(0)
            field_exceed_maximum = any(c > 1 for c in field_counts.values())

            if field_exceed_maximum is True:
                broken_field = next(k for k, v in field_counts.items() if v > 1)
                raise ValueError(f"field {broken_field} is has a maximum of 1")

            field_counts[field_name] += 1

        required_fields = {
            "pseudonym": field_counts["pseudonym"],
            "oprefKey": field_counts["oprfKey"],
            "careContext": field_counts["careContext"],
        }
        missing_field = next(k for k, v in required_fields.items() if v == 0)
        if missing_field:
            raise ValueError(f"parameter {missing_field} is required")

        return self
