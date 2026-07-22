import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, Request, Response

from app.dependencies import (
    get_crypto_service_api_client,
    get_key_info_service,
    get_referral_service,
)
from app.logging.events import Log
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.pseudonym import EncryptedPseudonym
from app.models.registrations import (
    CreateRegistrationRequest,
    Registration,
    RegistrationList,
    RegistrationQueryParams,
)
from app.services.crypto_service_api_client import CryptoServiceApiClient
from app.services.exceptions import (
    UnauthorizedManagingRequestError,
    UnauthorizedScopeError,
)
from app.services.key_info import KeyInfoService
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Registrations"], prefix="/registrations")


@router.get(
    "",
)
def get_registration(
    request: Request,
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    crypto_client: Annotated[CryptoServiceApiClient, Depends(get_crypto_service_api_client)],
    key_info_service: Annotated[KeyInfoService, Depends(get_key_info_service)],
    params: Annotated[RegistrationQueryParams, Query()],
) -> Any:
    ctx: AuthContext = request.state.auth
    if AuthorizationScope.READ not in ctx.scope:
        raise UnauthorizedScopeError(ctx.scope, AuthorizationScope.READ)

    active_key = key_info_service.get_active_key()
    pseudonym_resopnse = crypto_client.exchange(
        jwe=params.pseudonym,
        blind_factor=params.oprf_key,
        label=active_key.label,
        mechanism=active_key.mechanism,
    )
    encrypted_pseudonym = EncryptedPseudonym.from_response(pseudonym_resopnse)

    results = referral_service.get_many(ura_number=ctx.claims.ura_number, encrypted_pseudonym=encrypted_pseudonym)

    Log.event(
        logger,
        Log.REFERRALS_QUERIED,
        "Referrals queried",
        ura_number=str(ctx.claims.ura_number),
        result_count=len(results),
    )

    return RegistrationList.from_entities(results)


@router.post("")
def add_registration(
    data: Annotated[CreateRegistrationRequest, Body()],
    request: Request,
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    key_info_service: Annotated[KeyInfoService, Depends(get_key_info_service)],
    crypto_client: Annotated[CryptoServiceApiClient, Depends(get_crypto_service_api_client)],
) -> Any:
    ctx: AuthContext = request.state.auth
    if AuthorizationScope.CREATE not in ctx.scope:
        raise UnauthorizedScopeError(ctx.scope, AuthorizationScope.CREATE)

    if ctx.claims.source_id is None:
        raise UnauthorizedManagingRequestError()

    active_key = key_info_service.get_active_key()
    pseudonym_resp = crypto_client.exchange(
        jwe=data.pseudonym,
        blind_factor=data.oprf_key,
        label=active_key.label,
        mechanism=active_key.mechanism,
    )
    encryped_pseudonym = EncryptedPseudonym.from_response(pseudonym_resp)

    new_referral = referral_service.add_one(
        encrypted_pseudonym=encryped_pseudonym,
        ura_number=ctx.claims.ura_number,
        source=ctx.claims.source_id,
        organization_name=ctx.claims.organization_name,
        key_id=active_key.id,
    )
    return Registration.from_entity(new_referral)


@router.delete("")
def delete_registration(
    params: Annotated[RegistrationQueryParams, Query()],
    request: Request,
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    crypto_client: Annotated[CryptoServiceApiClient, Depends(get_crypto_service_api_client)],
    key_info_service: Annotated[KeyInfoService, Depends(get_key_info_service)],
) -> Any:
    ctx: AuthContext = request.state.auth
    if AuthorizationScope.DELETE not in ctx.scope:
        raise UnauthorizedScopeError(ctx.scope, AuthorizationScope.DELETE)

    if ctx.claims.source_id is None:
        raise UnauthorizedManagingRequestError()

    active_key = key_info_service.get_active_key()
    pseudonym_resp = crypto_client.exchange(
        jwe=params.pseudonym,
        blind_factor=params.oprf_key,
        label=active_key.label,
        mechanism=active_key.mechanism,
    )
    encrypted_pseudoym = EncryptedPseudonym.from_response(pseudonym_resp)

    deleted_count = referral_service.delete_many(
        ura_number=ctx.claims.ura_number,
        encrypted_pseudonym=encrypted_pseudoym,
        source=ctx.claims.source_id,
    )

    if deleted_count > 0:
        Log.event(
            logger,
            Log.ALL_PATIENT_REFERRALS_DELETED,
            "All patient referrals deleted",
            organization=ctx.claims.organization_name,
            ura_number=str(ctx.claims.ura_number),
            pseudonym_hash=str(encrypted_pseudoym),
            deleted_count=deleted_count,
        )

    return Response(status_code=204)
