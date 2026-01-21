import logging

from fastapi import APIRouter, Depends

from app.dependencies import get_organization_service, get_pseudonym_service
from app.exceptions.fhir_exception import FHIRException
from app.models.fhir.bundle import Bundle
from app.models.fhir.resources.organization.parameters import Parameters
from app.models.fhir.resources.organization.resource import Organization
from app.services.organization import OrganizationService
from app.services.prs.pseudonym_service import PseudonymService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Organization"], prefix="/Organization")


@router.post("/$localize", response_model_exclude_none=True)
def localise(
    parameters: Parameters,
    pseudonym_service: PseudonymService = Depends(get_pseudonym_service),
    organization_service: OrganizationService = Depends(get_organization_service),
) -> Bundle[Organization]:
    localization_dto = parameters.get_org_lokalization_dto()
    try:
        localisation_pseudonym = pseudonym_service.exchange(
            oprf_jwe=localization_dto.oprf_jwe, blind_factor=localization_dto.oprf_key
        )
    except Exception as e:
        logger.error(f"Failed to decrypt OPRF JWE: {e}")
        raise FHIRException(
            status_code=403,
            severity="error",
            code="invalid",
            msg="Subject invalid.",
        )

    organizations = organization_service.get(
        pseudonym=str(localisation_pseudonym),
        data_domain=localization_dto.data_domain,
        org_types=localization_dto.org_types,
    )

    return Bundle.from_organizations(organizations)
