from app.models.pseudonym import Pseudonym
from app.services.crypto_service_api_client import CryptoServiceApiClient


class CryptoServiceApiClientMock(CryptoServiceApiClient):
    def __init__(self) -> None:
        """Mock implementation of CryptoServiceApiClient for dev/testing purposes."""
        pass

    def exchange(self, jwe: str, blind_factor: str) -> Pseudonym:
        return Pseudonym(value=f"{jwe}:{blind_factor}")

    def is_healthy(self) -> bool:
        return True
