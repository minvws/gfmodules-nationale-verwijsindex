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

    source: str

    @field_validator("source", mode="before")
    @classmethod
    def deserialize_source(cls, val: object) -> str:
        if isinstance(val, UraNumber):
            return str(UraNumber(val))

        valid_ura = UraNumber(val)

        return str(valid_ura)

    @field_serializer("source")
    def serialize_source(self, source: UraNumber) -> str:
        return str(source)


class DataReferenceRequestParams(DataReferenceRequestBase):
    pseudonym: str | None = None
    oprf_key: str | None = None
    care_context: str | None = None
