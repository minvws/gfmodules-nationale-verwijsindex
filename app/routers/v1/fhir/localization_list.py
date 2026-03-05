import base64
import json
import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.params import Query

from app.dependencies import get_pseudonym_service, get_referral_service
from app.exceptions.fhir_exception import FHIRException
from app.models.data_domain import DataDomain
from app.models.fhir.bundle import Bundle, BundleEntry
from app.models.fhir.resources.localization_list.request import (
    LocalizationListParams,
)
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.pseudonym import Pseudonym
from app.models.response import DeleteResponse
from app.models.ura import UraNumber
from app.services.prs.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["v1-alpha - FHIR"], prefix="/v1-alpha/fhir/List")


@router.post(path="")
def create(
    data: LocalizationList,
    referral_service: ReferralService = Depends(get_referral_service),
    pseudonym_service: PseudonymService = Depends(get_pseudonym_service),
) -> Any:
    logging.info(f"Creating {data.model_dump_json()}")
    try:
        encoded_token = data.get_encoded_pseudonym()
        print(encoded_token)
        decoded_token = base64.urlsafe_b64decode(encoded_token)
        print(decoded_token)
        oprf_data = json.loads(decoded_token)
        print(oprf_data)
        pseudoym = pseudonym_service.exchange(
            oprf_jwe=oprf_data["evaluated_output"],
            blind_factor=oprf_data["blind_factor"],
        )
    except Exception as e:
        logger.error(f"error occurred while decoding pseudonym token: {e}")
        raise FHIRException(
            status_code=400,
            severity="error",
            code="invalid",
            msg="Invalid pseudonym in patient.identifier",
        )

    new_referral = referral_service.add_one(
        ura_number=data.get_ura(),
        pseudonym=pseudoym,
        data_domain=data.get_data_domain(),
        source=data.get_device(),
    )

    return LocalizationList.from_referral(new_referral)


@router.get("/{id}")
def get(
    id: UUID,
    referral_service: ReferralService = Depends(get_referral_service),
) -> Any:
    referral = referral_service.get_by_id(id)
    return LocalizationList.from_referral(referral)


@router.get(path="")
def query(
    request: Request,
    params: Annotated[LocalizationListParams, Query()],
    referral_service: ReferralService = Depends(get_referral_service),
    pseudonym_service: PseudonymService = Depends(get_pseudonym_service),
) -> Any:

    code: str | None = None
    pseudonym: Pseudonym | None = None
    source: str | None = None
    ura_number: UraNumber | None = None

    if params.empty():
        ura_number = request.state.auth.ura_number

    if params.patient:
        try:
            patient_identifier = params.get_patient_identifier()
        except ValueError as e:
            logger.error(f"error occurred while parcing query: {e}")
            raise FHIRException(
                status_code=400,
                severity="error",
                code="invalid",
                msg="Malformed patient.identifier parameter",
            )

        try:
            decoded_token = base64.urlsafe_b64decode(patient_identifier.value)
            oprf_data = json.loads(decoded_token)
            pseudonym = pseudonym_service.exchange(
                oprf_jwe=oprf_data["evaluated_output"],
                blind_factor=oprf_data["blind_factor"],
            )
        except Exception as e:
            logger.error(f"error occurred while decoding pseudonym token: {e}")
            raise FHIRException(
                status_code=400,
                severity="error",
                code="invalid",
                msg="Invalid pseudonym in patient.identifier",
            )

    if params.source:
        try:
            source_identifier = params.get_source_identifier()
            source = source_identifier.value
        except ValueError as e:
            logger.error(f"error occurred while parcing query: {e}")
            raise FHIRException(
                status_code=400,
                severity="error",
                code="invalid",
                msg="Malformed source.identifier parameter",
            )

        ura_number = request.state.auth.ura_number

    if params.code:
        code = params.code

    referrals = referral_service.get_many(
        pseudonym=pseudonym,
        source=source,
        data_domain=DataDomain(code) if code else None,
        ura_number=ura_number if ura_number else None,
    )
    bundle = Bundle(
        type="searchset",
        total=len(referrals),
        entry=[BundleEntry(resource=LocalizationList.from_referral(r)) for r in referrals],
    )

    return bundle


@router.delete(path="/{id}")
def delete(id: UUID, referral_service: ReferralService = Depends(get_referral_service)) -> Any:
    logging.info(f"Delete {id}")
    referral_service.delete_by_id(id)
    # TODO: this might be better as an operation outcome
    return DeleteResponse(status_code=204)


@router.delete(path="")
def delete_for_query(
    request: Request,
    params: Annotated[LocalizationListParams, Query()],
    referral_service: ReferralService = Depends(get_referral_service),
    pseudonym_service: PseudonymService = Depends(get_pseudonym_service),
) -> Any:
    code: str | None = None
    pseudonym: Pseudonym | None = None
    source: str | None = None
    ura_number = request.state.auth.ura_number

    if params.patient:
        try:
            patient_identifier = params.get_patient_identifier()
        except ValueError as e:
            logger.error(f"error occurred while parcing query: {e}")
            raise FHIRException(
                status_code=400,
                severity="error",
                code="invalid",
                msg="Malformed patient.identifier parameter",
            )

        try:
            decoded_token = base64.urlsafe_b64decode(patient_identifier.value)
            oprf_data = json.loads(decoded_token)
            pseudonym = pseudonym_service.exchange(
                oprf_jwe=oprf_data["evaluated_output"],
                blind_factor=oprf_data["blind_factor"],
            )
        except Exception as e:
            logger.error(f"error occurred while decoding pseudonym token: {e}")
            raise FHIRException(
                status_code=400,
                severity="error",
                code="invalid",
                msg="Invalid pseudonym in patient.identifier",
            )

    if params.source:
        try:
            source_identifier = params.get_source_identifier()
            source = source_identifier.value
        except ValueError as e:
            logger.error(f"error occurred while parcing query: {e}")
            raise FHIRException(
                status_code=400,
                severity="error",
                code="invalid",
                msg="Malformed source.identifier parameter",
            )

    if params.code:
        code = params.code

    referral_service.delete_many(
        pseudonym=pseudonym,
        source=source,
        data_domain=DataDomain(code) if code else None,
        ura_number=ura_number,
    )

    # TODO: Return operation outcome for delete many transaction
