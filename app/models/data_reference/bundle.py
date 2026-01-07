from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models.data_reference.resource import (
    NVIDataReferenceBaseId,
    NVIDataReferenceOutput,
)


class BundleEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    resource: NVIDataReferenceBaseId | None = None


class Bundle(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str | None = None
    resource_type: Literal["Bundle"] = "Bundle"
    type: Literal["searchset"] = "searchset"
    timestamp: datetime = datetime.now()
    total: int | None = None
    entry: List[BundleEntry]

    @classmethod
    def from_reference_outputs(cls, nvi_references: List[NVIDataReferenceOutput]) -> "Bundle":
        entries = [BundleEntry(resource=nvi_ref) for nvi_ref in nvi_references]
        obj = cls(entry=entries)
        obj.total = len(obj.entry)

        return obj
