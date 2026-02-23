import json
import logging
from typing import Any

from jwcrypto import jwe, jwk

logger = logging.getLogger(__name__)


class DecryptError(Exception):
    """Exception raised when decryption operations fail."""

    pass


class DecryptService:
    def __init__(self, mtls_key: str) -> None:
        self._private_key = self._read_private_key_file(mtls_key)

    def decrypt_jwe(self, oprf_jwe: str) -> Any:
        """
        Decrypts a JWE using a private key from the mTLS configuration.
        """
        try:
            token = jwe.JWE()
            token.deserialize(oprf_jwe)

            header = token.jose_header
            if header.get("alg") != "RSA-OAEP-256":
                logger.error("Invalid JWE algorithm: expected alg RSA-OAEP-256")
                raise DecryptError("Invalid JWE algorithm: expected alg RSA-OAEP-256")
            if header.get("enc") != "A256GCM":
                logger.error("Invalid JWE encryption: expected enc A256GCM")
                raise DecryptError("Invalid JWE encryption: expected enc A256GCM")

            token.decrypt(self._private_key)
            plaintext = token.payload.decode("utf-8")
            return json.loads(plaintext)
        except Exception as e:
            logger.error(f"Failed to decrypt JWE: {e}")
            raise DecryptError("Failed to decrypt JWE") from e

    def _read_private_key_file(self, mtls_key: str) -> jwk.JWK:
        try:
            with open(mtls_key, "rb") as key_file:
                private_key_pem = key_file.read()
            return jwk.JWK.from_pem(private_key_pem)
        except Exception as e:
            logger.error(f"Failed to read private key file: {e}")
            raise ValueError("Failed to read private key file") from e
