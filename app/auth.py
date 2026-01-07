import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request

from app import dependencies
from app.db.models.oauth_token import OAuthTokenEntity
from app.models.ura import UraNumber
from app.services.oauth import OAuthError, OAuthService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthContext:
    token: OAuthTokenEntity | None
    ura_number: UraNumber


bearer = HTTPBearer(auto_error=False)


def get_auth_ctx(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    oauth_service: OAuthService = Depends(dependencies.get_oauth_service),
) -> AuthContext:
    if not oauth_service.enabled():
        ctx = AuthContext(
            token=None,
            ura_number=UraNumber(oauth_service.get_override_ura()),
        )
        request.state.auth = ctx
        return ctx

    if creds is None or creds.scheme.lower() != "bearer":
        logger.error("Missing or invalid bearer token")
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        oauth_entity = oauth_service.verify(request)
    except OAuthError as e:
        logger.error(f"OAuth verification failed: {e.description}")
        raise HTTPException(status_code=e.status_code, detail=e.description) from e

    ctx = AuthContext(
        token=oauth_entity,
        ura_number=UraNumber(oauth_entity.ura_number),
    )
    request.state.auth = ctx
    return ctx
