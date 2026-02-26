from fastapi import HTTPException

from app.models.fhir.resources.operation_outcome.resource import (
    OperationOutcome,
    OperationOutcomeDetail,
    OperationOutcomeIssue,
)


class FHIRException(HTTPException):
    def __init__(
        self,
        status_code: int,
        severity: str,
        code: str,
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
        super().__init__(
            status_code=status_code,
            detail=self.outcome.model_dump(by_alias=True, exclude_none=True),
            headers={"Content-Type": "application/fhir+json"},
        )


class NotFoundException(FHIRException):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="not-found",
            severity="error",
            msg="NVIDataReference not found",
        )
