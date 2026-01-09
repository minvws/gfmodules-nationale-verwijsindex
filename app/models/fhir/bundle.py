from datetime import datetime
from typing import List, Literal, Sequence
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models.fhir.resources.data_reference.resource import (
    NVIDataReferenceOutput,
)
from app.models.fhir.resources.organization.resource import Organization


class NVIDataReferenceEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    resource: NVIDataReferenceOutput


class OrganizationEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    resource: Organization


class Bundle(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str | None = None
    resource_type: Literal["Bundle"] = "Bundle"
    type: Literal["searchset"] = "searchset"
    timestamp: datetime = datetime.now()
    total: int | None = None
    entry: Sequence[NVIDataReferenceEntry | OrganizationEntry]

    @classmethod
    def from_reference_outputs(
        cls, nvi_references: List[NVIDataReferenceOutput], bundle_id: UUID | None = None
    ) -> "Bundle":
        target_id = str(bundle_id) if bundle_id else str(uuid4())
        entries = [NVIDataReferenceEntry(resource=nvi_ref) for nvi_ref in nvi_references]
        obj = cls(entry=entries, id=target_id)
        obj.total = len(obj.entry)

        return obj

    @classmethod
    def from_organizations(cls, orgs: List[Organization], bundle_id: UUID | None = None) -> "Bundle":
        target_id = str(bundle_id) if bundle_id else str(uuid4())
        entries = [OrganizationEntry(resource=org) for org in orgs]
        obj = cls(entry=entries, id=target_id)
        obj.total = len(entries)

        return obj
