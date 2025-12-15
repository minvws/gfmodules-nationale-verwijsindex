from starlette.requests import Request

from app.middleware.ura.allowlisted_ura_middleware import AllowlistedUraMiddleware
from app.middleware.ura.ura_middleware import UraMiddleware
from app.models.ura import UraNumber


class ConfigBasedUraMiddleware(UraMiddleware):
    def __init__(
        self,
        config_value: UraNumber,
        filter_service: AllowlistedUraMiddleware | None = None,
    ) -> None:
        self._config_value = config_value
        self.filter_service = filter_service

    def authenticated_ura(self, request: Request) -> UraNumber:
        if self.filter_service:
            return self.filter_service.filter(self._config_value)

        return self._config_value
