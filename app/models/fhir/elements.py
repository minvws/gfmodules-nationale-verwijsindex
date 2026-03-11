from typing import Any, List, Self

from pydantic import model_validator

from app.models.fhir.resources.domain_resource import FhirBaseModel


class Coding(FhirBaseModel):
    system: str
    code: str
    display: str | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, value: Any) -> Any:
        if "code" not in value:
            raise ValueError("Coding.system is required")
        code = value["code"]
        if not isinstance(code, str):
            raise ValueError("Coding.code must be of type `String`")

        if "system" not in value:
            raise ValueError("Coding.system is required")
        system = value["system"]
        if not isinstance(system, str):
            raise ValueError("Coding.system must be of type String")

        if "display" in value:
            display = value["display"]
            if not isinstance(display, str):
                raise ValueError("Coding.display must be for type String")

        return value


class CodeableConcept(FhirBaseModel):
    coding: List[Coding]
    text: str | None = None


class Identifier(FhirBaseModel):
    system: str
    value: str

    @classmethod
    def from_query(cls, query: str, system: str) -> Self:
        data = query.split("|")
        if len(data) != 2:
            raise ValueError("Missing delimiter '|', unable to determine System for Identifier")
        if data[0] != system:
            raise ValueError(f"Unrecognized system, value must be {system}")

        return cls(system=data[0], value=data[1])


class Reference(FhirBaseModel):
    identifier: Identifier
    type: str | None = None


class Extension(FhirBaseModel):
    url: str
