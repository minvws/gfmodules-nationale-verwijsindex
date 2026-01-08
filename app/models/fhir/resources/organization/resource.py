from typing import List, Literal

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from app.models.fhir.elements import CodeableConcept, Identifier
from app.models.fhir.resources.domain_resource import DomainResource


class Organization(DomainResource):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    resource_type: Literal["Organization"] = "Organization"
    identifier: List[Identifier]
    active: bool
    type: List[CodeableConcept]
    name: str | None = None
