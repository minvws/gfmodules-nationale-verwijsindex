from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class OperationOutcomeDetail(BaseModel):
    text: str


class OperationOutcomeIssue(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    severity: str
    code: str
    details: OperationOutcomeDetail | None = None
    diagnostics: str | None = None
    expression: list[str] | None = None


class OperationOutcome(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    resource_type: str = "OperationOutcome"
    issue: list[OperationOutcomeIssue]


class FHIRException(HTTPException):
    def __init__(
        self,
        status_code: int,
        severity: str,
        code: str,
        msg: str,
        diagnostics: str | None = None,
        expression: list[str] | None = None,
    ):
        outcome = OperationOutcome(
            issue=[
                OperationOutcomeIssue(
                    severity=severity,
                    code=code,
                    details=OperationOutcomeDetail(text=msg),
                    diagnostics=diagnostics,
                    expression=expression,
                )
            ]
        )
        super().__init__(
            status_code=status_code,
            detail=outcome.model_dump(by_alias=True, exclude_none=True),
            headers={"Content-Type": "application/fhir+json"},
        )
