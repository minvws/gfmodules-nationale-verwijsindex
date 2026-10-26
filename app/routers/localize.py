from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import (
    get_pseudonym_resolver,
    get_referral_service,
)
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.registrations import LocalizeRequest, Registration
from app.routers.dependencies import require_scope
from app.services.pseudonym_resolver import PseudonymResolver
from app.services.referral_service import ReferralService

router = APIRouter(tags=["Localization"], prefix="/localize")


@router.post("")
def localize(
    data: Annotated[LocalizeRequest, Body()],
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    pseudonym_resolver: Annotated[PseudonymResolver, Depends(get_pseudonym_resolver)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.LOCALIZE))],
) -> Any:
    resolved = pseudonym_resolver.resolve_jwe(jwe=data.pseudonym, blind_factor=data.oprf_key)

    results = referral_service.localize(resolved.encrypted, ctx.claims.ura_number, ctx.claims.organization_name)

    return [Registration.from_entity(r) for r in results]
