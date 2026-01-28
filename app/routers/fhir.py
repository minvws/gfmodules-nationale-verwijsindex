import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.data import HCIM_2024_ZIBS, NVI_ORGANIZATION_TYPES
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
        200: {
            "description": "Successful retrieval of CapabilityStatement",
            "content": {"application/fhir+json": {}},
        },
        500: {"model": OperationOutcome},
    },
)
def metadata(
    capability_statement: dict[str, Any] = Depends(get_capability_statement),
) -> FHIRJSONResponse:
    """Return the FHIR CapabilityStatement for this server."""
    return FHIRJSONResponse(content=capability_statement)


@router.get(
    "/CodeSystem/nvi-organization-type",
    status_code=200,
    summary="get CodeSystems for Organization types (SourceType)",
    description="Retrieves the acceptable codes values for an SourceType (Organization) in the NVI",
    responses={
        200: {
            "description": "A CodeSystem that contains value sets for the organization types accepted byt he NVI",
            "content": {
                "application/json": {
                    "example": {
                        "resourceType": "CodeSystem",
                        "name": "Some name",
                        "title": "Some title",
                        "status": "draft",
                        "description": "Some description",
                        "caseSensitive": True,
                        "concept": [
                            {
                                "code": "zbc",
                                "display": "Zelfstandig behandelcentrum",
                            },
                        ],
                    }
                }
            },
        }
    },
)
def get_org_types() -> Dict[str, Any]:
    data = {
        "resourceType": "CodeSystem",
        "name": "NVIOrganizationTypes",
        "title": "NVI Zorgaanbieder Types",
        "status": "draft",
        "description": "Classificatie van zorgaanbieders voor NVI registraties. Dit is een voorlopige definitie; VWS zal op korte termijn een definitieve standaard publiceren.",
        "caseSensitive": True,
        "concept": [org_type.model_dump() for org_type in NVI_ORGANIZATION_TYPES],
    }
    return data


@router.get(
    "/CodeSystem/care-context-type",
    status_code=200,
    summary="get CodeSystems for CareContextTypes",
    description="Retrieves the accepted CareContextTypes code values inside the NVI",
    responses={
        200: {
            "description": "A CodeSystem that contains value sets for the organization types accepted byt he NVI",
            "content": {
                "application/json": {
                    "example": {
                        "resourceType": "CodeSystem",
                        "name": "Some name",
                        "title": "Some title",
                        "status": "draft",
                        "description": "Some description",
                        "caseSensitive": True,
                        "concept": [
                            {
                                "code": "MedicationAgreement",
                                "display": "Medicatieafspraak",
                                "definition": "Een medicatieafspraak is de afspraak tussen een zorgverlener en een patiënt over het gebruik van een geneesmiddel.",
                            }
                        ],
                    }
                }
            },
        }
    },
)
def get_care_context_types() -> Dict[str, Any]:
    data = {
        "resourceType": "CodeSystem",
        "name": "NVICareContextTypes",
        "title": "CareContextTypes voor NVI",
        "status": "draft",
        "caseSensitive": True,
        "concept": [zib.model_dump() for zib in HCIM_2024_ZIBS],
    }

    return data
