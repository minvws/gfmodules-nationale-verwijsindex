import logging
from collections.abc import Sequence

import gfmodules.logging as gflog
from gfmodules.logging import LogEvent

from app.db.models.referral import ReferralEntity
from app.errors.mapping import should_log, spec_for
from app.logging.events import Log
from app.models.pseudonym import BlindedPseudonym, EncryptedPseudonym
from app.models.ura import UraNumber
from app.services.pseudonym_resolver import PseudonymResolver
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)


def _log_failure(event: LogEvent, message: str, exc: Exception) -> None:
    if should_log(exc):
        gflog.emit(
            logger,
            event,
            message,
            fields={"http_status": spec_for(exc).http_status, "error_reason": str(exc)},
        )


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
        try:
            resolved = self._pseudonym_resolver.resolve(pseudonym)
            return self._referral_service.add_one(resolved.encrypted, ura_number, source, resolved.key_id)
        except Exception as exc:
            _log_failure(Log.REFERRAL_REGISTRATION_FAILED, "Referral registration failed", exc)
            raise

    def localize(self, pseudonym: BlindedPseudonym, requesting_ura: UraNumber) -> Sequence[ReferralEntity]:
        try:
            resolved = self._pseudonym_resolver.resolve(pseudonym)
            return self._referral_service.localize(resolved.encrypted, requesting_ura)
        except Exception as exc:
            event = Log.LOCALIZATION_FAILED if spec_for(exc).http_status < 500 else Log.LOCALIZATION_ERROR
            _log_failure(event, "Localization failed", exc)
            raise

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
