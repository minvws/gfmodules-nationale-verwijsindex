from typing import List

from app.models.auth.data import AuthorizationScope


class NotFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("Record not found")


class ConflictError(Exception):
    def __init__(self) -> None:
        super().__init__("Record already exists")


class ForbiddedError(Exception):
    def __init__(self, reason: str | None = None) -> None:
        msg = reason if reason else "Operation not allowed"
        super().__init__(msg)


class KeyInfoNotRegisteredError(Exception):
    """
    This error would occur for new referrals that have not been rotated yet with the new key
    or for example mismatch between the CrytpoClient and the NVI itself.

    Should be temporary and can be deprecated once all entries are rotated (encrypted) with
    the new key.
    """

    def __init__(self) -> None:
        super().__init__("KeyInfo not registered for referral")


class InvalidKeyInfoError(Exception):
    def __init__(self, msg: str | None = None) -> None:
        msg = msg if msg else "Inconsistency found in KeyInfo"
        super().__init__(msg)


class UnauthorizedError(Exception):
    pass


class UnauthorizedScopeError(UnauthorizedError):
    def __init__(self, scopes: List[AuthorizationScope], required_scope: AuthorizationScope) -> None:
        values = ", ".join([s.value for s in scopes])
        error_msg = f"{values} not authorized for requested action. required scope: `{required_scope.value}`"
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


class PseudonymError(Exception):
    def __init__(self, msg: str | None = None) -> None:
        error_msg = "Error occurred while decoding pseudonym" if msg is None else msg
        super().__init__(error_msg)
