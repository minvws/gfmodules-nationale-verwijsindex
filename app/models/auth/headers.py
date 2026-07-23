from typing import Annotated, Any, Dict, Self

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.auth.data import AuthorizationScope
from app.models.ura import UraNumber


class AuthHeaders(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    oin: Annotated[str, Field(alias="x-gf-act-sub")]  # org acting on behalf of main
    source_id: Annotated[str | None, Field(alias="x-gf-source-id", default=None)]
    ura: Annotated[str, Field(alias="x-gf-sub")]  # main org
    audience: Annotated[str, Field(alias="x-gf-audience")]
    scope: Annotated[str, Field(alias="x-gf-scope")]
    cert_type: Annotated[str, Field(alias="x-gf-cert-type")]
    organization_name: Annotated[str, Field(alias="x-gf-organization-name")]

    @field_validator("ura", mode="before")
    @classmethod
    def validate_ura_number(cls, data: str) -> str:
        try:
            ura_number = UraNumber(data)
        except ValueError as e:
            raise ValueError(f"Invalid URA Number in header: {data}") from e

        return ura_number.value

    @field_validator("scope", mode="before")
    @classmethod
    def validate_scope(cls, data: Any) -> str:
        if not isinstance(data, str):
            raise ValueError(f"Invalid scope type in AuthorizationRoles: {data}")

        entries = data.split()
        if not entries:
            raise ValueError("x-gf-scope must hold at least one scope")

        for entry in entries:
            try:
                _ = AuthorizationScope(entry)
            except ValueError as e:
                raise ValueError(f"Invalid scope {entry}: {e}")

        return data

    @classmethod
    def from_request(cls, req: Request) -> Self:
        headers = req.headers
        data: Dict[str, Any] = {}
        # A header is optional exactly when its field declares a default, so this cannot
        # drift out of step with the field definitions above.
        for name, field in cls.model_fields.items():
            header_name = field.alias or name
            value = headers.get(header_name)

            if field.is_required() and value is None:
                raise ValueError(f"{header_name} is required for {cls.__name__}")

            data[name] = value

        return cls(**data)
