import logging
from typing import Any, Dict

from fastapi import Request

from app.models.ura import UraNumber
from app.services.oauth_token_validator import OAuthTokenValidator

logger = logging.getLogger(__name__)


class OAuthTokenValidatorMock(OAuthTokenValidator):
    def __init__(self, override_ura_number: UraNumber) -> None:
        self._override_ura_number = override_ura_number

    def verify(self, request: Request) -> Dict[str, Any]:
        logger.debug("Returning mocked token because OAuthTokenValidatorMock is enabled")
        return {"scope": "mocked", "sub": self._override_ura_number.value}
