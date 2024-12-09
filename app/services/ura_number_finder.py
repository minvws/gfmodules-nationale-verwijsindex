import abc
import textwrap

from fastapi import HTTPException
from starlette.requests import Request
from uzireader.uziserver import UziServer

from app.data import UraNumber


class StarletteRequestURANumberFinder(abc.ABC):
    @abc.abstractmethod
    def find(self, request: Request) -> UraNumber: ...


class ConfigOverridenMockURANumberFinder(StarletteRequestURANumberFinder):
    _config_value: str

    def __init__(self, config_value: str) -> None:
        self._config_value = config_value

    def find(self, request: Request) -> UraNumber:
        return UraNumber(self._config_value)


class RequestURANumberFinder(StarletteRequestURANumberFinder):
    _CERT_START = "-----BEGIN CERTIFICATE-----"
    _CERT_END = "-----END CERTIFICATE-----"

    _SSL_CLIENT_CERT_HEADER_NAME = "x-proxy-ssl_client_cert"
    _cert: str

    def _enforce_cert_newlines(self, cert_data: str) -> str:
        cert_data = (
            cert_data.split(self._CERT_START)[-1].split(self._CERT_END)[0].strip()
        )
        result = self._CERT_START
        result += "\n"
        result += "\n".join(textwrap.wrap(cert_data.replace(" ", ""), 64))
        result += "\n"
        result += self._CERT_END

        return result

    def find(self, request: Request) -> UraNumber:
        if self._SSL_CLIENT_CERT_HEADER_NAME not in request.headers:
            raise HTTPException(
                status_code=401,
                detail="Missing client certificate",
            )
        cert = request.headers[self._SSL_CLIENT_CERT_HEADER_NAME]

        formatted_cert = self._enforce_cert_newlines(cert)
        uzi_server = UziServer(verify="SUCCESS", cert=formatted_cert)

        return UraNumber(uzi_server["SubscriberNumber"])
