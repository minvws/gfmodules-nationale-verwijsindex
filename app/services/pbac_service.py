import logging

import requests
from fastapi.exceptions import HTTPException

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

    def ura_number_is_authorized(self, ura_number: UraNumber, pseudonym: Pseudonym, data_domain: DataDomain) -> None:
        """
        Method that checks through PBAC if a URA number is authorized
        """
        if self.override_authorization_pbac:
            self.logger.info("PBAC authorization is overridden, allowing access")
            return

        input_json = {
            "input": {"uranumber": str(ura_number), "pseudonym": str(pseudonym), "datadomain": str(data_domain)}
        }

        try:
            response = requests.post(f"{self.endpoint}/v1/data/example/authz", timeout=self.timeout, json=input_json)
            response.raise_for_status()
        except requests.RequestException as e:
            self.logger.error(f"Failed to reach authorization server: {e}")
            raise HTTPException(status_code=500, detail="Failed to reach authorization server") from e

        try:
            allow = response.json()["result"]["allow"]
        except (ValueError, KeyError) as e:
            self.logger.error(f"Failed to parse response: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse response from authorization server") from e

        if not allow:
            self.logger.error(
                f"Authorization denied for URA number {ura_number}, pseudonym {pseudonym} and data domain {data_domain}"
            )
            raise HTTPException(status_code=403, detail="Authorization denied, policy not satisfied")
