import logging

from fastapi import Request

from app.exceptions.fhir_exception import FHIRException
from app.models.headers import AuthorizationRoles, Headers, RequestedAction

logger = logging.getLogger(__name__)


class UnauthorizedRoleException(Exception):
    pass


class HeaderService:
    def __init__(self, use_header_auth: bool = False):
        self.use_header_auth = use_header_auth

    def _get_headers(self, request: Request) -> Headers:
        try:
            return Headers.model_validate(dict(request.headers))
        except Exception as e:
            logger.error(f"Invalid headers: {e}")
            raise FHIRException(
                status_code=500,
                severity="error",
                code="invalid",
                msg="Authentication failed",
            ) from e

    def authorized_check(self, action: RequestedAction, request: Request) -> Headers | None:
        if not self.use_header_auth:
            return None  # If not using header auth, skip header checks and allow all actions
        headers = self._get_headers(request)
        try:
            match action:
                case RequestedAction.LOCALIZING:
                    if headers.x_authorized_role != AuthorizationRoles.CONSULTING:
                        raise UnauthorizedRoleException("Unauthorized role for localizing action")
                case RequestedAction.MODIFYING:
                    if headers.x_authorized_role != AuthorizationRoles.SOURCE:
                        raise UnauthorizedRoleException("Unauthorized role for modifying action")
                case _:
                    logger.warning(f"Unknown requested action `{action}` with headers: {headers.model_dump()}")
                    raise NotImplementedError(f"Authorization check for action `{action}` is not implemented")
            logger.info(f"Authorized `{action}` with headers: {headers.model_dump()}")
            return headers
        except (UnauthorizedRoleException, NotImplementedError) as e:
            logger.error(f"Error during authorization check for `{action}`: {e}")
            raise FHIRException(
                status_code=400,
                severity="error",
                code="invalid",
                msg="Organization unauthorized for requested action",
            )
