import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_bundle_service
from app.exceptions.fhir_exception import FHIRException
from app.models.fhir.bundle import Bundle
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.ura import UraNumber
from app.services.fhir.bundle import BundleService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["v1-alpha - FHIR"], prefix="/v1-alpha/fhir")


@router.post("", response_model_exclude_none=True)
def register(
    data: Bundle[LocalizationList],
    request: Request,
    localisation_list_service: BundleService = Depends(get_bundle_service),
) -> Any:
    cert_ura: UraNumber = request.state.auth.ura_number
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
        result = localisation_list_service.process_entry(authenticated_ura=cert_ura, entry=entry, index=i)
        results_bundle.entry.append(result)
    return results_bundle
