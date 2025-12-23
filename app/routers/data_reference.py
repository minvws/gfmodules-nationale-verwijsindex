import logging
from typing import Annotated, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app import dependencies
from app.models.data_domain import DataDomain
from app.models.data_reference.requests import (
    DataReferenceRequestParams,
)
from app.models.referrals.entry import ReferralEntry
from app.models.ura import UraNumber
from app.services.prs.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["NVI Data Reference"], prefix="/NVIDataReference")


@router.get("/")
def get_reference(
    params: Annotated[DataReferenceRequestParams, Query()],
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
) -> List[ReferralEntry]:
    if params.pseudonym and params.oprf_key:
        try:
            localisation_pseudonym = pseudonym_service.exchange(oprf_jwe=params.pseudonym, blind_factor=params.oprf_key)
        except Exception as e:
            logger.error(f"Failed to exchange pseudonym: {e}")
            raise HTTPException(status_code=404)

        if params.care_context:
            return referral_service.get_specific_patient(
                ura_number=UraNumber(params.source),
                pseudonym=localisation_pseudonym,
                data_domain=DataDomain(params.care_context),
            )

    return referral_service.get_all_registrations(ura_number=UraNumber(params.source))


@router.delete("/")
def delete_reference(
    params: Annotated[DataReferenceRequestParams, Query()],
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
) -> Any:
    if params.pseudonym and params.oprf_key:
        try:
            localisation_pseudonym = pseudonym_service.exchange(oprf_jwe=params.pseudonym, blind_factor=params.oprf_key)
        except Exception as e:
            logger.error(f"Failed to exchange pseudonym: {e}")
            raise HTTPException(status_code=404)

        if params.care_context is None:
            referral_service.delete_patient_registrations(
                ura_number=UraNumber(params.source),
                pseudonym=localisation_pseudonym,
            )
        else:
            referral_service.delete_specific_registration(
                ura_number=UraNumber(params.source),
                data_domain=DataDomain(params.care_context),
                pseudonym=localisation_pseudonym,
            )

        return Response(status_code=204)

    referral_service.delete_specific_organization(ura_number=UraNumber(params.source))
    return Response(status_code=204)
