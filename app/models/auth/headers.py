from enum import Enum
from typing import Any, Dict, Self

from fastapi import Request
from pydantic import BaseModel, Field, field_validator

from app.models.ura import UraNumber


class RequestedAction(Enum):
    LOCALIZING = "localizing"
    MODIFYING = "modifying"


class AuthorizationRoles(Enum):
    CONSULTING = "consulting"
    SOURCE = "source"


class AuthHeaders(BaseModel):
    x_oin_number: str = Field(alias="x-oin-number")
    x_source_id: str = Field(alias="x-source-id")
    x_ura_number: str = Field(alias="x-ura-number")
    x_audience: str = Field(alias="x-audience")
    x_authorized_role: AuthorizationRoles = Field(alias="x-authorized-role")

    @field_validator("x_ura_number", mode="before")
    @classmethod
    def validate_ura_number(cls, data: str) -> str:
        try:
            ura_number = UraNumber(data)
        except ValueError as e:
            raise ValueError(f"Invalid URA number in header: {data}") from e

        return ura_number.value

    @field_validator("x_authorized_role", mode="before")
    @classmethod
    def validate_authorized_role(cls, data: Any) -> AuthorizationRoles:
        try:
            return AuthorizationRoles(data)
        except Exception as e:
            raise ValueError(f"Invalid AuthorizationRoles : {e}")

    @classmethod
    def from_request_or_none(cls, req: Request) -> Self | None:
        try:
            return cls.from_request(req)

        except ValueError:
            return None

    @classmethod
    def from_request(cls, req: Request) -> Self:
        headers = req.headers
        data: Dict[str, Any] = {}
        for k in cls.__dict__.keys():
            prop = headers.get(k)
            if prop is None:
                raise ValueError(f"{k} is required to {cls.__name__}")

            data[k] = prop

        return cls(**data)
