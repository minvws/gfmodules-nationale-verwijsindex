import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_bundle_service, get_capability_statement
from app.models.fhir.bundle import Bundle
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.models.fhir.resources.operation_outcome.resource import OperationOutcome
from app.models.response import FHIRJSONResponse
from app.models.ura import UraNumber
from app.services.exceptions import InvalidModelError
from app.services.fhir.bundle import BundleService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["poc - FHIR"], prefix="/fhir")


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
        raise InvalidModelError("Bundle.entry is invalid")
    for i, entry in enumerate(data.entry):
        result = localisation_list_service.process_entry(authenticated_ura=cert_ura, entry=entry, index=i)
        results_bundle.entry.append(result)
    return results_bundle


@router.get(
    "/metadata",
    status_code=200,
    response_model_exclude_none=True,
    summary="FHIR CapabilityStatement",
    description="Retrieve the FHIR CapabilityStatement for this server.",
    responses={
        200: {
            "description": "Successful retrieval of CapabilityStatement",
            "content": {"application/fhir+json": {}},
        },
        500: {"model": OperationOutcome},
    },
)
def metadata(
    capability_statement: Annotated[dict[str, Any], Depends(get_capability_statement)],
) -> FHIRJSONResponse:
    """Return the FHIR CapabilityStatement for this server."""
    return FHIRJSONResponse(content=capability_statement)
