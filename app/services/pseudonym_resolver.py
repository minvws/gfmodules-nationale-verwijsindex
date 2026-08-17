import logging
from dataclasses import dataclass
from functools import cached_property
from uuid import UUID

from app.models.fhir.resources.localization_list.request import SUBJECT_IDENTIFIER_PARAM
from app.models.pseudonym import EncryptedPseudonym, PseudonymResponse
from app.services.crypto_service_api_client import CryptoServiceApiClient
from app.services.exceptions import PseudonymError
from app.services.key_info import KeyInfoService
from app.utils.fhir import decode_url_safe_token

logger = logging.getLogger(__name__)


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

    def resolve_jwe(self, jwe: str, blind_factor: str) -> ResolvedPseudonym:
        active_key = self._key_info_service.get_active_key()
        response = self._crypto_client.exchange(
            jwe=jwe,
            blind_factor=blind_factor,
            label=active_key.label,
            mechanism=active_key.mechanism,
        )
        return ResolvedPseudonym(response=response, key_id=active_key.id)

    def resolve_token(self, token: str) -> ResolvedPseudonym:
        active_key = self._key_info_service.get_active_key()
        # Only decoding is the client's responsibility. The exchange stays outside this
        # block so that a crypto-service fault surfaces as itself rather than being
        # reported back as an invalid pseudonym.
        try:
            data = decode_url_safe_token(token)
            jwe = data["evaluated_output"]
            blind_factor = data["blind_factor"]
        except Exception:
            logger.exception("Error occurred while decoding pseudonym token")
            raise PseudonymError(f"Invalid pseudonym in {SUBJECT_IDENTIFIER_PARAM}")

        response = self._crypto_client.exchange(
            jwe=jwe,
            blind_factor=blind_factor,
            label=active_key.label,
            mechanism=active_key.mechanism,
        )
        return ResolvedPseudonym(response=response, key_id=active_key.id)
