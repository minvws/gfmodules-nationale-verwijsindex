from typing import Any, List

from pydantic import BaseModel, model_validator


class Coding(BaseModel):
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


class CodeableConcept(BaseModel):
    coding: List[Coding]


class Identifier(BaseModel):
    system: str
    value: str
