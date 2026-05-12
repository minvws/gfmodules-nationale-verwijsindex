from typing import List

from app.models.auth.data import AuthorizationRole, AuthorizationScope, RequestedAction


class NotFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("Record not found")


class ConflictError(Exception):
    def __init__(self) -> None:
        super().__init__("Record already exists")


class UnauthorizedError(Exception):
    pass


class UnauthorizedActionError(UnauthorizedError):
    def __init__(self, action: RequestedAction, role: AuthorizationRole | None = None) -> None:
        error_msg = (
            f"role {role.value} is not authorized for {action.value}"
            if role
            else f"role missing from AuthorizationHeader, {action.value} requires role"
        )
        super().__init__(error_msg)


class UnauthorizedScopeError(UnauthorizedError):
    def __init__(self, scopes: List[AuthorizationScope], required_scope: AuthorizationScope) -> None:
        values = ", ".join([s.value for s in scopes])
        error_msg = f"{values} not authorized for requested action. required scope: {required_scope}"
        super().__init__(error_msg)


class UnauthorizedManagingRequestError(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__("Unauthorized managing request, missing source_id in AuthenticationHeaders")


class UnauthorizedUraError(UnauthorizedError):
    def __init__(self, msg: str | None = None) -> None:
        error_msg = msg if msg else "UraNumber not authorized for action"
        super().__init__(error_msg)


class InvalidModelError(ValueError):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)


class InvalidHeaderPropertyError(Exception):
    def __init__(self, prop: str, value: str) -> None:
        super().__init__(f"Invalid header property {prop}: unrecognized `{value}`")


class PseudonymDecodingError(Exception):
    def __init__(self, msg: str | None = None) -> None:
        error_msg = "Error occurred while decoding pseudonym" if msg is None else msg
        super().__init__(f"Pseudonym Decoding Error: {error_msg}")
