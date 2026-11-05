import logging
from collections.abc import Sequence

import gfmodules.logging as gflog
from gfmodules.logging import LogEvent

from app.db.models.referral import ReferralEntity
from app.errors.mapping import should_log, spec_for
from app.logging.events import Log
from app.models.pseudonym import EncryptedPseudonym, OprfPseudonym
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


def _failure_event(exc: Exception, failed: LogEvent, error: LogEvent) -> LogEvent:
    return failed if spec_for(exc).http_status < 500 else error


class PseudonymReferralService:
    def __init__(self, referral_service: ReferralService, pseudonym_resolver: PseudonymResolver) -> None:
        self._referral_service = referral_service
        self._pseudonym_resolver = pseudonym_resolver

    def register(
        self,
        pseudonym: OprfPseudonym,
        ura_number: UraNumber,
        source: str,
    ) -> tuple[ReferralEntity, bool]:
        try:
            resolved = self._pseudonym_resolver.resolve(pseudonym)
            return self._referral_service.add_one(resolved.encrypted, ura_number, source, resolved.key_id)
        except Exception as exc:
            event = _failure_event(exc, Log.REFERRAL_REGISTRATION_FAILED, Log.REFERRAL_REGISTRATION_ERROR)
            _log_failure(event, "Referral registration failed", exc)
            raise

    def localize(
        self,
        pseudonym: OprfPseudonym,
        requesting_ura: UraNumber,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[int, Sequence[ReferralEntity]]:
        try:
            encrypted = self._resolve_encrypted(pseudonym)
            return self._referral_service.localize(encrypted, requesting_ura, limit=limit, offset=offset)
        except Exception as exc:
            event = _failure_event(exc, Log.LOCALIZATION_FAILED, Log.LOCALIZATION_ERROR)
            _log_failure(event, "Localization failed", exc)
            raise

    def query(
        self,
        ura_number: UraNumber,
        pseudonym: OprfPseudonym | None = None,
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
        pseudonym: OprfPseudonym | None = None,
        source: str | None = None,
    ) -> int:
        encrypted = self._resolve_encrypted(pseudonym) if pseudonym else None
        return self._referral_service.delete_many(ura_number, encrypted_pseudonym=encrypted, source=source)

    def _resolve_encrypted(self, pseudonym: OprfPseudonym) -> EncryptedPseudonym:
        return self._pseudonym_resolver.resolve(pseudonym).encrypted
