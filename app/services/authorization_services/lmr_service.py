import logging

from requests import request

from app.models.ura import UraNumber
from app.services.authorization_services.authorization_interface import BaseAuthService

logger = logging.getLogger(__name__)


class LmrService(BaseAuthService):
    def __init__(
        self,
        mtls_cert: str | None = None,
        mtls_key: str | None = None,
        mtls_ca: str | None = None,
    ):
        self._mtls_cert = mtls_cert
        self._mtls_key = mtls_key
        self._mtls_ca = mtls_ca
        self._timeout = 10

    def is_authorized(
        self,
        client_ura_number: UraNumber,
        encrypted_lmr_id: str,
        lmr_endpoint: str,
    ) -> bool:
        try:
            response = request(
                method="POST",
                url=lmr_endpoint + "/authorize",
                json={
                    "client_ura_number": str(client_ura_number),
                    "encrypted_lmr_id": encrypted_lmr_id,
                },
                timeout=self._timeout,
                cert=((self._mtls_cert, self._mtls_key) if self._mtls_cert and self._mtls_key else None),
                verify=self._mtls_ca if self._mtls_ca else True,
            )
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, bool):
                logger.error("Invalid response format from LMR service")
                raise ValueError("Invalid response format from LMR service")
            return result
        except Exception as e:
            logger.error(f"LMR authorization request failed: {str(e)}")
            return False
