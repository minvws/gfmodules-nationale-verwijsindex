import logging
from collections.abc import Sequence
from uuid import UUID

import gfmodules.logging as gflog

from app.db.db import Database
from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository
from app.logging.events import Log
from app.metrics import UsageMetrics
from app.models.pseudonym import EncryptedPseudonym
from app.models.ura import UraNumber
from app.services.exceptions import (
    NotFoundError,
)

logger = logging.getLogger(__name__)


class ReferralService:
    def __init__(self, database: Database, usage_metrics: UsageMetrics) -> None:
        self.database = database
        self.usage_metrics = usage_metrics

    def get_by_id(self, id: UUID) -> ReferralEntity:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            referral = repo.find_by_id(id)

            if referral is None:
                raise NotFoundError()

            return referral

    def read(self, id: UUID, ura_number: UraNumber) -> ReferralEntity:
        referral = self._get_owned(id, ura_number)
        gflog.emit(
            logger,
            Log.REFERRAL_SEARCHED_ON_ID,
            "Referral searched on id",
            fields={"pseudonym_hash": referral.pseudonym},
        )
        return referral

    def _get_owned(self, id: UUID, ura_number: UraNumber) -> ReferralEntity:
        referral = self.get_by_id(id)
        if ura_number != UraNumber(referral.ura_number):
            gflog.emit(
                logger,
                Log.REFERRAL_ACCESS_DENIED,
                "Referral access denied: URA mismatch",
                fields={"resource_ura": referral.ura_number},
            )
            raise NotFoundError()
        return referral

    def add_one(
        self,
        encrypted_pseudonym: EncryptedPseudonym,
        ura_number: UraNumber,
        source: str,
        key_id: UUID,
    ) -> tuple[ReferralEntity, bool]:
        """
        Store a referral, or return the stored one when it already exists.

        Returns the referral and whether it was created by this call.
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)

            existing = referral_repository.find_one(
                pseudonym=encrypted_pseudonym.value,
                ura_number=str(ura_number),
                source=source,
            )
            if existing is not None:
                gflog.emit(logger, Log.IDEMPOTENT_REGISTRATION, "Idempotent referral registration")
                return existing, False

            new_referral: ReferralEntity = referral_repository.add_one(
                ReferralEntity(
                    pseudonym=encrypted_pseudonym.value,
                    ura_number=str(ura_number),
                    source=source,
                    key_id=key_id,
                )
            )

            gflog.emit(
                logger,
                Log.REGISTERED_REFERRAL,
                "Referral registered",
                fields={"pseudonym_hash": str(encrypted_pseudonym)},
            )
            self.usage_metrics.registered(ura_number)
            return new_referral, True

    def get_many(
        self,
        ura_number: UraNumber | None = None,
        encrypted_pseudonym: EncryptedPseudonym | None = None,
        source: str | None = None,
    ) -> Sequence[ReferralEntity]:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            referrals = repo.find_many(
                ura_number=str(ura_number) if ura_number else None,
                pseudonym=encrypted_pseudonym.value if encrypted_pseudonym else None,
                source=source,
            )

        return referrals

    def query(
        self,
        ura_number: UraNumber,
        encrypted_pseudonym: EncryptedPseudonym | None = None,
        source: str | None = None,
    ) -> Sequence[ReferralEntity]:
        referrals = self.get_many(ura_number=ura_number, encrypted_pseudonym=encrypted_pseudonym, source=source)
        gflog.emit(
            logger,
            Log.REFERRALS_QUERIED,
            "Referrals queried",
            fields={"result_count": len(referrals)},
        )
        return referrals

    def localize(
        self,
        encrypted_pseudonym: EncryptedPseudonym,
        requesting_ura: UraNumber,
    ) -> Sequence[ReferralEntity]:
        referrals = self.get_many(encrypted_pseudonym=encrypted_pseudonym)

        if referrals:
            gflog.emit(
                logger,
                Log.LOCALIZATION_SUCCESS,
                "Localization succeeded",
                fields={"pseudonym_hash": str(encrypted_pseudonym), "result_count": len(referrals)},
            )
        else:
            gflog.emit(
                logger,
                Log.LOCALIZATION_NO_MATCH,
                "Localization returned no match",
                fields={"result_count": 0},
            )

        self.usage_metrics.localized(requesting_ura, len(referrals))
        return referrals

    def delete_many(
        self,
        ura_number: UraNumber,
        encrypted_pseudonym: EncryptedPseudonym | None = None,
        source: str | None = None,
    ) -> int:
        deleted_count = self._delete(ura_number=ura_number, encrypted_pseudonym=encrypted_pseudonym, source=source)
        if deleted_count < 1:
            return deleted_count

        if encrypted_pseudonym is not None:
            gflog.emit(
                logger,
                Log.ALL_PATIENT_REFERRALS_DELETED,
                "All patient referrals deleted",
                fields={"pseudonym_hash": str(encrypted_pseudonym), "deleted_count": deleted_count},
            )
        else:
            gflog.emit(
                logger,
                Log.ALL_URA_REFERRALS_DELETED,
                "All URA referrals deleted",
                fields={"deleted_count": deleted_count},
            )
        return deleted_count

    def delete_by_id(self, id: UUID, ura_number: UraNumber, source: str) -> None:
        referral = self._get_owned(id, ura_number)
        if self._delete(ura_number=ura_number, source=source, id=id) < 1:
            raise NotFoundError()

        gflog.emit(
            logger,
            Log.REFERRAL_DELETED,
            "Referral deleted",
            fields={"pseudonym_hash": referral.pseudonym},
        )

    def _delete(
        self,
        ura_number: UraNumber,
        encrypted_pseudonym: EncryptedPseudonym | None = None,
        source: str | None = None,
        id: UUID | None = None,
    ) -> int:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            affected_rows = repo.delete_many(
                ura_number=str(ura_number),
                pseudonym=encrypted_pseudonym.value if encrypted_pseudonym else None,
                source=source,
                id=id,
            )

            session.commit()

        if affected_rows > 0:
            self.usage_metrics.deleted(ura_number, affected_rows)
        return affected_rows
