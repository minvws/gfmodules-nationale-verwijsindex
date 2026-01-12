import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from app import dependencies
from app.exceptions.fhir_exception import FHIRException
from app.models.data_domain import DataDomain
from app.models.fhir.bundle import Bundle
from app.models.fhir.resources.data_reference.requests import DataReferenceRequestParams
from app.models.fhir.resources.data_reference.resource import (
    NVIDataReferenceOutput,
    NVIDataRefrenceInput,
)
from app.models.pseudonym import Pseudonym
from app.models.ura import UraNumber
from app.services.prs.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["NVI Data Reference"], prefix="/NVIDataReference")


@router.get("", status_code=200)
def get_reference(
    params: Annotated[DataReferenceRequestParams, Query()],
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
) -> Bundle[NVIDataReferenceOutput]:
    if params.pseudonym and params.oprf_key:
        pseudonym = exchange_oprf(
            pseudonym_service=pseudonym_service,
            oprf_jwe=params.pseudonym,
            blind_factor=params.oprf_key,
        )

        if params.care_context:
            patient_reference = referral_service.get_specific_patient(
                ura_number=UraNumber(params.source),
                pseudonym=pseudonym,
                data_domain=DataDomain(params.care_context),
            )
            return Bundle.from_reference_outputs(patient_reference)

    registrations = referral_service.get_all_registrations(ura_number=UraNumber(params.source))
    return Bundle.from_reference_outputs(registrations)


@router.delete("")
def delete_reference(
    params: Annotated[DataReferenceRequestParams, Query()],
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
) -> Response:
    if params.pseudonym and params.oprf_key:
        pseudonym = exchange_oprf(
            pseudonym_service=pseudonym_service,
            oprf_jwe=params.pseudonym,
            blind_factor=params.oprf_key,
        )

        if params.care_context is None:
            referral_service.delete_patient_registrations(
                ura_number=UraNumber(params.source),
                pseudonym=pseudonym,
            )
        else:
            referral_service.delete_specific_registration(
                ura_number=UraNumber(params.source),
                data_domain=DataDomain(params.care_context),
                pseudonym=pseudonym,
            )

        return Response(status_code=204)

    referral_service.delete_specific_organization(ura_number=UraNumber(params.source))
    return Response(status_code=204)


@router.post("", response_model=NVIDataReferenceOutput, status_code=201)
def create_reference(
    data: NVIDataRefrenceInput,
    request: Request,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
    pseudonym_service: PseudonymService = Depends(dependencies.get_pseudonym_service),
) -> NVIDataReferenceOutput:
    source_url = str(request.url)
    pseudonym = exchange_oprf(
        pseudonym_service=pseudonym_service,
        oprf_jwe=data.oprf_key,
        blind_factor=data.subject.value,
    )

    new_reference = referral_service.add_one(
        pseudonym=pseudonym,
        data_domain=data.get_data_domain(),
        ura_number=data.get_ura_number(),
        organization_type=data.get_organization_type(),
        uzi_number=data.source.value,
        request_url=source_url,
    )
    return new_reference


def exchange_oprf(pseudonym_service: PseudonymService, oprf_jwe: str, blind_factor: str) -> Pseudonym:
    try:
        return pseudonym_service.exchange(oprf_jwe=oprf_jwe, blind_factor=blind_factor)
    except Exception as e:
        logger.error(f"failed to exchange pseudonym: {e}")
        raise FHIRException(
            status_code=500,
            severity="error",
            code="not-found",
            msg="Pseudonym could not be exchanged",
            diagnostics=str(e),
            expression=["NVIDataReference.subject"],
        )


@router.get("/{id}", status_code=200)
def get_by_id(
    id: UUID,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
) -> NVIDataReferenceOutput:
    data_reference = referral_service.get_by_id(id)
    return data_reference


@router.delete("/{id}")
def delete_by_id(
    id: UUID,
    referral_service: ReferralService = Depends(dependencies.get_referral_service),
) -> Response:
    referral_service.delete_by_id(id)
    return Response(status_code=204)
