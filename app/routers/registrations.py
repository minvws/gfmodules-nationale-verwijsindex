import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, Response

from app.dependencies import (
    get_pseudonym_resolver,
    get_referral_service,
)
from app.logging.events import Log
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.registrations import (
    CreateRegistrationRequest,
    Registration,
    RegistrationList,
    RegistrationQueryParams,
)
from app.routers.dependencies import require_scope
from app.services.exceptions import (
    UnauthorizedManagingRequestError,
)
from app.services.pseudonym_resolver import PseudonymResolver
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Registrations"], prefix="/registrations")


@router.get(
    "",
)
def get_registration(
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    pseudonym_resolver: Annotated[PseudonymResolver, Depends(get_pseudonym_resolver)],
    params: Annotated[RegistrationQueryParams, Query()],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.READ))],
) -> Any:
    resolved = pseudonym_resolver.resolve_jwe(jwe=params.pseudonym, blind_factor=params.oprf_key)

    results = referral_service.get_many(ura_number=ctx.claims.ura_number, encrypted_pseudonym=resolved.encrypted)

    Log.event(
        logger,
        Log.REFERRALS_QUERIED,
        "Referrals queried",
        ura_number=str(ctx.claims.ura_number),
        result_count=len(results),
    )

    return RegistrationList.from_entities(results)


@router.post("", status_code=201)
def add_registration(
    data: Annotated[CreateRegistrationRequest, Body()],
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    pseudonym_resolver: Annotated[PseudonymResolver, Depends(get_pseudonym_resolver)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.CREATE))],
) -> Any:
    if ctx.claims.source_id is None:
        raise UnauthorizedManagingRequestError()

    resolved = pseudonym_resolver.resolve_jwe(jwe=data.pseudonym, blind_factor=data.oprf_key)

    new_referral = referral_service.add_one(
        encrypted_pseudonym=resolved.encrypted,
        ura_number=ctx.claims.ura_number,
        source=ctx.claims.source_id,
        organization_name=ctx.claims.organization_name,
        key_id=resolved.key_id,
    )
    return Registration.from_entity(new_referral)


@router.delete("")
def delete_registration(
    params: Annotated[RegistrationQueryParams, Query()],
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    pseudonym_resolver: Annotated[PseudonymResolver, Depends(get_pseudonym_resolver)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.DELETE))],
) -> Any:
    if ctx.claims.source_id is None:
        raise UnauthorizedManagingRequestError()

    resolved = pseudonym_resolver.resolve_jwe(jwe=params.pseudonym, blind_factor=params.oprf_key)
    encrypted_pseudonym = resolved.encrypted

    deleted_count = referral_service.delete_many(
        ura_number=ctx.claims.ura_number,
        encrypted_pseudonym=encrypted_pseudonym,
        source=ctx.claims.source_id,
    )

    if deleted_count > 0:
        Log.event(
            logger,
            Log.ALL_PATIENT_REFERRALS_DELETED,
            "All patient referrals deleted",
            organization=ctx.claims.organization_name,
            ura_number=str(ctx.claims.ura_number),
            pseudonym_hash=str(encrypted_pseudonym),
            deleted_count=deleted_count,
        )

    return Response(status_code=204)
