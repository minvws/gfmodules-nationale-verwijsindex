import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_crypto_service_api_client, get_referral_service
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope, RequestedAction
from app.models.v1.localize import LocalizeRequest, LocalizeResponse, Source
from app.services.auth.auth_context import AuthContextService
from app.services.crypto_service_api_client import CryptoServiceApiClient
from app.services.exceptions import UnauthorizedActionError, UnauthorizedScopeError
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["v1"], prefix="/v1/localize")


@router.post("", response_model=LocalizeResponse)
def localize(
    body: LocalizeRequest,
    request: Request,
    crypto_client: Annotated[CryptoServiceApiClient, Depends(get_crypto_service_api_client)],
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
) -> LocalizeResponse:
    ctx: AuthContext = request.state.auth
    if AuthorizationScope.LOCALIZE not in ctx.scope:
        raise UnauthorizedScopeError(scopes=ctx.scope, required_scope=AuthorizationScope.LOCALIZE)
    if not AuthContextService.validate_action(ctx, RequestedAction.LOCALIZING):
        raise UnauthorizedActionError(RequestedAction.LOCALIZING, ctx.role)

    pseudonym = crypto_client.exchange(body.pseudonym, body.oprf_key)
    referrals = referral_service.get_many(pseudonym=pseudonym)

    return LocalizeResponse(results=[Source(ura=r.ura_number, source_id=r.source) for r in referrals])
