import base64
import json
import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.params import Query

from app.dependencies import (
    get_localization_list_service,
    get_pseudonym_service,
    get_referral_service,
)
from app.exceptions.fhir_exception import FHIRException
from app.models.data_domain import DataDomain
from app.models.fhir.bundle import (
    Bundle,
    BundleEntry,
)
from app.models.fhir.resources.localization_list.request import LocalizationListParams
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.pseudonym import Pseudonym
from app.services.localization_list import LocalizationListService
from app.services.prs.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["v1-alpha - FHIR"], prefix="/v1-alpha/fhir")


@router.post("", response_model_exclude_none=True)
def register(
    data: Bundle[LocalizationList],
    localisation_list_service: LocalizationListService = Depends(get_localization_list_service),
) -> Any:
    results_bundle = Bundle[Any](entry=[])
    valid_bundle = localisation_list_service.validate_localization_bundle_structure(data)
    if not valid_bundle:
        raise FHIRException(
            status_code=400,
            severity="error",
            code="structural",
            msg="Bundle.entry is invalid",
        )
    for i, entry in enumerate(data.entry):
        result = localisation_list_service.process_entry(entry=entry, index=i)
        results_bundle.entry.append(result)
    return results_bundle


@router.get("/List")
def get_list(
    params: Annotated[LocalizationListParams, Query()],
    referral_service: ReferralService = Depends(get_referral_service),
    pseudonym_service: PseudonymService = Depends(get_pseudonym_service),
) -> Any:
    if params.patient is None and params.source is None:
        raise FHIRException(
            status_code=400,
            severity="error",
            code="invalid",
            msg="Missing properties, either patient.identifier or source.identifier must be present",
        )

    code: str | None = None
    pseudonym: Pseudonym | None = None
    source: str | None = None

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
            data = json.loads(decoded_token)
            pseudonym = pseudonym_service.exchange(oprf_jwe=data["pseudonym"], blind_factor=data["oprfKey"])
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

    referrals = referral_service.get_many(pseudonym=pseudonym, source=source, data_domain=DataDomain(code))
    bundle = Bundle(
        type="searchset",
        total=len(referrals),
        entry=[BundleEntry(resource=LocalizationList.from_referral(r)) for r in referrals],
    )

    return bundle


@router.post("/List")
def add_list(
    data: LocalizationList,
    referral_service: ReferralService = Depends(get_referral_service),
    pseudonym_service: PseudonymService = Depends(get_pseudonym_service),
) -> Any:
    try:
        encoded_token = data.get_encoded_pseudonym()
        decoded_token = base64.urlsafe_b64decode(encoded_token)
        oprf_data = json.loads(decoded_token)
        pseudoym = pseudonym_service.exchange(oprf_jwe=oprf_data["pseudonym"], blind_factor=oprf_data["oprfKey"])
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
