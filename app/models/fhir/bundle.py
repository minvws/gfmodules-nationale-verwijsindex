from datetime import datetime
from typing import Generic, List, Literal, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models.fhir.resources.data_reference.resource import (
    NVIDataReferenceOutput,
)
from app.models.fhir.resources.domain_resource import DomainResource
from app.models.fhir.resources.organization.resource import Organization

T = TypeVar("T", bound=DomainResource)


class EntryRequest(BaseModel):
    method: Literal["POST", "DELETE"]
    url: str


class EntryResponse(BaseModel):
    pass


class BundleEntry(BaseModel, Generic[T]):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    request: EntryRequest | None = None
    resource: T


class Bundle(BaseModel, Generic[T]):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str | None = None
    resource_type: Literal["Bundle"] = "Bundle"
    type: Literal["searchset"] = "searchset"
    timestamp: datetime = datetime.now()
    total: int | None = None
    entry: List[BundleEntry[T]]

    @classmethod
    def from_reference_outputs(
        cls, nvi_references: List[NVIDataReferenceOutput], bundle_id: UUID | None = None
    ) -> "Bundle[NVIDataReferenceOutput]":
        target_id = str(bundle_id) if bundle_id else str(uuid4())
        entries = [BundleEntry(resource=nvi_ref) for nvi_ref in nvi_references]
        obj = Bundle(entry=entries, id=target_id)
        obj.total = len(obj.entry)

        return obj

    @classmethod
    def from_organizations(cls, orgs: List[Organization], bundle_id: UUID | None = None) -> "Bundle[Organization]":
        target_id = str(bundle_id) if bundle_id else str(uuid4())
        entries = [BundleEntry(resource=org) for org in orgs]
        obj = Bundle(entry=entries, id=target_id)
        obj.total = len(entries)

        return obj
