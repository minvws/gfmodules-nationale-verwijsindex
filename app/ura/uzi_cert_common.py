import textwrap

from uzireader.uzi import UziException
from uzireader.uziserver import UziServer

from app.models.ura import UraNumber

_CERT_START = "-----BEGIN CERTIFICATE-----"
_CERT_END = "-----END CERTIFICATE-----"


class UraException(Exception):
    pass


def _enforce_cert_newlines(cert_data: str) -> str:
    cert_data = cert_data.split(_CERT_START)[-1].split(_CERT_END)[0].strip()
    result = _CERT_START
    result += "\n"
    result += "\n".join(textwrap.wrap(cert_data.replace(" ", ""), 64))
    result += "\n"
    result += _CERT_END

    return result


def verify_and_get_uzi_cert(cert: str) -> UraNumber:
    formatted_cert = _enforce_cert_newlines(cert)
    uzi_server = UziServer(verify="SUCCESS", cert=formatted_cert)

    return UraNumber(uzi_server["SubscriberNumber"])


def get_ura_from_cert(cert_path: str) -> str:
    try:
        with open(cert_path, "r") as cert_file:
            cert_data = cert_file.read()
            ura_number = verify_and_get_uzi_cert(cert=cert_data).value
            return ura_number
    except (IOError, UziException) as e:
        raise UraException(f"Failed to load URA Number from ceritificate: {e}")
