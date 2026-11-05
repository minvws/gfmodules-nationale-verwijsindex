from typing import Literal, Self

from app.models.fhir.resources.domain_resource import DomainResource, FhirBaseModel

IssueType = Literal[
    "invalid",
    "structure",
    "required",
    "value",
    "invariant",
    "security",
    "login",
    "unknown",
    "expired",
    "forbidden",
    "suppressed",
    "processing",
    "not-supported",
    "duplicate",
    "multiple-matches",
    "not-found",
    "deleted",
    "too-long",
    "code-invalid",
    "extension",
    "too-costly",
    "business-rule",
    "conflict",
    "transient",
    "lock-error",
    "no-store",
    "exception",
    "timeout",
    "incomplete",
    "throttled",
    "informational",
]


class OperationOutcomeDetail(FhirBaseModel):
    text: str


class OperationOutcomeIssue(FhirBaseModel):
    severity: str
    code: str
    details: OperationOutcomeDetail | None = None
    expression: list[str] | None = None


class OperationOutcome(DomainResource):
    resource_type: str = "OperationOutcome"
    issue: list[OperationOutcomeIssue]

    @classmethod
    def make_error_outcome(cls, code: IssueType, msg: str) -> Self:
        return cls(
            issue=[
                OperationOutcomeIssue(
                    severity="error",
                    code=code,
                    details=(OperationOutcomeDetail(text=msg)),
                )
            ]
        )

    @classmethod
    def make_good_outcome(cls, msg: str) -> Self:
        return cls(
            issue=[
                OperationOutcomeIssue(
                    severity="information",
                    code="informational",
                    details=(OperationOutcomeDetail(text=msg)),
                )
            ]
        )
