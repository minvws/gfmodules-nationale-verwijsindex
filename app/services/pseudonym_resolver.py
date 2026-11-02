from dataclasses import dataclass
from functools import cached_property
from uuid import UUID

from app.models.pseudonym import EncryptedPseudonym, OprfPseudonym, PseudonymResponse
from app.services.crypto_service_api_client import CryptoServiceApiClient
from app.services.key_info import KeyInfoService


@dataclass
class ResolvedPseudonym:
    response: PseudonymResponse
    key_id: UUID

    @cached_property
    def encrypted(self) -> EncryptedPseudonym:
        return EncryptedPseudonym.from_response(self.response)


class PseudonymResolver:
    def __init__(
        self,
        crypto_client: CryptoServiceApiClient,
        key_info_service: KeyInfoService,
    ) -> None:
        self._crypto_client = crypto_client
        self._key_info_service = key_info_service

    def resolve(self, pseudonym: OprfPseudonym) -> ResolvedPseudonym:
        active_key = self._key_info_service.get_active_key()
        response = self._crypto_client.exchange(pseudonym, label=active_key.label, mechanism=active_key.mechanism)
        return ResolvedPseudonym(response=response, key_id=active_key.id)
