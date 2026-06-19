from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request

from app.dependencies import get_crypto_service_api_client, get_referral_service
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.registrations import LocalizeRequest, Registration
from app.services.crypto_service_api_client import CryptoServiceApiClient
from app.services.exceptions import UnauthorizedScopeError
from app.services.referral_service import ReferralService

router = APIRouter(tags=["Localization"], prefix="/localize")


@router.post("")
def localize(
    request: Request,
    data: Annotated[LocalizeRequest, Body()],
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    crypto_client: Annotated[CryptoServiceApiClient, Depends(get_crypto_service_api_client)],
) -> Any:
    ctx: AuthContext = request.state.auth
    if AuthorizationScope.LOCALIZE not in ctx.scope:
        raise UnauthorizedScopeError(ctx.scope, AuthorizationScope.LOCALIZE)

    pseudonym = crypto_client.exchange(data.pseudonym, data.oprf_key)

    results = referral_service.get_many(pseudonym=pseudonym)

    return [Registration.from_entity(r) for r in results]
