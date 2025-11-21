import logging

from requests.exceptions import ConnectionError, HTTPError, Timeout

from app.config import ConfigPseudonymApi
from app.services.http import HttpService
from app.services.prs.pseudonym_service import PseudonymError
from app.ura.uzi_cert_common import get_ura_from_cert

logger = logging.getLogger(__name__)


class PrsRegistrationService:
    def __init__(self, config: ConfigPseudonymApi):
        self._config = config
        self._http_service = HttpService(**config.model_dump())
        self._ura_number = get_ura_from_cert(config.mtls_cert)

    def register_nvi_at_prs(self) -> None:
        """
        Register the NVI organization and certificate at the PRS.
        """
        logger.info("Registering NVI at PRS")
        self.register_organization()
        self.register_certificate()

    def register_organization(self) -> None:
        """
        Register the NVI organization at the PRS.
        """
        try:
            response = self._http_service.do_request(
                method="POST",
                sub_route="orgs",
                data={
                    "ura": self._ura_number,
                    "name": "nationale-verwijsindex",
                    "max_key_usage": "bsn",
                },
            )

            if response.status_code == 409:
                logger.info("Organization already registered at PRS")
                return

        except (HTTPError, ConnectionError, Timeout) as e:
            logger.error(f"Failed to register certificate: {e}")
            raise PseudonymError("Failed to register orgnizaton")

    def register_certificate(self) -> None:
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

        except (HTTPError, ConnectionError, Timeout) as e:
            logger.error(f"Failed to register certificate: {e}")
            raise PseudonymError("Failed to register certificate")
