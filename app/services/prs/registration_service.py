import logging

import requests

from app.config import ConfigPseudonymApi
from app.services.prs.pseudonym_service import PseudonymError
from app.ura.uzi_cert_common import verify_and_get_uzi_cert

logger = logging.getLogger(__name__)


class PrsRegistrationService:
    def __init__(self, config: ConfigPseudonymApi):
        self._config = config

    def register_nvi_at_prs(self) -> None:
        """
        Register the NVI organization and certificate at the PRS.
        """
        logger.info("Registering NVI at PRS")
        self._register_organization()
        self._register_certificate()

    def _register_organization(self) -> None:
        """
        Register the NVI organization at the PRS.
        """
        with open(self._config.mtls_cert, "r") as cert_file:
            cert_data = cert_file.read()
            ura_number = verify_and_get_uzi_cert(cert=cert_data).value

        try:
            request = requests.post(
                url=f"{self._config.endpoint}/orgs",
                json={
                    "ura": ura_number,
                    "name": "nationale-verwijsindex",
                    "max_key_usage": "bsn",
                },
                timeout=self._config.timeout,
                cert=(self._config.mtls_cert, self._config.mtls_key),
                verify=self._config.mtls_ca,
            )
            request.raise_for_status()
        except requests.RequestException as e:
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 409:
                logger.info("Organization already registered at PRS")
                return
            logger.error(f"Failed to register organization: {e}")
            raise PseudonymError("Failed to register organization")

    def _register_certificate(self) -> None:
        """
        Register the NVI certificate at the PRS.
        """
        try:
            request = requests.post(
                url=f"{self._config.endpoint}/register/certificate",
                json={
                    "scope": ["nationale-verwijsindex"],
                },
                timeout=self._config.timeout,
                cert=(self._config.mtls_cert, self._config.mtls_key),
                verify=self._config.mtls_ca,
            )
            request.raise_for_status()
        except requests.RequestException as e:
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 409:
                logger.info("Certificate already registered at PRS")
                return
            logger.error(f"Failed to register certificate: {e}")
            raise PseudonymError("Failed to register certificate")
