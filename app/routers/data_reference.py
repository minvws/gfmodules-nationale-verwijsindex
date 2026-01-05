import logging
from typing import Annotated, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app import dependencies
from app.models.data_domain import DataDomain
from app.models.data_reference.bundle import Bundle
from app.models.data_reference.requests import (
    DataReferenceRequestParams,
)
from app.models.data_reference.resource import (
    NVIDataRefrenceInput,
)
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
) -> Bundle:
    if params.pseudonym and params.oprf_key:
        try:
            localisation_pseudonym = pseudonym_service.exchange(oprf_jwe=params.pseudonym, blind_factor=params.oprf_key)
        except Exception as e:
            logger.error(f"Failed to exchange pseudonym: {e}")
            raise HTTPException(status_code=404)

        if params.care_context:
            patient_reference = referral_service.get_specific_patient(
                ura_number=UraNumber(params.source),
                pseudonym=localisation_pseudonym,
                data_domain=DataDomain(params.care_context),
            )
            return Bundle.from_reference_outputs(patient_reference)

    registrations = referral_service.get_all_registrations(ura_number=UraNumber(params.source))
    return Bundle.from_reference_outputs(registrations)


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


@router.post("/")
def create_reference(
    request: Request,
    data: NVIDataRefrenceInput,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
) -> Response:
    source_url = str(request.url)
    try:
        localisatin_pseudonym = pseudonym_service.exchange(oprf_jwe=data.subject.value, blind_factor=data.oprf_key)
    except Exception as e:
        logger.error(f"failed to exchange pseudonym: {e}")
        raise HTTPException(status_code=404)

    new_reference = referral_service.add_one(
        pseudonym=localisatin_pseudonym,
        data_domain=data.get_data_domain(),
        ura_number=data.get_ura_number(),
        organization_type=data.get_organization_type(),
        uzi_number=data.source.value,
        request_url=source_url,
    )

    return Response(status_code=201, content=new_reference)


@router.get("/{id}")
def get_by_id(
    id: UUID,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
) -> Response:
    data_reference = referral_service.get_by_id(id)
    return Response(status_code=200, content=data_reference)


@router.delete("/{id}")
def delete_by_id(
    id: UUID,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
) -> Response:
    referral_service.delete_by_id(id)
    return Response(status_code=204)
