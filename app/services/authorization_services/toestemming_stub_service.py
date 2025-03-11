import logging
from typing import Any, Dict

import requests
from fastapi import HTTPException

from app.services.authorization_services.authorization_interface import BaseAuthService

logger = logging.getLogger(__name__)


class ToestemmingStubService(BaseAuthService):
    def __init__(
        self,
        endpoint: str,
        timeout: int,
    ):
        self.endpoint = endpoint
        self.timeout = timeout

    def is_authorized(
        # Toestemming stub needs: Ura, Pseudonym, and Category (datadomain)
        self,
        **kwargs: bool | str,
    ) -> bool:
        read_share = kwargs.get("read_share")
        ura_number = kwargs.get("ura_number")
        pseudonym = kwargs.get("pseudonym")
        category = kwargs.get("category")

        category = "hospital"  # TODO: Hardcoded category for now

        if read_share == "read":
            if not all([ura_number, pseudonym, category]):
                raise ValueError("Missing required parameters")
            input_json = {"ura_number": ura_number, "pseudonym": pseudonym, "category": category}
            url = f"{self.endpoint}/read-permission"
        elif read_share == "share":
            if not all([ura_number, pseudonym]):
                raise ValueError("Missing required parameters")
            input_json = {"ura_number": ura_number, "pseudonym": pseudonym}
            url = f"{self.endpoint}/share-permission"
        else:
            raise ValueError("Invalid read_share parameter, must be 'read' or 'share")

        return self.__request_permission(url, input_json)

    def __request_permission(self, url: str, json: Dict[str, Any]) -> bool:
        try:
            response = requests.post(url, timeout=self.timeout, json=json)
            response.raise_for_status()
        except (requests.RequestException, requests.HTTPError) as e:
            logger.error(f"Failed to reach authorization server: {e}")
            raise HTTPException(status_code=500, detail="Failed to reach authorization server") from e

        try:
            response_message = response.json()
            if not isinstance(response_message, bool):
                raise ValueError("Response is not a boolean")
            return response_message
        except ValueError as e:
            logger.error(f"Failed to parse response: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse response") from e
