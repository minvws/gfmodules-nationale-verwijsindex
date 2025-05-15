import abc

from starlette.requests import Request

from app.data import UraNumber


class UraMiddleware(abc.ABC):
    @abc.abstractmethod
    def authenticated_ura(self, request: Request) -> UraNumber: ...
