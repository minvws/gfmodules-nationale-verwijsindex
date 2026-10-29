from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_pseudonym_referral_service
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.registrations import LocalizeRequest, Registration
from app.routers.dependencies import require_scope
from app.services.pseudonym_referral_service import PseudonymReferralService

router = APIRouter(tags=["Localization"], prefix="/localize")


@router.post("")
def localize(
    data: Annotated[LocalizeRequest, Body()],
    pseudonym_referral_service: Annotated[PseudonymReferralService, Depends(get_pseudonym_referral_service)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.LOCALIZE))],
) -> Any:
    results = pseudonym_referral_service.localize(data.oprf_pseudonym(), ctx.claims.ura_number)

    return [Registration.from_entity(r) for r in results]
