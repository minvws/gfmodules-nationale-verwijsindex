import base64
import logging

import pyoprf
import requests

from app.data import Pseudonym
from app.services.api_service import HttpService
from app.services.decrypt_service import DecryptService
from app.ura.uzi_cert_common import verify_and_get_uzi_cert

logger = logging.getLogger(__name__)


class PseudonymError(Exception):
    """Exception raised when pseudonym operations fail."""

    pass


class PseudonymService:
    def __init__(
        self,
        mtls_cert: str,
        decrypt_service: DecryptService,
        api_service: HttpService,
    ):
        self._api_service = api_service
        self._mtls_cert = mtls_cert
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
            response = self._api_service.do_request(
                method="POST",
                json={
                    "ura": ura_number,
                    "name": "nvi",
                    "max_key_usage": "bsn",
                },
                sub_route="orgs",
            )
            response.raise_for_status()
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
            response = self._api_service.do_request(
                method="POST",
                json={
                    "scope": ["nvi"],
                },
                sub_route="register/certificate",
            )
            response.raise_for_status()
        except requests.RequestException as e:
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 409:
                logger.info("Organization already registered at PRS")
                return
            logger.error(f"Failed to register certificate: {e}")
            raise PseudonymError("Failed to register certificate")
