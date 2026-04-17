import logging

from app.config import ConfigOAuth
from app.models.auth.headers import AuthHeaders
from app.services.auth.exceptions import (
    InvalidHeaderPropertyValue,
)

logger = logging.getLogger(__name__)


class AuthHeaderService:
    def __init__(self, config: ConfigOAuth) -> None:
        self.config = config

    def validate(self, auth_headers: AuthHeaders) -> AuthHeaders:
        audience = auth_headers.x_audience

        if audience != self.config.audience:
            logger.error(
                f"Invalid audience value {audience} value should be {self.config.audience}. Check config values in case incoming value is correct"
            )
            InvalidHeaderPropertyValue("audience", audience)

        return auth_headers
