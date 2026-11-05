from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, Response

from app.dependencies import get_pseudonym_referral_service
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.pseudonym import OprfPseudonym
from app.models.registrations import Registration, RegistrationList
from app.routers.dependencies import require_managing_source, require_scope
from app.services.pseudonym_referral_service import PseudonymReferralService

router = APIRouter(tags=["Registrations"], prefix="/registrations")


@router.get(
    "",
)
def get_registration(
    pseudonym_referral_service: Annotated[PseudonymReferralService, Depends(get_pseudonym_referral_service)],
    pseudonym: Annotated[OprfPseudonym, Query()],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.READ))],
) -> Any:
    _, results = pseudonym_referral_service.query(ctx.claims.ura_number, pseudonym=pseudonym)

    return RegistrationList.from_entities(results)


@router.post(
    "",
    status_code=201,
    responses={200: {"description": "The registration already existed and is returned unchanged"}},
)
def add_registration(
    pseudonym: Annotated[OprfPseudonym, Body()],
    response: Response,
    pseudonym_referral_service: Annotated[PseudonymReferralService, Depends(get_pseudonym_referral_service)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.CREATE))],
    source: Annotated[str, Depends(require_managing_source)],
) -> Any:
    referral, created = pseudonym_referral_service.register(
        pseudonym,
        ura_number=ctx.claims.ura_number,
        source=source,
    )
    if not created:
        response.status_code = 200
    return Registration.from_entity(referral)


@router.delete("")
def delete_registration(
    pseudonym: Annotated[OprfPseudonym, Query()],
    pseudonym_referral_service: Annotated[PseudonymReferralService, Depends(get_pseudonym_referral_service)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.DELETE))],
    source: Annotated[str, Depends(require_managing_source)],
) -> Any:
    pseudonym_referral_service.delete_many(
        ctx.claims.ura_number,
        pseudonym=pseudonym,
        source=source,
    )

    return Response(status_code=204)
