from datetime import datetime
from typing import Dict, Generic, List, Literal, Self, TypeVar
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.fhir.resources.data_reference.resource import (
    NVIDataReferenceOutput,
)
from app.models.fhir.resources.domain_resource import DomainResource, FhirBaseModel
from app.models.fhir.resources.operation_outcome.resource import OperationOutcome
from app.models.fhir.resources.organization.resource import Organization

T = TypeVar("T", bound=DomainResource)


class EntryRequestDto(BaseModel):
    resource: str | None = None
    id: UUID | None = None
    params: Dict[str, str] | None = None

    @classmethod
    def from_url(cls, url: str) -> Self:

        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")

        resource = path_parts[0] if path_parts else None
        target_id = UUID(path_parts[1]) if len(path_parts) > 1 else None

        query_params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        return cls(resource=resource, id=target_id, params=query_params)


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
            status="422",
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
    def make_good_response(cls, msg: str | None = None, status: str = "200") -> Self:
        message = msg if msg else "Resource has been modified successfully"

        return cls(status=status, outcome=OperationOutcome.make_good_outcome(msg=message))

    @classmethod
    def make_error_response(cls, msg: str | None = None, status: str = "500") -> Self:
        msg = msg if msg else "Error occurred"

        return cls(
            status=status,
            outcome=OperationOutcome.make_error_outcome(code="error", msg=msg),
        )


class BundleEntry(FhirBaseModel, Generic[T]):
    request: EntryRequest | None = None
    response: EntryResponse | None = None
    resource: T | None = None


class Bundle(DomainResource, Generic[T]):
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
