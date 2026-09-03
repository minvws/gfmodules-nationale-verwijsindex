import logging
from typing import Annotated, Any

import gfmodules.logging as gflog
from fastapi import APIRouter, Body, Depends

from app.dependencies import (
    get_pseudonym_resolver,
    get_referral_service,
)
from app.logging.events import Log
from app.models.auth.context import AuthContext
from app.models.auth.data import AuthorizationScope
from app.models.registrations import LocalizeRequest, Registration
from app.routers.dependencies import require_scope
from app.services.pseudonym_resolver import PseudonymResolver
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Localization"], prefix="/localize")


@router.post("")
def localize(
    data: Annotated[LocalizeRequest, Body()],
    referral_service: Annotated[ReferralService, Depends(get_referral_service)],
    pseudonym_resolver: Annotated[PseudonymResolver, Depends(get_pseudonym_resolver)],
    ctx: Annotated[AuthContext, Depends(require_scope(AuthorizationScope.LOCALIZE))],
) -> Any:
    resolved = pseudonym_resolver.resolve_jwe(jwe=data.pseudonym, blind_factor=data.oprf_key)

    results = referral_service.get_many(encrypted_pseudonym=resolved.encrypted)

    ura_number = str(ctx.claims.ura_number)
    if results:
        gflog.emit(
            logger,
            Log.LOCALIZATION_SUCCESS,
            "Localization succeeded",
            fields={
                "organization": ctx.claims.organization_name,
                "ura_number": ura_number,
                "pseudonym_hash": str(resolved.response),
                "result_count": len(results),
            },
        )
    else:
        gflog.emit(
            logger,
            Log.LOCALIZATION_NO_MATCH,
            "Localization returned no match",
            fields={"ura_number": ura_number, "result_count": 0},
        )

    return [Registration.from_entity(r) for r in results]
