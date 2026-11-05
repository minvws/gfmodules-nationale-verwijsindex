from app.models.fhir.resources.operation_outcome.resource import (
    IssueType,
    OperationOutcome,
    OperationOutcomeDetail,
    OperationOutcomeIssue,
)


class FHIRError:
    def __init__(
        self,
        severity: str,
        code: IssueType,
        msg: str,
        expression: list[str] | None = None,
    ):
        self.outcome = OperationOutcome(
            issue=[
                OperationOutcomeIssue(
                    severity=severity,
                    code=code,
                    details=OperationOutcomeDetail(text=msg),
                    expression=expression,
                )
            ]
        )
        self.headers = {"Content-type": "application/fhir+json"}
