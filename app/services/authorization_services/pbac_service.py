import logging

import requests
from fastapi.exceptions import HTTPException

from app.services.authorization_services.authorization_interface import BaseAuthService
from app.telemetry import get_tracer

logger = logging.getLogger(__name__)


class PbacService(BaseAuthService):
    def __init__(
        self,
        endpoint: str,
        timeout: int,
    ):
        self.endpoint = endpoint
        self.timeout = timeout

    def is_authorized(self, **kwargs: bool | str) -> bool:
        explicit_permission = kwargs.get("explicit_permission", None)
        if explicit_permission is None:
            raise HTTPException(status_code=500, detail="Missing explicit permission parameter")
        """
        Method that checks through PBAC if a URA number is authorized
        """
        input_json = {
            "input": {
                "explicit_permission": explicit_permission,
            }
        }
        with get_tracer().start_as_current_span("PBAC") as span:  # type: ignore
            span.set_attribute("input", str(input_json))

            try:
                response = requests.post(
                    f"{self.endpoint}/v1/data/example/authz", timeout=self.timeout, json=input_json
                )
                response.raise_for_status()
            except (requests.RequestException, requests.HTTPError) as e:
                logger.error(f"Failed to reach authorization server: {e}")
                raise HTTPException(status_code=500, detail="Failed to reach authorization server") from e

            try:
                response_message = response.json()
                span.set_attribute("response", str(response_message))

                if not isinstance(response_message, dict):
                    raise ValueError("Response is not a JSON object")

                result = response_message.get("result")
                if not isinstance(result, dict):
                    raise KeyError("Missing or invalid 'result' field in response")

                allow = result.get("allow")
                if not isinstance(allow, bool):
                    raise KeyError("'allow' field is missing or not a boolean")

                return allow

            except (ValueError, KeyError) as e:
                logger.error(f"Failed to parse response: {e}")
                raise HTTPException(status_code=500, detail="Failed to parse response from authorization server") from e
