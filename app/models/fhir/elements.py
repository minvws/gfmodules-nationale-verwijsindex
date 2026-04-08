import logging
from typing import Any, List, Self

from pydantic import model_validator

from app.models.fhir.resources.domain_resource import FhirBaseModel

logger = logging.getLogger(__name__)


class Coding(FhirBaseModel):
    system: str
    code: str
    display: str | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, value: Any) -> Any:
        if "code" not in value:
            raise ValueError("Coding.code is required")
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

    @classmethod
    def from_query(cls, query: str, system: str) -> Self:
        data = query.split("|")
        if len(data) == 1:
            logger.debug(f"Parsing coding from query: {query} with implicit system: {system}")
            return cls(system=system, code=query)
        if len(data) != 2:
            logger.debug(f"Invalid coding query format: {query}")
            raise ValueError("Invalid query format, unable to determine System for Coding")
        if data[0] and data[0] != system:
            logger.debug(f"Unrecognized system in coding query: {query}")
            raise ValueError(f"Unrecognized system, value must be {system}")
        return cls(system=data[0], code=data[1])


class CodeableConcept(FhirBaseModel):
    coding: List[Coding]
    text: str | None = None


class Identifier(FhirBaseModel):
    system: str
    value: str

    @classmethod
    def from_query(cls, query: str, system: str) -> Self:
        data = query.split("|")
        if len(data) == 1:
            logger.debug(f"Parsing identifier from query: {query} with implicit system: {system}")
            return cls(system=system, value=query)
        if len(data) != 2:
            logger.debug(f"Invalid identifier query format: {query}")
            raise ValueError("Invalid query format, unable to determine System for Identifier")
        if data[0] and data[0] != system:
            logger.debug(f"Unrecognized system in identifier query: {query}")
            raise ValueError(f"Unrecognized system, value must be {system}")
        return cls(system=data[0], value=data[1])


class Reference(FhirBaseModel):
    identifier: Identifier
    type: str | None = None


class Extension(FhirBaseModel):
    url: str
