import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_organization_service, get_pseudonym_service
from app.models.fhir.bundle import Bundle
from app.models.fhir.resources.organization.parameters import Parameters
from app.services.organization import OrganizationService
from app.services.prs.pseudonym_service import PseudonymService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Organization"], prefix="/Organization")


@router.post("/$localize")
def localise(
    parameters: Parameters,
    pseudonym_service: PseudonymService = Depends(get_pseudonym_service),
    organization_service: OrganizationService = Depends(get_organization_service),
) -> Any:
    localization_dto = parameters.get_org_lokalization_dto()
    try:
        localisation_pseudonym = pseudonym_service.exchange(
            oprf_jwe=localization_dto.oprf_jwe, blind_factor=localization_dto.oprf_key
        )
    except Exception as e:
        logger.error(f"Failed to exchange pseudonym: {e}")
        raise HTTPException(status_code=404)

    organizations = organization_service.get(
        pseudonym=str(localisation_pseudonym),
        data_domain=localization_dto.data_domain,
        org_types=localization_dto.org_types,
    )

    return Bundle.from_organizations(organizations)
