from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing_extensions import Literal


class UrlResource(BaseModel):
    url: str


class CodeSystemConcept(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel)

    code: str
    display: str
    definition: str


class CodeSystem(UrlResource):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel)

    resource_type: Literal["CodeSystem"] = "CodeSystem"
    url: str
    version: str
    name: str
    title: str
    status: Literal["draft", "active", "retired", "unknown"]
    case_sensitive: bool
    content: Literal["not-present", "example", "fragment", "complete", "supplement"]
    concept: List[CodeSystemConcept]


class ValueSetComposeInclude(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel)

    system: str
    concept: List[CodeSystemConcept] | None = Field(default=None)


class ValueSetCompose(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel)

    include: List[ValueSetComposeInclude]


class ValueSetExpansion(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel)

    timestamp: datetime = datetime.now()
    total: int
    contains: List[CodeSystemConcept]


class ValueSet(UrlResource):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel)

    resource_type: Literal["ValueSet"] = "ValueSet"
    url: str
    version: str
    name: str
    title: str
    status: Literal["draft", "active", "retired", "unknown"]
    description: str
    compose: ValueSetCompose
    expansion: ValueSetExpansion | None = Field(default=None)
