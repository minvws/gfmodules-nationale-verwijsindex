import logging
from enum import Enum
from typing import Any, Dict, List, Self

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.ura import UraNumber

logger = logging.getLogger(__name__)


class AuthorizationRoles(Enum):
    CONSULTING = "consulting"
    SOURCE = "source"


class AuthHeaders(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    oin: str | None = Field(alias="x-gf-oin", default=None)
    source_id: str | None = Field(alias="x-gf-source-id", default=None)
    ura: str = Field(alias="x-gf-ura")
    audience: str = Field(alias="x-gf-audience")
    authorized_role: str = Field(alias="x-gf-authorized-role")
    scope: List[str] = Field(alias="x-gf-scope")
    cert_type: str = Field(alias="x-gf-cert-type")

    @field_validator("ura", mode="before")
    @classmethod
    def validate_ura_number(cls, data: str) -> str:
        try:
            ura_number = UraNumber(data)
        except ValueError as e:
            raise ValueError(f"Invalid URA Number in header: {data}") from e

        return ura_number.value

    @field_validator("authorized_role", mode="before")
    @classmethod
    def validate_authorized_role(cls, data: Any) -> str:
        try:
            results = AuthorizationRoles(data)
            return results.value
        except Exception as e:
            raise ValueError(f"Invalid AuthorizationRoles : {e}")

    @classmethod
    def from_request(cls, req: Request) -> Self:
        headers = req.headers
        data: Dict[str, Any] = {}
        for name, field in cls.model_fields.items():
            header_name = field.alias or name
            value = headers.get(header_name)

            if field.is_required() is False and value is None:
                raise ValueError(f"{header_name} is required for {cls.__name__}")

            if header_name == "x-gf-scope" and value is not None:
                split_value = value.split(",")
                data[name] = split_value
                continue

            data[name] = value

        return cls(**data)
