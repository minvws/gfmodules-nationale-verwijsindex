from starlette.requests import Request

from app.data import UraNumber
from app.ura.ura_middleware.ura_middleware import UraMiddleware


class ConfigBasedUraMiddleware(UraMiddleware):
    _config_value: UraNumber

    def __init__(self, config_value: UraNumber) -> None:
        self._config_value = config_value

    def authenticated_ura(self, request: Request) -> UraNumber:
        return self._config_value
