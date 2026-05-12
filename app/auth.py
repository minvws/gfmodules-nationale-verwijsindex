import logging
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request

from app import dependencies
from app.models.auth.context import AuthContext, AuthenticationClaims
from app.models.auth.data import AuthorizationRole, AuthorizationScope
from app.models.auth.headers import AuthHeaders
from app.models.ura import UraNumber
from app.services.auth.header import AuthHeaderService

logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """
    Raised for general OAuth2 errors.
    """

    def __init__(self, code: str, description: str, status_code: int = 400):
        super().__init__(description)
        self.code = code
        self.description = description
        self.status_code = status_code


bearer = HTTPBearer(auto_error=False)


def get_auth_ctx(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    auth_headers_service: AuthHeaderService = Depends(dependencies.get_auth_header_service),
) -> AuthContext:
    try:
        auth_headers = AuthHeaders.from_request(request)
    except ValueError as e:
        logger.error(f"Failed to extract AuthHeaders: {e}")
        raise ValueError(f"Inavalid Authorization Headers in request: {e}")

    validated_auth_headers = auth_headers_service.validate(auth_headers)
    claims = AuthenticationClaims(
        ura_number=UraNumber(validated_auth_headers.ura),
        source_id=validated_auth_headers.source_id,
        oin=validated_auth_headers.oin,
    )
    ctx = AuthContext(
        claims=claims,
        scope=[AuthorizationScope(s) for s in validated_auth_headers.scope],
        role=AuthorizationRole(validated_auth_headers.authorized_role),
        audience=validated_auth_headers.audience,
    )
    request.state.auth = ctx
    return ctx
