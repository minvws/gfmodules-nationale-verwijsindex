import logging
from typing import Any, Literal

from requests import HTTPError, Response, request
from requests.exceptions import ConnectionError, Timeout

logger = logging.getLogger(__name__)


class HttpService:
    def __init__(
        self,
        endpoint: str,
        timeout: int,
        mtls_cert: str | None,
        mtls_key: str | None,
        mtls_ca: str | None,
    ):
        self._endpoint = endpoint
        self._timeout = timeout
        self._mtls_cert = mtls_cert
        self._mtls_key = mtls_key
        self._mtls_ca = mtls_ca

    def do_request(
        self,
        method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
        sub_route: str = "",
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> Response:
        try:
            cert = (self._mtls_cert, self._mtls_key) if self._mtls_cert and self._mtls_key else None
            verify = self._mtls_ca if self._mtls_ca else True
            response = request(
                method=method,
                url=f"{self._endpoint}/{sub_route}" if sub_route else self._endpoint,
                params=params,
                headers=headers,
                json=data,
                timeout=self._timeout,
                cert=cert,
                verify=verify,
            )

            return response
        except (ConnectionError, Timeout) as e:
            logger.error(f"Request failed: {e}")
            raise e
        except HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise e
