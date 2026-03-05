from pydantic import (
    BaseModel,
    ConfigDict,
    field_serializer,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

from app.models.ura import UraNumber


class DataReferenceRequestBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    source: str

    @field_validator("source", mode="before")
    @classmethod
    def deserialize_organization(cls, val: object) -> str:
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

    @model_validator(mode="after")
    def validate_pseudonym_and_oprf_key_pair(self) -> "DataReferenceRequestParams":
        if bool(self.pseudonym) != bool(self.oprf_key):
            raise ValueError("pseudonym and oprfKey must both be provided")

        return self
