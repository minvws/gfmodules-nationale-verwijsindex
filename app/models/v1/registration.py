from datetime import datetime
from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field


class CreateRegistrationRequest(BaseModel):
    pseudonym: str
    oprf_key: str


class RegistrationQueryParams(BaseModel):
    pseudonym: Annotated[str | None, Query()] = None
    oprf_key: Annotated[str | None, Query()] = None

    def has_pseudonym(self) -> bool:
        return self.pseudonym is not None and self.oprf_key is not None


class Registration(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ura: str = Field(validation_alias="ura_number")
    source_id: str = Field(validation_alias="source")
    created_at: datetime


class RegistrationList(BaseModel):
    registrations: list[Registration]
    total: int
