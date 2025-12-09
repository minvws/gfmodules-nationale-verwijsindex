import base64
import logging
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed448, ed25519, rsa
from uzireader.uzi import UziException
from uzireader.uziserver import UziServer

from app.jwt_validator import DeziSigningCert
from app.models.ura import UraNumber
from app.utils.certificates.utils import enforce_cert_newlines, load_certificate

logger = logging.getLogger(__name__)


class DeziCertExceptin(Exception):
    pass


def load_dezi_signing_certificates(cert_store_path: str) -> list[DeziSigningCert]:
    """
    Load the DEZI signing certificates from the given directory path and return them as a list of DeziSigningCert objects.
    The certificates are expected to be in PEM format.
    """
    if not cert_store_path:
        raise ValueError("DEZI signing certificate path is required")

    dir_path = Path(cert_store_path)
    if not dir_path.exists():
        raise FileNotFoundError(f"DEZI signing certificates not found at: {dir_path}")

    certificates = []
    for cert_file in dir_path.iterdir():
        certificate: x509.Certificate
        try:
            certificate = load_certificate(str(cert_file))
        except ValueError as e:
            logger.warning(e)
            continue

        # Generate x5t (X.509 certificate SHA-1 thumbprint)
        sha1_fingerprint = certificate.fingerprint(hashes.SHA1())  # NOSONAR
        x5t = base64.urlsafe_b64encode(sha1_fingerprint).decode("utf-8")
        x5t = x5t.rstrip("=")  # Remove padding for x5t

        public_key = certificate.public_key()
        print(public_key)
        if not isinstance(
            public_key,
            (
                rsa.RSAPublicKey,
                ec.EllipticCurvePublicKey,
                ed25519.Ed25519PublicKey,
                ed448.Ed448PublicKey,
            ),
        ):
            raise TypeError(f"Unsupported public key type in DEZI certificate: {type(public_key)}")

        certificates.append(
            DeziSigningCert(
                certificate=certificate,
                public_key=public_key,
                x5t=x5t,
            )
        )
    return certificates


def verify_and_get_uzi_cert(cert: str) -> UraNumber:
    formatted_cert = enforce_cert_newlines(cert)
    uzi_server = UziServer(verify="SUCCESS", cert=formatted_cert)
    return UraNumber(uzi_server["SubscriberNumber"])


def get_ura_from_cert(cert_path: str) -> UraNumber:
    try:
        with open(cert_path, "r") as cert_file:
            cert_data = cert_file.read()
            ura_number = verify_and_get_uzi_cert(cert=cert_data)
            return ura_number
    except (IOError, UziException) as e:
        raise DeziCertExceptin(f"Failed to load URA Number from ceritificate: {e}")
