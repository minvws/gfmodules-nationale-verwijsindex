from abc import ABC, abstractmethod

from app.models.ura import UraNumber


class BaseAuthService(ABC):
    @abstractmethod
    def is_authorized(
        self,
        client_ura_number: UraNumber,
        encrypted_lmr_id: str,
        lmr_endpoint: str,
    ) -> bool:
        pass
