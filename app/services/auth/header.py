import logging

from fastapi import Request

from app.config import ConfigOAuth
from app.services.auth.exceptions import (
    InvalidHeaderPropertyValue,
    MissingHeaderProperty,
)

logger = logging.getLogger(__name__)


class AuthHeaderService:
    def __init__(self, config: ConfigOAuth) -> None:
        self.config = config

    def validate(self, request: Request) -> Request:
        # TODO: temoporary return in case Token Bearer exists, needs to be removed once
        # support for LDN is deprecated
        token = request.headers.get("authorization")
        if token is not None:
            return request

        audience = request.headers.get("x-audience")
        if audience is None:
            raise MissingHeaderProperty("audience")

        if audience != self.config.audience:
            logger.error(
                f"Invalid audience value {audience} value should be {self.config.audience}. Check config values in case incoming value is correct"
            )
            InvalidHeaderPropertyValue("audience", audience)

        return request
