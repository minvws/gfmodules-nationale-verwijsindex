import logging
from typing import List

from fastapi import APIRouter, Depends, Request, status
from opentelemetry import trace
from starlette.responses import Response

from app import dependencies
from app.data import UraNumber
from app.response_models.referrals import (
    CreateReferralRequest,
    DeleteReferralRequest,
    ReferralEntry,
    ReferralQuery,
)
from app.services.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService

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
    payload: CreateReferralRequest,
    request: Request,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
    _: UraNumber = Depends(dependencies.authenticated_ura),
) -> ReferralEntry:
    """
    Creates a referral
    """
    span = trace.get_current_span()
    span.update_name(
        f"POST {router.prefix}/ pseudonym={str(payload.pseudonym)} data_domain={str(payload.data_domain)}, ura_number={str(payload.ura_number)}"
    )
    localisation_pseudonym = pseudonym_service.exchange(payload.pseudonym)

    referral: ReferralEntry = referral_service.add_one_referral(
        pseudonym=localisation_pseudonym,
        data_domain=payload.data_domain,
        ura_number=payload.ura_number,
        uzi_number=payload.requesting_uzi_number,
        request_url=str(request.url),
    )
    span.set_attribute("data.referral", str(referral))

    return referral


@router.post(
    "/query",
    summary="Queries referrals by pseudonym or data domain",
    response_model=List[ReferralEntry],
    status_code=status.HTTP_201_CREATED,
)
def query_referrals(
    payload: ReferralQuery,
    request: Request,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
    _: UraNumber = Depends(dependencies.authenticated_ura),
) -> List[ReferralEntry]:
    """
    Queries referrals by optional pseudonym or optional data domain
    """
    span = trace.get_current_span()
    span.update_name(
        f"POST {router.prefix}/query pseudonym={str(payload.pseudonym)} data_domain={str(payload.data_domain)} ura_number={str(payload.ura_number)}"
    )
    request_url = str(request.url)

    localisation_pseudonym = None
    if payload.pseudonym is not None:
        localisation_pseudonym = pseudonym_service.exchange(payload.pseudonym)

    referrals = referral_service.query_referrals(
        pseudonym=localisation_pseudonym,
        data_domain=payload.data_domain,
        ura_number=payload.ura_number,
        request_url=request_url,
    )
    span.set_attribute("data.referrals_found", len(referrals))
    span.set_attribute("data.referrals", str(referrals))

    return referrals


@router.delete(
    "/", summary="Deletes a referral", status_code=status.HTTP_204_NO_CONTENT
)
def delete_referral(
    request: Request,
    req: DeleteReferralRequest,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
    _: UraNumber = Depends(dependencies.authenticated_ura),
) -> Response:
    """
    Deletes a referral
    """
    span = trace.get_current_span()
    span.update_name(
        f"DELETE {router.prefix}/ pseudonym={str(req.pseudonym)} data_domain={str(req.data_domain)} ura_number={str(req.ura_number)}"
    )
    request_url = str(request.url)
    localisation_pseudonym = pseudonym_service.exchange(req.pseudonym)

    referral_service.delete_one_referral(
        pseudonym=localisation_pseudonym,
        data_domain=req.data_domain,
        ura_number=req.ura_number,
        request_url=request_url,
    )
    return Response(status_code=204)
