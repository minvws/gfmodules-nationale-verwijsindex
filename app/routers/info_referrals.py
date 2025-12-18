import logging
from typing import List

from fastapi import APIRouter, Depends, Response
from opentelemetry import trace

from app import dependencies
from app.models.data_domain import DataDomain
from app.models.referrals.entry import ReferralEntry
from app.models.referrals.requests import ReferralRequest
from app.services.prs.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["Referrals info"],
)


@router.post(
    "/info",
    summary="Gets information about the referrals by pseudonym and data domain",
    response_model=List[ReferralEntry],
)
def get_referral_info(
    req: ReferralRequest,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
) -> List[ReferralEntry] | Response:
    """
    Searches for referrals by pseudonym and data domain
    """
    span = trace.get_current_span()
    span.update_name(f"POST /info data_domain={str(req.data_domain)}")

    try:
        localisation_pseudonym = pseudonym_service.exchange(req.oprf_jwe, req.blind_factor)
    except Exception as e:
        logger.error(f"Failed to exchange pseudonym: {e}")
        return Response(status_code=404)

    referrals = referral_service.get_referrals_by_domain_and_pseudonym(
        pseudonym=localisation_pseudonym,
        data_domain=DataDomain(value=req.data_domain),
    )
    span.set_attribute("data.referrals_found", len(referrals))
    span.set_attribute("data.referrals", str(referrals))

    return referrals
