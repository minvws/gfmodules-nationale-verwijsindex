import logging

import requests

from app.data import DataDomain, Pseudonym, UraNumber


class PbacService:
    logger = logging.getLogger(__name__)

    def __init__(
        self,
        endpoint: str,
        timeout: int,
        override_authorization_pbac: bool,
    ):
        self.endpoint = endpoint
        self.timeout = timeout
        self.override_authorization_pbac = override_authorization_pbac

    def ura_number_is_authorized(self, ura_number: UraNumber, pseudonym: Pseudonym, data_domain: DataDomain) -> bool:
        """
        Method that checks through PBAC if a URA number is authorized
        """
        if self.override_authorization_pbac:
            self.logger.info("PBAC authorization is overridden, allowing access")
            return True

        input_json = {
            "input": {"uranumber": str(ura_number), "pseudonym": str(pseudonym), "datadomain": str(data_domain)}
        }
        print(input_json)

        response = requests.post(f"{self.endpoint}/v1/data/example/authz", timeout=self.timeout, json=input_json)

        response.raise_for_status()

        return response.json()["result"]["allow"]  # type: ignore
