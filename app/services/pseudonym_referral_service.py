from collections.abc import Sequence

from app.db.models.referral import ReferralEntity
from app.models.pseudonym import BlindedPseudonym, EncryptedPseudonym
from app.models.ura import UraNumber
from app.services.pseudonym_resolver import PseudonymResolver
from app.services.referral_service import ReferralService


class PseudonymReferralService:
    def __init__(self, referral_service: ReferralService, pseudonym_resolver: PseudonymResolver) -> None:
        self._referral_service = referral_service
        self._pseudonym_resolver = pseudonym_resolver

    def register(
        self,
        pseudonym: BlindedPseudonym,
        ura_number: UraNumber,
        source: str,
    ) -> tuple[ReferralEntity, bool]:
        resolved = self._pseudonym_resolver.resolve(pseudonym)
        return self._referral_service.add_one(resolved.encrypted, ura_number, source, resolved.key_id)

    def localize(
        self,
        pseudonym: BlindedPseudonym,
        requesting_ura: UraNumber,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[int, Sequence[ReferralEntity]]:
        encrypted = self._resolve_encrypted(pseudonym)
        return self._referral_service.localize(encrypted, requesting_ura, limit=limit, offset=offset)

    def query(
        self,
        ura_number: UraNumber,
        pseudonym: BlindedPseudonym | None = None,
        source: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[int, Sequence[ReferralEntity]]:
        encrypted = self._resolve_encrypted(pseudonym) if pseudonym else None
        return self._referral_service.query(
            ura_number, encrypted_pseudonym=encrypted, source=source, limit=limit, offset=offset
        )

    def delete_many(
        self,
        ura_number: UraNumber,
        pseudonym: BlindedPseudonym | None = None,
        source: str | None = None,
    ) -> int:
        encrypted = self._resolve_encrypted(pseudonym) if pseudonym else None
        return self._referral_service.delete_many(ura_number, encrypted_pseudonym=encrypted, source=source)

    def _resolve_encrypted(self, pseudonym: BlindedPseudonym) -> EncryptedPseudonym:
        return self._pseudonym_resolver.resolve(pseudonym).encrypted
