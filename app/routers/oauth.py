import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from starlette.responses import JSONResponse
from uzireader.uziserver import UziServer

from app import dependencies
from app.models.ura import UraNumber
from app.services.ca import CaService
from app.services.oauth import OAuthError, OAuthInvalidClientError, OAuthInvalidRequestError, OAuthService

logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["OAuth endpoints"],
    prefix="/oauth",
)


class JsonException(Exception):
    def __init__(self, response: JSONResponse):
        self.response = response


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
    oauth_service: OAuthService = Depends(dependencies.get_oauth_service),
    ca_service: CaService = Depends(dependencies.get_ca_service),
) -> JSONResponse:
    """
    OAuth2 token endpoint. Validates OAuth client and generates access tokens.
    """

    if ca_service.is_uzi_server_certificate(request):
        # UZI server certificates do not require OAuth validation
        cert_pem = ca_service.get_pem_from_request(request)
        uzi_data = UziServer(verify="SUCCESS", cert=cert_pem)
        ura_number = uzi_data["SubscriberNumber"]
    elif ca_service.is_ldn_server_certificate(request):
        # LDN server certificates require OAuth validation
        try:
            ura_number = get_ura_from_oauth(
                grant_type, scope, client_assertion_type, client_assertion, request, oauth_service
            )
        except JsonException as e:
            logger.error("OAuth validation failed for LDN certificate.")
            return e.response
    else:
        logger.error("Unknown client certificate authority.")
        return invalid_client("Unknown client certificate authority.")

    granted_scope = ["nvi:all"]
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


def get_ura_from_oauth(
    grant_type: str,
    scope: Optional[str],
    client_assertion_type: Optional[str],
    client_assertion: Optional[str],
    request: Request,
    oauth_service: OAuthService,
) -> UraNumber:
    """
    Validates the OAuth client and retrieves the URA number.
    """
    try:
        jwt_claims = oauth_service.validate(grant_type, scope, client_assertion_type, client_assertion, request)
        return UraNumber(jwt_claims["iss"])

    except OAuthInvalidClientError as e:
        logger.error(f"Invalid OAuth client: {e}")
        raise JsonException(invalid_client(str(e)))
    except OAuthInvalidRequestError as e:
        logger.error(f"Invalid OAuth request: {e}")
        raise JsonException(
            JSONResponse(status_code=400, content={"error": "invalid_request", "error_description": str(e)})
        )
    except OAuthError as e:
        logger.error(f"OAuth error: {e.description}")
        raise JsonException(
            JSONResponse(status_code=e.status_code, content={"error": e.code, "error_description": e.description})
        )
    except Exception as e:
        logger.error(f"OAuth error: {e}")
        raise JsonException(JSONResponse(status_code=500, content={"error": "generic_error", "error_description": e}))
