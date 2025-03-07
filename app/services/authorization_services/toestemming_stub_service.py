import logging

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
        ura_number = kwargs.get("ura_number")
        pseudonym = kwargs.get("pseudonym")
        category = kwargs.get("category")

        category = "hospital"  # Hardcoded category for now

        if not all([ura_number, pseudonym, category]):
            raise ValueError("Missing required parameters")
        input_json = {"ura_number": ura_number, "pseudonym": pseudonym, "category": category}

        try:
            response = requests.post(f"{self.endpoint}/read-permission", timeout=self.timeout, json=input_json)
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
            raise HTTPException(status_code=500, detail="Failed to parse response")
