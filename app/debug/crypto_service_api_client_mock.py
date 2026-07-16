from app.models.pseudonym import PseudonymResponse
from app.services.crypto_service_api_client import CryptoServiceApiClient


class CryptoServiceApiClientMock(CryptoServiceApiClient):
    def __init__(self) -> None:
        """Mock implementation of CryptoServiceApiClient for dev/testing purposes."""
        pass

    def exchange(self, jwe: str, blind_factor: str, label: str, mechanism: str) -> PseudonymResponse:
        return PseudonymResponse(
            encrypted_pseudonym=f"{jwe}:{blind_factor}",
            iv="abcdefghijklmnop",
        )

    def is_healthy(self) -> bool:
        return True
