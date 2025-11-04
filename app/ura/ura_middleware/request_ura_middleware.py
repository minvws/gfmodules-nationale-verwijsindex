from fastapi import HTTPException
from starlette.requests import Request

from app.data_models.typing import UraNumber
from app.ura.ura_middleware.ura_middleware import UraMiddleware
from app.ura.uzi_cert_common import verify_and_get_uzi_cert


class RequestUraMiddleware(UraMiddleware):
    _SSL_CLIENT_CERT_HEADER_NAME = "x-proxy-ssl_client_cert"

    def authenticated_ura(self, request: Request) -> UraNumber:
        if self._SSL_CLIENT_CERT_HEADER_NAME not in request.headers:
            raise HTTPException(
                status_code=401,
                detail="Missing client certificate",
            )
        cert = request.headers[self._SSL_CLIENT_CERT_HEADER_NAME]

        return verify_and_get_uzi_cert(cert)
