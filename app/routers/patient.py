import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_pseudonym_service, get_referral_service
from app.exceptions.fhir_exception import FHIRException
from app.models.fhir.bundle import Bundle
from app.models.fhir.resources.localization_list.resource import LocalizationList
from app.services.decrypt_service import DecryptService
from app.services.prs.pseudonym_service import PseudonymService
from app.services.referral_service import ReferralService
from app.utils.certificates.utils import enforce_cert_newlines

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Patient"], prefix="/Patient")


@router.post("")
def register(
    request: Request,
    data: Bundle[LocalizationList],
    referral_service: ReferralService = Depends(get_referral_service),
    pseudonym_service: PseudonymService = Depends(get_pseudonym_service),
) -> Any:
    # TODO: Validation here
    method = data.entry[0].request.method
    resource = data.entry[0].resource
    client_cert = enforce_cert_newlines(request.headers.get("x-forwarded-tls-client-cert"))
    pseudonym_token = DecryptService.deserialize_jwt(data.entry[0].resource.get_pseudonym_jwt(), client_cert)
    pseudonym_data = json.loads(pseudonym_token)
    try:
        pseudonym = pseudonym_service.exchange(
            oprf_jwe=pseudonym_data["pseudonym"], blind_factor=pseudonym_data["oprfKey"]
        )
    except Exception as e:
        logger.error(f"failed to exchange pseudonym {e}")
        raise FHIRException(
            status_code=500,
            severity="error",
            code="not-found",
            msg="Pseudonym could not be exchanged",
            expression=["NVIDataReference.subject"],
        )

    match method:
        case "POST":
            referral_service.add_one(
                pseudonym=pseudonym,
                data_domain=resource.get_data_domain(),
                ura_number=resource.get_ura(),
            )
        case "DELETE":
            referral_service.delete_one(
                pseudonym=pseudonym,
                data_domain=resource.get_data_domain(),
                ura_number=resource.get_ura(),
            )
    return {"message": "Ok!!"}
