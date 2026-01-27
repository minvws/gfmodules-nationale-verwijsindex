import logging
from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_capability_statement
from app.exceptions.fhir_exception import OperationOutcome
from app.models.response import FHIRJSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["FHIR"], prefix="/fhir")


@router.get(
    "/metadata",
    status_code=200,
    response_model_exclude_none=True,
    summary="FHIR CapabilityStatement",
    description="Retrieve the FHIR CapabilityStatement for this server.",
    responses={
        200: {"description": "Successful retrieval of CapabilityStatement", "content": {"application/fhir+json": {}}},
        500: {"model": OperationOutcome},
    },
)
def metadata(
    capability_statement: dict[str, Any] = Depends(get_capability_statement),
) -> FHIRJSONResponse:
    """Return the FHIR CapabilityStatement for this server."""
    return FHIRJSONResponse(content=capability_statement)
