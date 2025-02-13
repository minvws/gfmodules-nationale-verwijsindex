from abc import ABC, abstractmethod

from app.data import DataDomain, Pseudonym, UraNumber


class BaseAuthService(ABC):
    @abstractmethod
    def is_authorized(self, ura_number: UraNumber, pseudonym: Pseudonym, data_domain: DataDomain) -> bool:
        pass
