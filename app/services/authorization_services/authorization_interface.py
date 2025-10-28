from abc import ABC, abstractmethod

from app.data import Pseudonym, UraNumber


class BaseAuthService(ABC):
    @abstractmethod
    def is_authorized(
        self,
        endpoint: str,
        pseudonym: Pseudonym,
        requesting_ura_number: UraNumber,
        encrypted_lmr_id: str,
    ) -> bool:
        pass
