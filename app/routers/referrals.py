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
    response_model=None,
)
def create_referral(
    payload: CreateReferralRequest,
    request: Request,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
    _: UraNumber = Depends(dependencies.authenticated_ura),
) -> Response:
    """
    Creates a referral
    """
    span = trace.get_current_span()
    span.update_name(f"POST /info data_domain={str(payload.data_domain)}, ura_number={str(payload.ura_number)}")

    try:
        localisation_pseudonym = pseudonym_service.exchange(
            oprf_jwe=payload.oprf_jwe,
            blind_factor=payload.blind_factor,
        )
    except Exception as e:
        logger.error(f"Failed to exchange pseudonym: {e}")
        return Response(status_code=404)

    referral: ReferralEntry = referral_service.add_one_referral(
        pseudonym=localisation_pseudonym,
        data_domain=payload.data_domain,
        ura_number=payload.ura_number,
        uzi_number=payload.requesting_uzi_number,
        request_url=str(request.url),
        encrypted_lmr_id=payload.encrypted_lmr_id,
    )
    span.set_attribute("data.referral", str(referral))

    return Response(status_code=201)


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
) -> List[ReferralEntry] | Response:
    """
    Queries referrals by optional pseudonym or optional data domain
    """
    span = trace.get_current_span()
    span.update_name(
        f"POST {router.prefix}/query data_domain={str(payload.data_domain)} ura_number={str(payload.ura_number)}"
    )
    request_url = str(request.url)
    localisation_pseudonym = None
    if payload.oprf_jwe and payload.blind_factor:
        try:
            localisation_pseudonym = pseudonym_service.exchange(
                oprf_jwe=payload.oprf_jwe,
                blind_factor=payload.blind_factor,
            )
        except Exception as e:
            logger.error(f"Failed to exchange pseudonym: {e}")
            return Response(status_code=404)

    referrals = referral_service.query_referrals(
        pseudonym=localisation_pseudonym,
        data_domain=payload.data_domain,
        ura_number=payload.ura_number,
        request_url=request_url,
    )
    span.set_attribute("data.referrals_found", len(referrals))
    span.set_attribute("data.referrals", str(referrals))

    return referrals


@router.delete("/", summary="Deletes a referral", status_code=status.HTTP_204_NO_CONTENT)
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
    span.update_name(f"DELETE {router.prefix}/ data_domain={str(req.data_domain)} ura_number={str(req.ura_number)}")
    request_url = str(request.url)
    try:
        localisation_pseudonym = pseudonym_service.exchange(
            oprf_jwe=req.oprf_jwe,
            blind_factor=req.blind_factor,
        )
    except Exception as e:
        logger.error(f"Failed to exchange pseudonym: {e}")
        return Response(status_code=404)

    referral_service.delete_one_referral(
        pseudonym=localisation_pseudonym,
        data_domain=req.data_domain,
        ura_number=req.ura_number,
        request_url=request_url,
    )
    return Response(status_code=204)
