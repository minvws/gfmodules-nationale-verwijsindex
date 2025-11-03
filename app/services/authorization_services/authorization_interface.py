from abc import ABC, abstractmethod


class BaseAuthService(ABC):
    @abstractmethod
    def is_authorized(self, **kwargs: bool | str) -> bool:
        pass
