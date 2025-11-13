import logging

import requests

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

    def is_authorized(self, **kwargs: bool | str) -> bool:
        request_payload = {
            "client_ura_number": kwargs.get("client_ura_number"),
            "encrypted_lmr_id": kwargs.get("encrypted_lmr_id"),
        }
        endpoint = kwargs.get("lmr_endpoint")

        if not endpoint or not isinstance(endpoint, str):
            logger.error("LMR endpoint is not provided or invalid")
            raise ValueError("LMR endpoint is required for authorization")

        for key, value in request_payload.items():
            if value is None:
                logger.error(f"Missing required authorization parameter: {key}")
                raise ValueError(f"Missing required authorization parameter: {key}")

        try:
            response = requests.request(
                method="POST",
                url=endpoint + "/authorize",
                json=request_payload,
                timeout=self._timeout,
                cert=(self._mtls_cert, self._mtls_key) if self._mtls_cert and self._mtls_key else None,
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
