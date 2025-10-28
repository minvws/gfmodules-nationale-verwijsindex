import base64
import json
import logging
from typing import Any

import jwt
import pyoprf
import requests
from fastapi import HTTPException
from jwcrypto import jwe

from app.data import Pseudonym
from app.ura.uzi_cert_common import verify_and_get_uzi_cert

logger = logging.getLogger(__name__)


class PseudonymService:
    def __init__(
        self,
        endpoint: str,
        timeout: int,
        provider_id: str,
        mtls_cert: str,
        mtls_key: str,
        mtls_ca: str,
        jwkey: jwt.PyJWK,
        public_key: jwt.PyJWK,
    ):
        self._endpoint = endpoint
        self._timeout = timeout
        self._mtls_cert = mtls_cert
        self._mtls_key = mtls_key
        self._mtls_ca = mtls_ca
        self._jwkey = jwkey
        self._provider_id = provider_id
        self._public_key = public_key
        self._ura_number: str | None = None

        # Pre-register NVI organization and certificate at PRS on service initialization
        self.register_nvi_at_prs()

    def exchange(self, oprf_jwe: str, blind_factor: str) -> Pseudonym:
        """
        Exchanges the pseudonym using OPRF protocol with the PRS.
        """
        logger.info("Decrypting OPRF JWE")

        # Decrypt OPRF-JWE<NVI> with private key pre-registered at PRS
        jwe_data = self._decrypt_jwe(oprf_jwe, self._jwkey)

        if jwe_data["subject"].startswith("pseudonym:eval:") is False:
            raise HTTPException(detail={"error": "invalid subject"}, status_code=400)
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
        if not self._ura_number:
            self._ura_number = verify_and_get_uzi_cert(cert=cert_data).value

        try:
            request = requests.post(
                url=f"{self._endpoint}/orgs",
                json={
                    "ura": self._ura_number,
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
            raise HTTPException(detail={"error": "Failed to register organization"}, status_code=500)

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
            logger.error(f"Failed to register organization: {e}")
            raise HTTPException(detail={"error": "Failed to register organization"}, status_code=500)

    def _decrypt_jwe(self, data: str, private_key: jwt.PyJWK) -> Any:
        """
        Decrypts a JWE using the provided private key.
        """
        try:
            token = jwe.JWE()
            token.deserialize(data)

            header = token.jose_header
            if header.get("alg") != "RSA-OAEP-256":
                raise ValueError("Invalid JWE algorithm")
            if header.get("enc") != "A256GCM":
                raise ValueError("Invalid JWE encryption")

            token.decrypt(private_key)
            plaintext = token.payload.decode("utf-8")
            return json.loads(plaintext)
        except Exception as e:
            raise HTTPException(detail=f"Failed to decrypt JWE: {e}", status_code=400) from e
