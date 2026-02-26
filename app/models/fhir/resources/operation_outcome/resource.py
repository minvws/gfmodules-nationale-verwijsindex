from typing import Self

from app.models.fhir.resources.domain_resource import DomainResource, FhirBaseModel


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
    def make_error_outcome(cls, code: str, msg: str) -> Self:
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
