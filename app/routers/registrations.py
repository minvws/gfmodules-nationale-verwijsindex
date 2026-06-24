import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, Request, Response

from app.dependencies import get_crypto_service_api_client, get_referral_service
from app.logging.events import Log
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.registrations import (
    CreateRegistrationRequest,
    Registration,
    RegistrationList,
    RegistrationQueryParams,
)
from app.services.crypto_service_api_client import CryptoServiceApiClient
from app.services.exceptions import (
    InvalidModelError,
    UnauthorizedScopeError,
)
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
    params: Annotated[RegistrationQueryParams, Query()],
) -> Any:
    ctx: AuthContext = request.state.auth
    if AuthorizationScope.READ not in ctx.scope:
        raise UnauthorizedScopeError(ctx.scope, AuthorizationScope.READ)

    pseudonym = crypto_client.exchange(params.pseudonym, params.oprf_key)

    results = referral_service.get_many(ura_number=ctx.claims.ura_number, pseudonym=pseudonym)

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
    crypto_client: Annotated[CryptoServiceApiClient, Depends(get_crypto_service_api_client)],
) -> Any:
    ctx: AuthContext = request.state.auth
    if AuthorizationScope.CREATE not in ctx.scope:
        raise UnauthorizedScopeError(ctx.scope, AuthorizationScope.CREATE)

    if ctx.claims.source_id is None:
        raise InvalidModelError("source_id is required to complete transaction")

    pseudonym = crypto_client.exchange(data.pseudonym, data.oprf_key)

    new_referral = referral_service.add_one(
        pseudonym=pseudonym,
        ura_number=ctx.claims.ura_number,
        source=ctx.claims.source_id,
    )
    return Registration.from_entity(new_referral)


@router.delete("")
def delete_registration(
    params: Annotated[RegistrationQueryParams, Query()],
    request: Request,
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    crypto_client: Annotated[CryptoServiceApiClient, Depends(get_crypto_service_api_client)],
) -> Any:
    ctx: AuthContext = request.state.auth
    if AuthorizationScope.DELETE not in ctx.scope:
        raise UnauthorizedScopeError(ctx.scope, AuthorizationScope.DELETE)

    if ctx.claims.source_id is None:
        raise InvalidModelError("source_id is required to complete transaction")

    pseudonym = crypto_client.exchange(params.pseudonym, params.oprf_key)

    deleted_count = referral_service.delete_many(
        ura_number=ctx.claims.ura_number,
        pseudonym=pseudonym,
        source=ctx.claims.source_id,
    )

    if deleted_count > 0:
        Log.event(
            logger,
            Log.ALL_PATIENT_REFERRALS_DELETED,
            "All patient referrals deleted",
            ura_number=str(ctx.claims.ura_number),
            pseudonym_hash=str(pseudonym),
            deleted_count=deleted_count,
        )

    return Response(status_code=204)
