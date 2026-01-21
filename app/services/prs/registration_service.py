import logging

from requests.exceptions import ConnectionError, HTTPError, Timeout

from app.config import ConfigPseudonymApi
from app.models.ura import UraNumber
from app.services.client_oauth import ClientOAuthService
from app.services.http import HttpService
from app.services.prs.exception import PseudonymError

logger = logging.getLogger(__name__)


class PrsRegistrationService:
    def __init__(
        self, ura_number: UraNumber, config: ConfigPseudonymApi, client_oauth_service: ClientOAuthService
    ) -> None:
        self._oauth_service = client_oauth_service
        self._config = config
        self._http_service = HttpService(
            endpoint=self._config.endpoint,
            timeout=self._config.timeout,
            mtls_cert=self._config.mtls_cert,
            mtls_key=self._config.mtls_key,
            verify_ca=self._config.verify_ca,
        )
        self._ura_number = ura_number
        self._access_token: str | None = None

    def register_nvi_at_prs(self) -> None:
        """
        Register the NVI organization and certificate at the PRS.
        """
        logger.info("Registering NVI at PRS")
        self._register_organization()
        self._register_certificate()

    def _register_organization(self) -> None:
        """
        Register the NVI organization at the PRS.
        """
        try:
            headers = {}
            if self._oauth_service.enabled():
                headers["Authorization"] = "Bearer " + self.fetch_oauth_token()

            response = self._http_service.do_request(
                method="POST",
                sub_route="orgs",
                headers=headers,
                data={
                    "ura": self._ura_number.value,
                    "name": "nationale-verwijsindex",
                    "max_key_usage": "bsn",
                },
            )
            logger.debug("Response status code: %d", response.status_code)

            # No authentication, we can retry by clearing the token. This will fetch a new access token on the next attempt
            if response.status_code == 401:
                self._access_token = None

            if response.status_code == 409:
                logger.info("Organization already registered at PRS")
                return

            response.raise_for_status()

        except (HTTPError, ConnectionError, Timeout) as e:
            logger.error(f"Failed to register organization: {e}")
            raise PseudonymError("Failed to register organization")

    def _register_certificate(self) -> None:
        """
        Register the NVI certificate at the PRS.
        """
        try:
            headers = {}
            if self._oauth_service.enabled():
                headers["Authorization"] = "Bearer " + self.fetch_oauth_token()

            response = self._http_service.do_request(
                method="POST",
                headers=headers,
                sub_route="register/certificate",
                data={"scope": ["nationale-verwijsindex"]},
            )

            # No authentication, we can retry by clearing the token. This will fetch a new access token on the next attempt
            if response.status_code == 401:
                self._access_token = None

            if response.status_code == 409:
                logging.info("Certificate already registered at PRS")
                return

            response.raise_for_status()

        except (HTTPError, ConnectionError, Timeout) as e:
            logger.error(f"Failed to register certificate: {e}")
            raise PseudonymError("Failed to register certificate")

    def fetch_oauth_token(self) -> str:
        if not self._oauth_service.enabled():
            return ""

        if self._access_token is None:
            self._access_token = self._oauth_service.get_access_token("prs:read", self._config.endpoint)

        return self._access_token
