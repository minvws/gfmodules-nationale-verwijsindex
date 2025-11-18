import logging
from typing import List

from fastapi import APIRouter, Depends, Header, Response
from opentelemetry import trace

from app import dependencies
from app.data import DataDomain, UraNumber
from app.jwt_validator import JwtValidationError, JwtValidator
from app.response_models.referrals import ReferralEntry, ReferralRequest, ReferralRequestHeader
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
    header: ReferralRequestHeader = Header(),
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
    client_ura_number: UraNumber = Depends(dependencies.authenticated_ura),
    jwt_validator: JwtValidator = Depends(dependencies.get_jwt_validator),
) -> List[ReferralEntry] | Response:
    """
    Searches for referrals by pseudonym and data domain
    """
    span = trace.get_current_span()
    span.update_name(f"POST /info data_domain={str(req.data_domain)}")

    try:
        # Validate the JWT token - this will raise an exception if invalid
        if not header.authorization.startswith("Bearer "):
            raise ValueError("Invalid JWT token format")
        jwt_token = header.authorization.removeprefix("Bearer ").strip()
        decoded_token = jwt_validator.validate_lrs_jwt(jwt_token, str(client_ura_number))
    except JwtValidationError as e:
        raise ValueError(f"Invalid JWT token: {e}")

    try:
        localisation_pseudonym = pseudonym_service.exchange(req.oprf_jwe, req.blind_factor)
    except Exception as e:
        logger.error(f"Failed to exchange pseudonym: {e}")
        return Response(status_code=404)

    referrals = referral_service.get_referrals_by_domain_and_pseudonym(
        pseudonym=localisation_pseudonym,
        data_domain=DataDomain(value=req.data_domain),
        client_ura_number=client_ura_number,
        breaking_glass=decoded_token["breaking_glass"],
    )
    span.set_attribute("data.referrals_found", len(referrals))
    span.set_attribute("data.referrals", str(referrals))

    return referrals
