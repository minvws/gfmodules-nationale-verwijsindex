from typing import Any, Dict

from fastapi import Request

from app.models.ura import UraNumber
from app.services.oauth import OAuthService


class OAuthServiceMock(OAuthService):
    def __init__(self, override_ura_number: UraNumber):
        self._override_ura_number = override_ura_number

    def verify(self, request: Request) -> Dict[str, Any]:
        return {"scope": "", "sub": self._override_ura_number.value}

    def override_ura_number(self) -> UraNumber:
        return self._override_ura_number
