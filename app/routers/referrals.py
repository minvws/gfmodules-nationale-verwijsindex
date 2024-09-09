import logging
from typing import List
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from opentelemetry import trace
from starlette.responses import Response

from app import container
from app.authentication import authenticated_ura
from app.config import get_config
from app.data import UraNumber
from app.services.referral_service import ReferralService
from app.response_models.referrals import ReferralRequest, ReferralEntry, CreateReferralRequest
from app.services.pseudonym_service import PseudonymService

logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["Referrals"],
)


@router.post(
    "/info",
    summary="Gets information about the referrals by pseudonym and data domain",
    response_model=List[ReferralEntry],
)
def get_referral_info(
    req: ReferralRequest,
    referral_service: ReferralService = Depends(container.get_referral_service),
    pseudonym_service: PseudonymService = Depends(container.get_pseudonym_service),
    _: UraNumber = Depends(authenticated_ura)
) -> List[ReferralEntry]:
    """
    Searches for referrals by pseudonym and data domain
    """
    span = trace.get_current_span()
    span.update_name(f"POST /info pseudonym={str(req.pseudonym)} data_domain={str(req.data_domain)}")

    localisation_pseudonym = pseudonym_service.exchange(req.pseudonym, get_config().app.provider_id)
    referrals = referral_service.get_referrals_by_domain_and_pseudonym(
        pseudonym=localisation_pseudonym, data_domain=req.data_domain
    )
    span.set_attribute("data.referrals_found", len(referrals))

    if len(referrals) == 0:
        raise HTTPException(status_code=404, detail="No referrals found")

    span.set_attribute("data.referrals", str(referrals))

    return referrals


@router.post(
    "/create",
    summary="Creates a referral",
    response_model=ReferralEntry,
)
def create_referral(
    req: CreateReferralRequest,
    referral_service: ReferralService = Depends(container.get_referral_service),
) -> ReferralEntry:
    """
    Creates a referral
    """
    span = trace.get_current_span()
    span.update_name(f"POST /create pseudonym={str(req.pseudonym)} data_domain={str(req.data_domain)}, ura_number={str(req.ura_number)}")

    referral = referral_service.add_one_referral(
        pseudonym=req.pseudonym, data_domain=req.data_domain, ura_number=req.ura_number
    )
    span.set_attribute("data.referral", str(referral))

    return referral

@router.post(
    "/delete",
    summary="Deletes a referral",
)
def delete_referral(
    req: CreateReferralRequest,
    referral_service: ReferralService = Depends(container.get_referral_service),
    _: UraNumber = Depends(authenticated_ura)
) -> Response:
    """
    Deletes a referral by URA
    """
    span = trace.get_current_span()
    span.update_name(f"POST /delete  ura_number={str(req.ura_number)}")

    referral = referral_service.delete_one_referral(pseudonym=req.pseudonym, data_domain=req.data_domain, ura_number=req.ura_number)
    span.set_attribute("data.referral-removed", str(referral))

    if referral:
        return Response(status_code=204)
    else:
        return Response(status_code=404)
