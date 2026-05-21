import logging
from json import JSONDecodeError

from requests.exceptions import ConnectionError, HTTPError, Timeout

from app.config import ConfigCryptoServiceApi
from app.models.pseudonym import Pseudonym
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

    def exchange(self, jwe: str, blind_factor: str) -> Pseudonym:
        try:
            response = self._http.do_request(
                method="POST",
                sub_route="decrypt_and_hash",
                params={"jwe": jwe, "blind_factor": blind_factor},
            )
            return Pseudonym(value=response.json()["hashed_pseudonym"])
        except (ConnectionError, Timeout):
            logger.exception("Error during request to Crypto Service API")
            raise ConnectionError("Failed to connect to the Crypto Service API")
        except HTTPError:
            raise ValueError("Invalid pseudonym or oprf_key")
        except (JSONDecodeError, KeyError):
            logger.exception("Unexpected response from Crypto Service API")
            raise RuntimeError("Unexpected response from the Crypto Service API")

    def is_healthy(self) -> bool:
        try:
            response = self._http.do_request(method="GET", sub_route="health")
            return response.status_code == 200
        except (ConnectionError, Timeout, HTTPError):
            logger.exception("Health check failed")
            return False
