import textwrap

from uzireader.uziserver import UziServer

from app.data import UraNumber

_CERT_START = "-----BEGIN CERTIFICATE-----"
_CERT_END = "-----END CERTIFICATE-----"


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
