import logging
from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import (
    get_localization_list_service,
)
from app.exceptions.fhir_exception import FHIRException
from app.models.fhir.bundle import (
    Bundle,
)
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.services.localization_list import LocalizationListService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["FHIR"], prefix="/v1-alpha/fhir")


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
