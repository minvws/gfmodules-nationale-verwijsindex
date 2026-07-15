import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request

from app.dependencies import (
    get_crypto_service_api_client,
    get_key_info_service,
    get_referral_service,
)
from app.logging.events import Log
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.pseudonym import EncryptedPseudonym
from app.models.registrations import LocalizeRequest, Registration
from app.services.crypto_service_api_client import CryptoServiceApiClient
from app.services.exceptions import UnauthorizedScopeError
from app.services.key_info import KeyInfoService
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Localization"], prefix="/localize")


@router.post("")
def localize(
    request: Request,
    data: Annotated[LocalizeRequest, Body()],
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    crypto_client: Annotated[CryptoServiceApiClient, Depends(get_crypto_service_api_client)],
    key_info_service: Annotated[KeyInfoService, Depends(get_key_info_service)],
) -> Any:
    ctx: AuthContext = request.state.auth
    if AuthorizationScope.LOCALIZE not in ctx.scope:
        raise UnauthorizedScopeError(ctx.scope, AuthorizationScope.LOCALIZE)

    active_key = key_info_service.get_active_key()
    pseudonym_resp = crypto_client.exchange(
        jwe=data.pseudonym,
        blind_factor=data.oprf_key,
        label=active_key.label,
        mechanism=active_key.mechanism,
    )
    encrypted_pseudonym = EncryptedPseudonym.from_response(pseudonym_resp)

    results = referral_service.get_many(encrypted_pseudonym=encrypted_pseudonym)

    ura_number = str(ctx.claims.ura_number)
    if results:
        Log.event(
            logger,
            Log.LOCALIZATION_SUCCESS,
            "Localization succeeded",
            organization=ctx.claims.organization_name,
            ura_number=ura_number,
            pseudonym_hash=str(pseudonym_resp),
            result_count=len(results),
        )
    else:
        Log.event(
            logger,
            Log.LOCALIZATION_NO_MATCH,
            "Localization returned no match",
            ura_number=ura_number,
            result_count=0,
        )

    return [Registration.from_entity(r) for r in results]
