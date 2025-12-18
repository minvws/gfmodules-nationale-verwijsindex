import logging

from uzireader.uzi import UziException
from uzireader.uziserver import UziServer

from app.data import X509_FILE_EXTENSIONS
from app.models.dezi import DeziSigningCert
from app.models.ura import UraNumber
from app.utils.certificates.exceptions import DeziCertError
from app.utils.certificates.utils import (
    create_certificate,
    enforce_cert_newlines,
    load_many_certificate_files,
    load_one_certificate_file,
)

logger = logging.getLogger(__name__)


def load_dezi_signing_certificates(cert_store_path: str) -> list[DeziSigningCert]:
    """
    Load the DEZI signing certificates from the given directory path and return them as a list of DeziSigningCert objects.
    The certificates are expected to be in PEM format.
    """
    if not cert_store_path:
        raise ValueError("DEZI signing certificate path is required")

    files = load_many_certificate_files(cert_store_path, X509_FILE_EXTENSIONS)

    certificates = []
    for file in files:
        certificate = create_certificate(file)
        dezi_signing_cert = DeziSigningCert.from_x509_certificate(certificate)
        certificates.append(dezi_signing_cert)

    return certificates


def verify_and_get_uzi_cert(cert: str) -> UraNumber:
    formatted_cert = enforce_cert_newlines(cert)
    uzi_server = UziServer(verify="SUCCESS", cert=formatted_cert)
    return UraNumber(uzi_server["SubscriberNumber"])


def get_ura_from_cert(cert_path: str) -> UraNumber:
    try:
        cert_data = load_one_certificate_file(cert_path)
        ura_number = verify_and_get_uzi_cert(cert_data)
        return ura_number
    except (IOError, UziException, ValueError) as e:
        raise DeziCertError(f"Failed to load URA Number from ceritificate: {e}")
