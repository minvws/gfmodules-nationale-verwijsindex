import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request

from app import dependencies
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


@dataclass(frozen=True)
class AuthContext:
    """
    Authentication context extracted from the bearer token. This can be used in the route handlers
    """

    # List of claims from the token
    claims: Dict[str, Any]
    # OAuth scope
    scope: List[str]
    # URA number of the authenticated user
    ura_number: UraNumber
    # OIN Number
    oin: str | None = None
    # authrozied role
    role: str | None = None


bearer = HTTPBearer(auto_error=False)


def get_auth_ctx(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    # oauth_service: OAuthService = Depends(dependencies.get_oauth_service),
    auth_headers_service: AuthHeaderService = Depends(dependencies.get_auth_header_service),
) -> AuthContext:
    try:
        auth_headers = AuthHeaders.from_request(request)
    except ValueError as e:
        logger.error(f"Failed to extract AuthHeaders: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid Authorizaiton Headers in request {e}")

    validated_auth_headers = auth_headers_service.validate(auth_headers)
    ctx = AuthContext(
        claims={},
        scope=validated_auth_headers.scope,
        ura_number=UraNumber(validated_auth_headers.ura),
        oin=validated_auth_headers.oin,
        role=validated_auth_headers.authorized_role,
    )
    request.state.auth = ctx
    return ctx

    # try:
    #     claims = oauth_service.verify(request)
    # except OAuthError as e:
    #     logger.error(f"OAuth verification failed: {e.description}")
    #     raise HTTPException(status_code=e.status_code, detail=e.description) from e
    #
    # ctx = AuthContext(
    #     claims=claims,
    #     scope=claims["scope"],
    #     ura_number=UraNumber(claims["sub"]),
    # )
    # request.state.auth = ctx
    # return ctx
