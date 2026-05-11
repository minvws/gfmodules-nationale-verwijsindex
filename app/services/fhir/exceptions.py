from typing import List

from fastapi import HTTPException

from app.models.auth.data import AuthorizationRole, AuthorizationScope, RequestedAction
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
            msg="Record not found",
        )


class UnauthorizedAction(FHIRException):
    def __init__(self, action: RequestedAction, role: AuthorizationRole | None = None) -> None:
        error_msg = (
            f"role {role.value} is not authorized for {action.value}"
            if role
            else f"role missing from AuthorizationHeader, {action.value} requires role"
        )
        super().__init__(
            status_code=401,
            code="security",
            severity="error",
            msg=error_msg,
        )


class UnauthorizedScope(FHIRException):
    def __init__(self, scopes: List[AuthorizationScope], required_scope: AuthorizationScope) -> None:
        values = ", ".join([s.value for s in scopes])
        super().__init__(
            status_code=401,
            code="security",
            severity="error",
            msg=f"{values} not authorized for requested action. required scope: {required_scope.value}",
        )


class UnauthorizedManagingRequest(FHIRException):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="security",
            severity="error",
            msg="Unauthorized managing request, missing source_id in AuthenticationHeaders",
        )
