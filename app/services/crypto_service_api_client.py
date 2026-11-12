import logging
from http import HTTPStatus

from requests.exceptions import ConnectionError, HTTPError, Timeout

from app.config import ConfigCryptoServiceApi
from app.models.pseudonym import OprfPseudonym, PseudonymResponse
from app.services.exceptions import CryptoServiceError, PseudonymExchangeError
from app.services.http import HttpService

logger = logging.getLogger(__name__)


class CryptoServiceApiClient:
    def __init__(self, config: ConfigCryptoServiceApi) -> None:
        self._http = HttpService(
            endpoint=config.endpoint,
            timeout=config.timeout,
            mtls_cert=config.mtls_cert,
            mtls_key=config.mtls_key,
            verify_ca=config.verify_ca,
        )

    def exchange(self, pseudonym: OprfPseudonym, label: str, mechanism: str) -> PseudonymResponse:
        try:
            response = self._http.do_request(
                method="POST",
                sub_route="process",
                data={
                    "jwe": pseudonym.jwe,
                    "blind_factor": pseudonym.blind_factor,
                    "label": label,
                    "mechanism": mechanism,
                },
            )
            data = response.json()
            return PseudonymResponse(**data)
        except (ConnectionError, Timeout) as e:
            logger.exception("Error during request to Crypto Service API")
            raise CryptoServiceError("Failed to connect to the Crypto Service API") from e
        except HTTPError as e:
            if e.response is not None and e.response.status_code == HTTPStatus.BAD_REQUEST:
                raise PseudonymExchangeError("Invalid pseudonym or oprf_key") from e
            raise CryptoServiceError("The Crypto Service API failed to exchange the pseudonym") from e
        except (KeyError, ValueError) as e:
            logger.exception("Unexpected response from Crypto Service API")
            raise CryptoServiceError("Unexpected response from the Crypto Service API") from e

    def is_healthy(self) -> bool:
        try:
            response = self._http.do_request(method="GET", sub_route="health")
            return response.status_code == 200
        except (ConnectionError, Timeout, HTTPError):
            logger.exception("Health check failed")
            return False
