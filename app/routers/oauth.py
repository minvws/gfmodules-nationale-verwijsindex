import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from starlette.responses import JSONResponse

from app import dependencies
from app.models.ura import UraNumber
from app.services.oauth import OAuthError, OAuthInvalidClientError, OAuthInvalidRequestError, OAuthService

logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["OAuth endpoints"],
    prefix="/oauth",
)


def invalid_client(msg: str = "invalid_client") -> JSONResponse:
    """
    Returns a 401 Unauthorized response for invalid client errors.
    """
    return JSONResponse(
        status_code=401,
        content={"error": "invalid_client", "error_description": msg},
        headers={"WWW-Authenticate": 'Basic realm="oauth"'},
    )


def invalid_request(msg: str) -> JSONResponse:
    """
    Returns a 400 Bad Request response for invalid request errors.
    """
    return JSONResponse(status_code=400, content={"error": "invalid_request", "error_description": msg})


def oauth_error(code: str, desc: str, status: int = 400) -> JSONResponse:
    """
    Returns a JSON response for (generic) OAuth errors.
    """
    return JSONResponse(status_code=status, content={"error": code, "error_description": desc})


@router.get(
    "/test-endpoint",
    summary="Test OAuth endpoint",
    response_model=None,
)
def oauth_test_endpoint(
    request: Request,
    oauth_service: OAuthService = Depends(dependencies.get_oauth_service),
) -> JSONResponse:
    """
    A simple test endpoint to verify that the OAuth router is working. This will be removed in production.
    """
    try:
        token = oauth_service.verify(request)
    except OAuthError as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.code, "error_description": e.description})

    ret = {
        "message": "OAuth endpoint is working.",
        "token_id": str(token.id),
        "ura_number": token.ura_number,
        "scopes": token.scopes,
    }
    return JSONResponse(
        status_code=200,
        content=ret,
    )


@router.post(
    "/token",
    summary="Creates a new token",
    response_model=None,
)
def oauth_token(
    request: Request,
    grant_type: str = Form(...),
    scope: Optional[str] = Form(None),
    client_assertion_type: Optional[str] = Form(None),
    client_assertion: Optional[str] = Form(None),
    ura_number: UraNumber = Depends(dependencies.authenticated_ura),
    oauth_service: OAuthService = Depends(dependencies.get_oauth_service),
) -> JSONResponse:
    """
    OAuth2 token endpoint. Validates OAuth client and generates access tokens.
    """
    logger.debug("OAuth token request for URA number: %s", ura_number)

    try:
        oauth_service.validate(grant_type, scope, client_assertion_type, client_assertion, request, ura_number)
    except OAuthInvalidClientError as e:
        return invalid_client(str(e))
    except OAuthInvalidRequestError as e:
        return JSONResponse(status_code=400, content={"error": "invalid_request", "error_description": str(e)})
    except OAuthError as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.code, "error_description": e.description})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "generic_error", "error_description": e})

    # @TODO: Check scope
    granted_scope = (scope or "read").split(" ")

    logger.debug("Generating access token for URA number: %s with scope: %s", ura_number, granted_scope)
    access_token = oauth_service.generate_token(ura_number, granted_scope)

    return JSONResponse(
        status_code=200,
        content={
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": granted_scope,
        },
    )
