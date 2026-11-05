from app.models.pseudonym import OprfPseudonym, PseudonymResponse
from app.services.crypto_service_api_client import CryptoServiceApiClient


class CryptoServiceApiClientMock(CryptoServiceApiClient):
    def __init__(self) -> None:
        """Mock implementation of CryptoServiceApiClient for dev/testing purposes."""

    def exchange(self, pseudonym: OprfPseudonym, label: str, mechanism: str) -> PseudonymResponse:
        return PseudonymResponse(
            encrypted_pseudonym=f"{pseudonym.jwe}:{pseudonym.blind_factor}",
            iv="abcdefghijklmnop",
        )

    def is_healthy(self) -> bool:
        return True
