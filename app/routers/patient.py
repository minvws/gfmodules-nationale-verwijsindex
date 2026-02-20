import logging
from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_referral_service
from app.models.fhir.bundle import Bundle
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Patient"], prefix="/Patient")


@router.post("")
def register(
    data: Bundle[LocalizationList],
    referral_service: ReferralService = Depends(get_referral_service),
) -> Any:
    # TODO: Validation here
    method = data.entry[0].request.method

    # do pseudonym

    match method:
        case "DELETE":
            # do delete
            pass
        case "POST":
            # add
            pass
