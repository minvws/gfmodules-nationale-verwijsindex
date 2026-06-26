import logging
from typing import List

from app.models.auth.headers import AuthHeaders
from app.services.exceptions import InvalidHeaderPropertyError

logger = logging.getLogger(__name__)


class AuthHeaderService:
    def __init__(self, expected_audiences: List[str]) -> None:
        self.expected_audiences = expected_audiences

    def validate(self, auth_headers: AuthHeaders) -> AuthHeaders:
        audience = auth_headers.audience

        if audience not in self.expected_audiences:
            logger.error(
                f"Invalid audience value {audience} value should be {self.expected_audiences}. Check config values in case incoming value is correct"
            )
            raise InvalidHeaderPropertyError("audience", audience)

        return auth_headers
