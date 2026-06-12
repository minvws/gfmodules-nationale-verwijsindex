from typing import Annotated, Any, Dict, Self

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.auth.data import AuthorizationRole, AuthorizationScope
from app.models.ura import UraNumber


class AuthHeaders(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    oin: Annotated[str | None, Field(alias="x-gf-oin", default=None)]
    source_id: Annotated[str | None, Field(alias="x-gf-source-id", default=None)]
    ura: Annotated[str, Field(alias="x-gf-sub")]
    audience: Annotated[str, Field(alias="x-gf-audience")]
    authorized_role: Annotated[str, Field(alias="x-gf-authorized-role")]
    scope: Annotated[str, Field(alias="x-gf-scope")]
    cert_type: Annotated[str, Field(alias="x-gf-cert-type")]

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
            results = AuthorizationRole(data)
            return results.value
        except ValueError as e:
            raise ValueError(f"Invalid AuthorizationRoles : {data}") from e

    @field_validator("scope", mode="before")
    @classmethod
    def validate_scope(cls, data: Any) -> str:
        if not isinstance(data, str):
            raise ValueError(f"Invalid scope type in AuthorizationRoles: {data}")

        for entry in data.split():
            try:
                _valid = AuthorizationScope(entry)
            except ValueError as e:
                raise ValueError(f"Invalid scope {entry}: {e}")

        return data

    @classmethod
    def from_request(cls, req: Request) -> Self:
        headers = req.headers
        data: Dict[str, Any] = {}
        optional_fields = ["oin", "x-gf-oin", "source_id", "x-gf-source-id"]
        for name, field in cls.model_fields.items():
            header_name = field.alias or name
            value = headers.get(header_name)

            if header_name not in optional_fields and value is None:
                raise ValueError(f"{header_name} is required for {cls.__name__}")

            data[name] = value

        return cls(**data)
