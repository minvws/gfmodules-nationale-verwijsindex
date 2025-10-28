import logging
from typing import List

from fastapi import APIRouter, Depends, Header, Request, status
from opentelemetry import trace
from starlette.responses import Response

from app import dependencies
from app.data import UraNumber
from app.data_models.referrals import (
    CreateReferralRequest,
    DeleteReferralRequest,
    ReferralEntry,
    ReferralQuery,
    ReferralRequest,
    ReferralRequestHeader,
)
from app.services.jwt_validator import JwtValidationError, JwtValidator
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
    referral_request: CreateReferralRequest,
    request: Request,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    requesting_ura_number: UraNumber = Depends(dependencies.authenticated_ura),
) -> Response:
    """
    Creates a referral
    """
    span = trace.get_current_span()
    span.update_name(
        f"POST /info data_domain={str(referral_request.data_domain)}, ura_number={str(referral_request.ura_number)}"
    )

    referral: ReferralEntry = referral_service.create_referral(
        create_req=referral_request,
        requesting_ura_number=requesting_ura_number,
        request_url=str(request.url),
    )
    span.set_attribute("data.referral", referral.model_dump_json())

    return Response(status_code=201)


@router.post(
    "/query",
    summary="Queries referrals by pseudonym or data domain",
    response_model=List[ReferralEntry],
    status_code=status.HTTP_201_CREATED,
)
def query_referrals(
    query_request: ReferralQuery,
    request: Request,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    requesting_ura_number: UraNumber = Depends(dependencies.authenticated_ura),
) -> List[ReferralEntry] | Response:
    """
    Queries referrals by optional pseudonym or optional data domain
    """
    span = trace.get_current_span()
    span.update_name(
        f"POST {router.prefix}/query data_domain={str(query_request.data_domain)} ura_number={str(query_request.ura_number)}"
    )

    referrals = referral_service.query_referrals(
        query_request=query_request,
        request_url=str(request.url),
        requesting_ura_number=requesting_ura_number,
    )
    span.set_attribute("data.referrals_found", len(referrals))
    span.set_attribute("data.referrals", [referral.model_dump_json() for referral in referrals])

    return referrals


@router.delete("/", summary="Deletes a referral", status_code=status.HTTP_204_NO_CONTENT)
def delete_referral(
    request: Request,
    delete_request: DeleteReferralRequest,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    requesting_ura_number: UraNumber = Depends(dependencies.authenticated_ura),
) -> Response:
    """
    Deletes a referral
    """
    span = trace.get_current_span()
    span.update_name(
        f"DELETE {router.prefix}/ data_domain={str(delete_request.data_domain)} ura_number={str(delete_request.ura_number)}"
    )
    referral_service.delete_referral(
        delete_request=delete_request,
        requesting_ura_number=requesting_ura_number,
        request_url=str(request.url),
    )
    span.set_attribute("data.referral_deleted", True)
    return Response(status_code=204)


@router.post(
    "/info",
    summary="Queries referrals by pseudonym and data domain and checks for authorization in LMR",
    response_model=List[ReferralEntry],
)
def get_referral_info(
    referral_request: ReferralRequest,
    request: Request,
    header: ReferralRequestHeader = Header(),
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    requesting_ura_number: UraNumber = Depends(dependencies.authenticated_ura),
    jwt_validator: JwtValidator = Depends(dependencies.get_jwt_validator),
) -> List[ReferralEntry]:
    """
    Searches for referrals by pseudonym and data domain
    """
    span = trace.get_current_span()
    span.update_name(f"POST /info data_domain={str(referral_request.data_domain)}")

    try:
        # Validate the JWT token - this will raise an exception if invalid
        if not header.authorization.startswith("Bearer "):
            raise ValueError("Invalid JWT token format")
        jwt_token = header.authorization.removeprefix("Bearer ").strip()
        decoded_token = jwt_validator.validate_lrs_jwt(jwt_token, requesting_ura_number)
    except JwtValidationError as e:
        raise ValueError(f"Invalid JWT token: {e}")

    referrals = referral_service.request_uras_for_timeline(
        referral_request=referral_request,
        requesting_ura_number=requesting_ura_number,
        requesting_uzi_number=decoded_token["dezi_jwt"]["uzi_id"],
        request_url=str(request.url),
        breaking_glass=decoded_token["breaking_glass"],
    )

    span.set_attribute("data.referrals_found", len(referrals))
    span.set_attribute("data.referrals", [referral.model_dump_json() for referral in referrals])

    return referrals
