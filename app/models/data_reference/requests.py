from pydantic import (
    BaseModel,
    ConfigDict,
    field_serializer,
    field_validator,
)
from pydantic.alias_generators import to_camel

from app.models.ura import UraNumber


class DataReferenceRequestBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)

    source: str

    @field_validator("source", mode="before")
    @classmethod
    def deserialize_ura(cls, val: object) -> UraNumber:
        if not isinstance(val, UraNumber):
            return UraNumber(val)
        return val

    @field_serializer("source")
    def serialize_source(self, source: UraNumber) -> str:
        return str(source)


class DataReferenceRequestParams(DataReferenceRequestBase):
    pseudonym: str | None = None
    oprfkey: str | None = None
    care_context: str | None = None
