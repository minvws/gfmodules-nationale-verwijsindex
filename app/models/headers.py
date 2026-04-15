from enum import Enum

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.models.ura import UraNumber


class RequestedAction(Enum):
    LOCALIZING = "localizing"
    MODIFYING = "modifying"


class AuthorizationRoles(Enum):
    CONSULTING = "consulting"
    SOURCE = "source"


class Headers(BaseModel):
    x_oin_number: str = Field(alias="x-oin-number")
    x_source_id: str = Field(alias="x-source-id")
    x_ura_number: UraNumber = Field(alias="x-ura-number")
    x_audience: str = Field(alias="x-audience")
    x_authorized_role: AuthorizationRoles = Field(alias="x-authorized-role")

    @field_validator("x_ura_number", mode="before")
    @classmethod
    def validate_ura_number(cls, v: str) -> UraNumber:
        try:
            return UraNumber(v)
        except ValueError as e:
            raise ValueError(f"Invalid URA number in header: {v}") from e

    @field_serializer("x_ura_number")
    def serialize_ura_number(self, v: UraNumber) -> str:
        return str(v)
