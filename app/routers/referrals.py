import logging
from typing import List
from fastapi import APIRouter, Depends
from opentelemetry import trace
from starlette.responses import Response

from app import container
from app.authentication import authenticated_ura
from app.data import UraNumber
from app.services.referral_service import ReferralService
from app.response_models.referrals import ReferralEntry, CreateReferralRequest, ReferralQuery, DeleteReferralRequest

logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["Referral registrations"],
    prefix="/registrations",
)

@router.post(
    "/",
    summary="Creates a referral",
    response_model=ReferralEntry,
)
def create_referral(
    req: CreateReferralRequest,
    referral_service: ReferralService = Depends(container.get_referral_service),
    _: UraNumber = Depends(authenticated_ura)
) -> ReferralEntry:
    """
    Creates a referral
    """
    span = trace.get_current_span()
    span.update_name(f"POST {router.prefix}/ pseudonym={str(req.pseudonym)} data_domain={str(req.data_domain)}, ura_number={str(req.ura_number)}")

    referral = referral_service.add_one_referral(pseudonym=req.pseudonym, data_domain=req.data_domain, ura_number=req.ura_number)
    span.set_attribute("data.referral", str(referral))

    return referral

@router.post(
    "/query",
    summary="Queries referrals by pseudonym or data domain",
    response_model=List[ReferralEntry],
)
def query_referrals(
    req: ReferralQuery,
    referral_service: ReferralService = Depends(container.get_referral_service),
    _: UraNumber = Depends(authenticated_ura)
) -> List[ReferralEntry]:
    """
    Queries referrals by optional pseudonym or optional data domain
    """
    span = trace.get_current_span()
    span.update_name(f"POST {router.prefix}/query pseudonym={str(req.pseudonym)} data_domain={str(req.data_domain)} ura_number={str(req.ura_number)}")

    referrals = referral_service.query_referrals(pseudonym=req.pseudonym, data_domain=req.data_domain, ura_number=req.ura_number)
    span.set_attribute("data.referrals_found", len(referrals))
    span.set_attribute("data.referrals", str(referrals))

    return referrals

@router.delete(
    "/",
    summary="Deletes a referral",
)
def delete_referral(
    req: DeleteReferralRequest,
    referral_service: ReferralService = Depends(container.get_referral_service),
    _: UraNumber = Depends(authenticated_ura)
) -> Response:
    """
    Deletes a referral
    """
    span = trace.get_current_span()
    span.update_name(f"DELETE {router.prefix}/ pseudonym={str(req.pseudonym)} data_domain={str(req.data_domain)} ura_number={str(req.ura_number)}")
    referral_service.delete_one_referral(pseudonym=req.pseudonym, data_domain=req.data_domain, ura_number=req.ura_number)
    return Response(status_code=204)
