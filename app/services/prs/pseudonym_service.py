import base64
import logging

import pyoprf

from app.data import Pseudonym
from app.services.decrypt_service import DecryptService

logger = logging.getLogger(__name__)


class PseudonymError(Exception):
    """Exception raised when pseudonym operations fail."""

    pass


class PseudonymService:
    def __init__(
        self,
        decrypt_service: DecryptService,
    ):
        self._decrypt_service = decrypt_service

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
