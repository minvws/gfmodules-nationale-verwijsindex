from typing import List

from fastapi import HTTPException

from app.models.fhir.elements import Coding
from app.models.fhir.operation_outcome import OperationOutcome, OperationOutcomeDetail, OperationOutcomeIssue


class FHIRException(HTTPException):
    def __init__(
        self,
        status_code: int,
        severity: str,
        code: str,
        msg: str,
        expression: List[str] | None = None,
        coding: List[Coding] | None = None,
    ):
        outcome = OperationOutcome(
            issue=[
                OperationOutcomeIssue(
                    severity=severity,
                    code=code,
                    details=OperationOutcomeDetail(text=msg, coding=coding),
                    expression=expression,
                )
            ]
        )
        super().__init__(
            status_code=status_code,
            detail=outcome.model_dump(by_alias=True, exclude_none=True),
            headers={"Content-Type": "application/fhir+json"},
        )
