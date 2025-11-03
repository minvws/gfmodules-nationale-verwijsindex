import logging
import time
from typing import Any, Dict

from requests import Response, Timeout, request
from yarl import URL

logger = logging.getLogger(__name__)


class HttpService:
    """
    Class for making HTTP requests with retry logic
    """

    def __init__(
        self,
        base_url: str,
        timeout: int,
        retries: int,
        backoff: float,
        mtls_cert: str | None = None,
        mtls_key: str | None = None,
        mtls_ca: str | None = None,
    ) -> None:
        self.base_url = base_url
        self._mtls_cert = mtls_cert
        self._mtls_key = mtls_key
        self._mtls_ca = mtls_ca
        self._timeout = timeout
        self._retries = retries
        self._backoff = backoff

    def do_request(
        self,
        method: str,
        headers: Dict[str, str] | None = None,
        sub_route: str | None = None,
        json: Dict[str, Any] | None = None,
        params: Dict[str, Any] | None = None,
    ) -> Response:
        """
        Perform an HTTP request.
        """
        url = self.make_target_url(sub_route, params)

        for attempt in range(self._retries):
            try:
                logger.info(f"Making HTTP {method} request to {url}")
                response = request(
                    method=method,
                    url=str(url),
                    headers=headers,
                    timeout=self._timeout,
                    json=json,
                    cert=(self._mtls_cert, self._mtls_key) if self._mtls_cert and self._mtls_key else None,
                    verify=self._mtls_ca or True,
                )
                return response
            except (
                ConnectionError,
                Timeout,
            ):
                logger.warning(f"Failed to make request to {url} on attempt {attempt}")

                # Connection error or timeout, we can retry with an exponential backoff until
                # we reach the max retries
                if attempt < self._retries - 1:
                    logger.info(f"Retrying in {self._backoff * (2**attempt)} seconds")
                    time.sleep(self._backoff * (2**attempt))

        logger.error(f"Failed to make request to {url} after {self._retries} attempts")
        raise ConnectionError("Failed to make request after too many retries")

    def make_target_url(self, sub_route: str | None = None, params: Dict[str, Any] | None = None) -> URL:
        url = self.base_url
        if sub_route:
            url = f"{url}/{sub_route}"

        target = URL(url)
        if params:
            return target.with_query(params)

        return target
