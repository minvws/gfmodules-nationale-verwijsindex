from pydantic import (
    BaseModel,
    ConfigDict,
    field_serializer,
    field_validator,
)
from pydantic.alias_generators import to_camel

from app.models.ura import UraNumber


class ListModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
