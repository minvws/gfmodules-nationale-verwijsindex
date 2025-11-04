import abc

from starlette.requests import Request

from app.data_models.typing import UraNumber


class UraMiddleware(abc.ABC):
    @abc.abstractmethod
    def authenticated_ura(self, request: Request) -> UraNumber: ...
