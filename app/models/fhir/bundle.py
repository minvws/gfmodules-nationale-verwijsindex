from datetime import datetime
from typing import List, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models.fhir.resources.data_reference.resource import (
    NVIDataReferenceOutput,
)


class BundleEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    resource: NVIDataReferenceOutput | None = None


class Bundle(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str | None = None
    resource_type: Literal["Bundle"] = "Bundle"
    type: Literal["searchset"] = "searchset"
    timestamp: datetime = datetime.now()
    total: int | None = None
    entry: List[BundleEntry]

    @classmethod
    def from_reference_outputs(
        cls, nvi_references: List[NVIDataReferenceOutput], bundle_id: UUID | None = None
    ) -> "Bundle":
        target_id = str(bundle_id) if bundle_id else str(uuid4())
        entries = [BundleEntry(resource=nvi_ref) for nvi_ref in nvi_references]
        obj = cls(entry=entries, id=target_id)
        obj.total = len(obj.entry)

        return obj
