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

    def localize(self, pseudonym: BlindedPseudonym, requesting_ura: UraNumber) -> Sequence[ReferralEntity]:
        resolved = self._pseudonym_resolver.resolve(pseudonym)
        return self._referral_service.localize(resolved.encrypted, requesting_ura)

    def query(
        self,
        ura_number: UraNumber,
        pseudonym: BlindedPseudonym | None = None,
        source: str | None = None,
    ) -> Sequence[ReferralEntity]:
        return self._referral_service.query(ura_number, encrypted_pseudonym=self._encrypt(pseudonym), source=source)

    def delete_many(
        self,
        ura_number: UraNumber,
        pseudonym: BlindedPseudonym | None = None,
        source: str | None = None,
    ) -> int:
        return self._referral_service.delete_many(
            ura_number, encrypted_pseudonym=self._encrypt(pseudonym), source=source
        )

    def _encrypt(self, pseudonym: BlindedPseudonym | None) -> EncryptedPseudonym | None:
        if pseudonym is None:
            return None
        return self._pseudonym_resolver.resolve(pseudonym).encrypted
