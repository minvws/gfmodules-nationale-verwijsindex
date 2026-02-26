from pydantic import (
    BaseModel,
    ConfigDict,
    field_serializer,
    field_validator,
)
from pydantic.alias_generators import to_camel

from app.models.ura import UraNumber


class DataReferenceRequestBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    organization: str

    @field_validator("organization", mode="before")
    @classmethod
    def deserialize_organization(cls, val: object) -> str:
        if isinstance(val, UraNumber):
            return str(UraNumber(val))

        valid_ura = UraNumber(val)

        return str(valid_ura)

    @field_serializer("organization")
    def serialize_organization(self, organization: UraNumber) -> str:
        return str(organization)


class DataReferenceRequestParams(DataReferenceRequestBase):
    pseudonym: str | None = None
    oprf_key: str | None = None
    care_context: str | None = None
    source: str | None = None
