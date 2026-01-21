import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request

from app import dependencies
from app.data import OPERATION_OUTCOME_AUTHENTICATION_CODING
from app.exceptions.fhir_exception import FHIRException
from app.models.ura import UraNumber
from app.services.client_oauth import OAuthError
from app.services.oauth import OAuthService

logger = logging.getLogger(__name__)


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


bearer = HTTPBearer(auto_error=False)


def get_auth_ctx(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    oauth_service: OAuthService = Depends(dependencies.get_oauth_service),
) -> AuthContext:
    if not oauth_service.enabled():
        ctx = AuthContext(
            claims={},
            scope=[],
            ura_number=oauth_service.override_ura_number(),
        )
        request.state.auth = ctx
        return ctx

    if creds is None or creds.scheme.lower() != "bearer":
        logger.error("Missing or invalid bearer token")
        raise FHIRException(
            status_code=401,
            severity="error",
            code="login",
            msg="Invalid access token.",
            coding=OPERATION_OUTCOME_AUTHENTICATION_CODING,
        )

    try:
        claims = oauth_service.verify(request)
    except OAuthError as e:
        logger.error(f"OAuth verification failed: {e.message}")
        raise FHIRException(
            status_code=401,
            severity="error",
            code="login",
            msg="Invalid access token.",
            coding=OPERATION_OUTCOME_AUTHENTICATION_CODING,
        ) from e

    ctx = AuthContext(
        claims=claims,
        scope=claims["scope"],
        ura_number=UraNumber(claims["sub"]),
    )
    request.state.auth = ctx
    return ctx
