import logging

from app.data import Pseudonym, UraNumber
from app.services.api_service import HttpService
from app.services.authorization_services.authorization_interface import BaseAuthService

logger = logging.getLogger(__name__)


class LmrService(BaseAuthService):
    def __init__(
        self,
        api_service: HttpService,
    ):
        self.api_service = api_service

    def is_authorized(
        self,
        endpoint: str,
        pseudonym: Pseudonym,
        requesting_ura_number: UraNumber,
        encrypted_lmr_id: str,
    ) -> bool:
        request_payload = {
            "pseudonym": str(pseudonym),
            "requesting_ura_number": str(requesting_ura_number),
            "encrypted_lmr_id": encrypted_lmr_id,
        }

        try:
            self.api_service.base_url = endpoint
            response = self.api_service.do_request(method="POST", json=request_payload, sub_route="authorize")
            response.raise_for_status()
            return bool(response.json().get("authorized", False))
        except Exception as e:
            logger.error(f"LMR authorization request failed: {str(e)}")
            return False
