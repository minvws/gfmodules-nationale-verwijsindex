import base64
import logging

import pyoprf
import requests

from app.models.pseudonym import Pseudonym
from app.services.decrypt_service import DecryptService
from app.ura.uzi_cert_common import verify_and_get_uzi_cert

logger = logging.getLogger(__name__)


class PseudonymError(Exception):
    """Exception raised when pseudonym operations fail."""

    pass


class PseudonymService:
    def __init__(
        self,
        endpoint: str,
        timeout: int,
        provider_id: str,
        mtls_cert: str,
        mtls_key: str,
        mtls_ca: str,
        decrypt_service: DecryptService,
    ):
        self._endpoint = endpoint
        self._timeout = timeout
        self._mtls_cert = mtls_cert
        self._mtls_key = mtls_key
        self._mtls_ca = mtls_ca
        self._provider_id = provider_id
        self._decrypt_service = decrypt_service

        # Pre-register NVI organization and certificate at PRS on service initialization
        self.register_nvi_at_prs()

    def exchange(self, oprf_jwe: str, blind_factor: str) -> Pseudonym:
        """
        Exchanges the pseudonym using OPRF protocol with the PRS.
        """
        logger.info("Decrypting OPRF JWE")

        # Decrypt OPRF-JWE<NVI> with private key pre-registered at PRS
        jwe_data = self._decrypt_service.decrypt_jwe(oprf_jwe)

        if jwe_data["subject"].startswith("pseudonym:eval:") is False:
            logger.error("JWE is invalid: subject does not start with pseudonym:eval:")
            raise PseudonymError("JWE is invalid: subject does not start with pseudonym:eval:")
        subj = jwe_data["subject"].split(":")[-1]

        subj = base64.urlsafe_b64decode(subj)
        bf = base64.urlsafe_b64decode(blind_factor)

        pseudonym = base64.urlsafe_b64encode(pyoprf.unblind(bf, subj)).decode()

        logger.info(f"Pseudonym exchange completed: {pseudonym}")

        return Pseudonym(value=pseudonym)

    def register_nvi_at_prs(self) -> None:
        """
        Register the NVI organization and certificate at the PRS.
        """
        logger.info("Registering NVI at PRS")
        with open(self._mtls_cert, "r") as cert_file:
            cert_data = cert_file.read()
        self._register_organization(cert_data)
        self._register_certificate()

    def _register_organization(self, cert_data: str) -> None:
        """
        Register the NVI organization at the PRS.
        """
        ura_number = verify_and_get_uzi_cert(cert=cert_data).value

        try:
            request = requests.post(
                url=f"{self._endpoint}/orgs",
                json={
                    "ura": ura_number,
                    "name": "nvi",
                    "max_key_usage": "bsn",
                },
                timeout=self._timeout,
                cert=(self._mtls_cert, self._mtls_key),
                verify=self._mtls_ca,
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
                url=f"{self._endpoint}/register/certificate",
                json={
                    "scope": ["nvi"],
                },
                timeout=self._timeout,
                cert=(self._mtls_cert, self._mtls_key),
                verify=self._mtls_ca,
            )
            request.raise_for_status()
        except requests.RequestException as e:
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 409:
                logger.info("Organization already registered at PRS")
                return
            logger.error(f"Failed to register certificate: {e}")
            raise PseudonymError("Failed to register certificate")
