from datetime import datetime
from typing import Generic, List, Literal, Self, TypeVar
from uuid import UUID, uuid4

from pydantic import Field

from app.models.fhir.resources.data_reference.resource import (
    NVIDataReferenceOutput,
)
from app.models.fhir.resources.domain_resource import DomainResource, FhirBaseModel
from app.models.fhir.resources.operation_outcome.resource import OperationOutcome
from app.models.fhir.resources.organization.resource import Organization

T = TypeVar("T", bound=DomainResource)


class EntryRequest(FhirBaseModel):
    method: Literal["POST", "DELETE", "GET", "PUT"]
    url: str


class EntryResponse(FhirBaseModel):
    status: str
    outcome: OperationOutcome | None = None

    @classmethod
    def make_validation_response(
        cls,
        msg: str | None = None,
        code: Literal["required", "structure", "invalid"] = "required",
    ) -> Self:
        message = msg if msg else "Structural data is invalid or missing required properties"
        return cls(
            status="400",
            outcome=OperationOutcome.make_error_outcome(code=code, msg=message),
        )

    @classmethod
    def make_forbidden_respone(cls, msg: str | None = None) -> Self:
        message = msg if msg else "URA number not allowed to perform requested operation"
        return cls(
            status="403",
            outcome=OperationOutcome.make_error_outcome(
                code="forbidden",
                msg=message,
            ),
        )

    @classmethod
    def make_unauthorized_response(cls, msg: str | None = None) -> Self:
        message = msg if msg else "Unauthorized access to perform operation"

        return cls(
            status="401",
            outcome=OperationOutcome.make_error_outcome(code="security", msg=message),
        )

    @classmethod
    def make_good_response(cls, msg: str | None = None) -> Self:
        message = msg if msg else "Resource has been modified successfully"

        return cls(status="201", outcome=OperationOutcome.make_good_outcome(msg=message))


class BundleEntry(FhirBaseModel, Generic[T]):
    request: EntryRequest | None = None
    response: EntryResponse | None = None
    resource: T | None = None


class Bundle(FhirBaseModel, Generic[T]):
    id: str | None = None
    resource_type: Literal["Bundle"] = "Bundle"
    type: Literal["searchset", "transaction"] = "searchset"
    timestamp: datetime | None = Field(default=None)
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
