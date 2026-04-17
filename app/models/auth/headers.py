from enum import Enum
from typing import Any, Dict, List, Self

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.ura import UraNumber


class AuthorizationRoles(Enum):
    CONSULTING = "consulting"
    SOURCE = "source"


class AuthHeaders(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    x_oin_number: str = Field(alias="x-oin-number")
    x_source_id: str = Field(alias="x-source-id")
    x_ura_number: str = Field(alias="x-ura-number")
    x_audience: str = Field(alias="x-audience")
    x_authorized_role: AuthorizationRoles = Field(alias="x-authorized-role")
    x_scope: List[str] = Field(alias="x-scope")

    @field_validator("x_ura_number", mode="before")
    @classmethod
    def validate_ura_number(cls, data: str) -> str:
        try:
            ura_number = UraNumber(data)
        except ValueError as e:
            raise ValueError(f"Invalid URA Number in header: {data}") from e

        return ura_number.value

    @field_serializer("x_authorized_role")
    def serialize_role(self, value: AuthorizationRoles) -> str:
        return value.value

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

        for name, field in cls.model_fields.items():
            header_name = field.alias or name
            value = headers.get(header_name)

            if value is None:
                raise ValueError(f"{header_name} is required for {cls.__name__}")

            data[name] = value

        return cls(**data)
