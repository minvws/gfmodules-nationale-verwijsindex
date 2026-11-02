from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_pseudonym_referral_service
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.pseudonym import OprfPseudonym
from app.models.registrations import Registration
from app.routers.dependencies import require_scope
from app.services.pseudonym_referral_service import PseudonymReferralService

router = APIRouter(tags=["Localization"], prefix="/localize")


@router.post("")
def localize(
    pseudonym: Annotated[OprfPseudonym, Body()],
    pseudonym_referral_service: Annotated[PseudonymReferralService, Depends(get_pseudonym_referral_service)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.LOCALIZE))],
) -> Any:
    _, results = pseudonym_referral_service.localize(pseudonym, ctx.claims.ura_number)

    return [Registration.from_entity(r) for r in results]
