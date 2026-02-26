import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_organization_service, get_pseudonym_service
from app.exceptions.fhir_exception import FHIRException
from app.models.fhir.bundle import Bundle
from app.models.fhir.resources.data import CARE_CONTEXT_SYSTEM, SOURCE_SYSTEM
from app.models.fhir.resources.operation_outcome.resource import OperationOutcome
from app.models.fhir.resources.organization.parameters import Parameters
from app.models.fhir.resources.organization.resource import Organization
from app.models.response import FHIRJSONResponse
from app.services.organization import OrganizationService
from app.services.prs.pseudonym_service import PseudonymService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Organization"], prefix="/Organization")


@router.post(
    "/$localize",
    status_code=200,
    response_model_exclude_none=True,
    response_class=FHIRJSONResponse,
    summary="Localize Organizations",
    description="Localize Organizations that registered referrals for a pseudonym.",
    responses={
        200: {
            "description": "Successful retrieval of localized Organizations",
            "model": Bundle[Organization],
            "content": {
                "application/fhir+json": {
                    "example": {
                        "resourceType": "Bundle",
                        "type": "searchset",
                        "timestamp": "2024-12-08T14:35:22Z",
                        "total": 2,
                        "entry": [
                            {
                                "resource": {
                                    "resourceType": "Organization",
                                    "id": "90000001",
                                    "identifier": [{"system": SOURCE_SYSTEM, "value": "90000001"}],
                                }
                            }
                        ],
                    }
                }
            },
        },
        400: {"model": OperationOutcome},
        403: {"model": OperationOutcome},
        404: {"model": OperationOutcome},
        422: {"model": OperationOutcome},
        500: {"model": OperationOutcome},
    },
)
def localize(
    parameters: Annotated[
        Parameters,
        Body(
            examples=[
                {
                    "resourceType": "Parameters",
                    "parameter": [
                        {
                            "name": "pseudonym",
                            "valueString": "eyJhbGciOiJSU0EtT0FFUC0yNTYiLCJlbmMiOiJBMjU2R0NNIn0.dGhpcyBpcyBhIGV4YW1wbGUgSldFIGVuY3J5cHRlZCBwc2V1ZG9ueW0...",
                        },
                        {
                            "name": "oprfKey",
                            "valueString": "base64-encoded-oprf-key-from-bsnk",
                        },
                        {
                            "name": "careContext",
                            "valueCoding": {
                                "system": CARE_CONTEXT_SYSTEM,
                                "code": "MedicationAgreement",
                                "display": "Medicatieafspraak",
                            },
                        },
                        {"name": "filterOrgType", "valueCode": "apotheek"},
                    ],
                }
            ]
        ),
    ],
    pseudonym_service: PseudonymService = Depends(get_pseudonym_service),
    organization_service: OrganizationService = Depends(get_organization_service),
) -> Bundle[Organization]:
    localization_dto = parameters.get_org_lokalization_dto()
    try:
        localisation_pseudonym = pseudonym_service.exchange(
            oprf_jwe=localization_dto.oprf_jwe, blind_factor=localization_dto.oprf_key
        )
    except Exception as e:
        logger.error(f"Failed to exchange pseudonym: {e}")
        raise FHIRException(
            status_code=500,
            severity="error",
            code="not-found",
            msg="Pseudonym could not be exchanged",
            expression=["Parameters.parameter.pseudonym"],
        )

    organizations = organization_service.get(
        pseudonym=str(localisation_pseudonym),
        data_domain=localization_dto.data_domain,
        org_types=localization_dto.org_types,
    )

    return Bundle.from_organizations(organizations)
