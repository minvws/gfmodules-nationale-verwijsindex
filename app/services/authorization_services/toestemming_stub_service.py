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
        # Toestemming stub needs: source_ura or source_category, and target_ura or target_Category and a pseudonym
        self,
        **kwargs: bool | str,
    ) -> bool:
        pseudonym = kwargs.get("pseudonym")
        source_ura_number = kwargs.get("source_ura_number")
        source_category = kwargs.get("source_category")
        target_ura_number = kwargs.get("target_ura_number")
        target_category = kwargs.get("target_category")

        url = f"{self.endpoint}/permission"
        input_json = {
            "pseudonym": pseudonym,
            "source_ura_number": source_ura_number,
            "source_category": source_category,
            "target_ura_number": target_ura_number,
            "target_category": target_category,
        }

        input_json = {k: v for k, v in input_json.items() if v is not None}

        print(input_json)

        try:
            response = requests.post(url, timeout=self.timeout, json=input_json)
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
