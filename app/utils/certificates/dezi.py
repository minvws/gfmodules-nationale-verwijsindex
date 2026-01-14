import logging

from uzireader.uzi import UziException
from uzireader.uziserver import UziServer

from app.models.ura import UraNumber
from app.utils.certificates.exceptions import DeziCertError
from app.utils.certificates.utils import (
    enforce_cert_newlines,
    load_one_certificate_file,
)

logger = logging.getLogger(__name__)


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
