from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request

from app.dependencies import get_pseudonym_service, get_referral_service
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope, RequestedAction
from app.models.registrations import LocalizeRequest, Registration
from app.services.auth.auth_context import AuthContextService
from app.services.exceptions import UnauthorizedActionError, UnauthorizedScopeError
from app.services.prs.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService

router = APIRouter(tags=["Localization"], prefix="/localize")


@router.post("")
def localize(
    request: Request,
    data: Annotated[LocalizeRequest, Body()],
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    pseudonym_service: Annotated[PseudonymService, Depends(get_pseudonym_service)],
) -> Any:
    ctx: AuthContext = request.state.auth
    if AuthorizationScope.LOCALIZE not in ctx.scope:
        raise UnauthorizedScopeError(ctx.scope, AuthorizationScope.LOCALIZE)

    valid_action = AuthContextService.validate_action(ctx, RequestedAction.LOCALIZING)
    if not valid_action:
        raise UnauthorizedActionError(RequestedAction.LOCALIZING, ctx.role)

    pseudonym = pseudonym_service.exchange(oprf_jwe=data.pseudonym, blind_factor=data.oprf_key)

    results = referral_service.get_many(pseudonym=pseudonym)

    return [Registration.from_entity(r) for r in results]
