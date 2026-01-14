import logging
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies import get_capability_statement

logger = logging.getLogger(__name__)
router = APIRouter(tags=["FHIR"], prefix="/fhir")


@router.get("/metadata", status_code=200, response_model_exclude_none=True, summary="FHIR CapabilityStatement")
def metadata(
    capability_statement: dict[str, Any] = Depends(get_capability_statement),
) -> JSONResponse:
    """Return the FHIR CapabilityStatement for this server."""
    return JSONResponse(content=capability_statement)
