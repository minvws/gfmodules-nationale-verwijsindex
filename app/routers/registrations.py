from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, Response

from app.dependencies import (
    get_pseudonym_resolver,
    get_referral_service,
)
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.registrations import (
    CreateRegistrationRequest,
    Registration,
    RegistrationList,
    RegistrationQueryParams,
)
from app.routers.dependencies import require_managing_source, require_scope
from app.services.pseudonym_resolver import PseudonymResolver
from app.services.referral_service import ReferralService

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
    resolved = pseudonym_resolver.resolve(params.oprf_pseudonym())

    results = referral_service.query(ctx.claims.ura_number, encrypted_pseudonym=resolved.encrypted)

    return RegistrationList.from_entities(results)


@router.post(
    "",
    status_code=201,
    responses={200: {"description": "The registration already existed and is returned unchanged"}},
)
def add_registration(
    data: Annotated[CreateRegistrationRequest, Body()],
    response: Response,
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    pseudonym_resolver: Annotated[PseudonymResolver, Depends(get_pseudonym_resolver)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.CREATE))],
    source: Annotated[str, Depends(require_managing_source)],
) -> Any:
    resolved = pseudonym_resolver.resolve(data.oprf_pseudonym())

    referral, created = referral_service.add_one(
        encrypted_pseudonym=resolved.encrypted,
        ura_number=ctx.claims.ura_number,
        source=source,
        key_id=resolved.key_id,
    )
    if not created:
        response.status_code = 200
    return Registration.from_entity(referral)


@router.delete("")
def delete_registration(
    params: Annotated[RegistrationQueryParams, Query()],
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    pseudonym_resolver: Annotated[PseudonymResolver, Depends(get_pseudonym_resolver)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.DELETE))],
    source: Annotated[str, Depends(require_managing_source)],
) -> Any:
    resolved = pseudonym_resolver.resolve(params.oprf_pseudonym())

    referral_service.delete_many(
        ura_number=ctx.claims.ura_number,
        encrypted_pseudonym=resolved.encrypted,
        source=source,
    )

    return Response(status_code=204)
