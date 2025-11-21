import logging

from requests.exceptions import ConnectionError, HTTPError, Timeout

from app.config import ConfigPseudonymApi
from app.models.ura import UraNumber
from app.services.http import HttpService
from app.services.prs.exception import PseudonymError

logger = logging.getLogger(__name__)


class PrsRegistrationService:
    def __init__(self, ura_number: UraNumber, config: ConfigPseudonymApi):
        self._http_service = HttpService(**config.model_dump())
        self._ura_number = ura_number

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
            response = self._http_service.do_request(
                method="POST",
                sub_route="orgs",
                data={
                    "ura": self._ura_number.value,
                    "name": "nationale-verwijsindex",
                    "max_key_usage": "bsn",
                },
            )

            if response.status_code == 409:
                logger.info("Organization already registered at PRS")
                return

            response.raise_for_status()

        except (HTTPError, ConnectionError, Timeout) as e:
            logger.error(f"Failed to register orgnizaton: {e}")
            raise PseudonymError("Failed to register orgnizaton")

    def _register_certificate(self) -> None:
        """
        Register the NVI certificate at the PRS.
        """
        try:
            response = self._http_service.do_request(
                method="POST",
                sub_route="/register/certificate",
                data={"scope": ["nationale-verwijsindex"]},
            )

            if response.status_code == 409:
                logging.info("Certificate already registered at PRS")
                return

            response.raise_for_status()

        except (HTTPError, ConnectionError, Timeout) as e:
            logger.error(f"Failed to register certificate: {e}")
            raise PseudonymError("Failed to register certificate")
