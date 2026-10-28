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

    def add_one(
        self,
        encrypted_pseudonym: EncryptedPseudonym,
        ura_number: UraNumber,
        source: str,
        organization_name: str,
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
                gflog.emit(
                    logger,
                    Log.IDEMPOTENT_REGISTRATION,
                    "Idempotent referral registration",
                    fields={"ura_number": str(ura_number)},
                )
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
                fields={
                    "organization": organization_name,
                    "ura_number": str(ura_number),
                    "pseudonym_hash": str(encrypted_pseudonym),
                },
            )
            self.usage_metrics.registered(ura_number)
            return new_referral, True

    def get_one(
        self,
        encrypted_pseudonym: EncryptedPseudonym,
        ura_number: UraNumber,
        source: str,
    ) -> ReferralEntity | None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            referral = repo.find_one(
                pseudonym=encrypted_pseudonym.value,
                ura_number=str(ura_number),
                source=source,
            )

        return referral

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

    def localize(
        self,
        encrypted_pseudonym: EncryptedPseudonym,
        requesting_ura: UraNumber,
        organization_name: str,
    ) -> Sequence[ReferralEntity]:
        referrals = self.get_many(encrypted_pseudonym=encrypted_pseudonym)

        if referrals:
            gflog.emit(
                logger,
                Log.LOCALIZATION_SUCCESS,
                "Localization succeeded",
                fields={
                    "organization": organization_name,
                    "ura_number": str(requesting_ura),
                    "pseudonym_hash": str(encrypted_pseudonym),
                    "result_count": len(referrals),
                },
            )
        else:
            gflog.emit(
                logger,
                Log.LOCALIZATION_NO_MATCH,
                "Localization returned no match",
                fields={"ura_number": str(requesting_ura), "result_count": 0},
            )

        self.usage_metrics.localized(requesting_ura, len(referrals))
        return referrals

    def delete_many(
        self,
        ura_number: UraNumber,
        encrypted_pseudonym: EncryptedPseudonym | None = None,
        source: str | None = None,
        id: str | UUID | None = None,
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

    def delete_one(
        self,
        encrypted_pseudonym: EncryptedPseudonym,
        ura_number: UraNumber,
        source: str,
    ) -> None:
        """
        Method that removes a referral from the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)
            referral = referral_repository.find_one(
                pseudonym=encrypted_pseudonym.value,
                ura_number=str(ura_number),
                source=source,
            )
            if referral is None:
                raise NotFoundError()

            referral_repository.delete_one(referral)

    def delete_by_id(self, id: UUID) -> None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            target = repo.find_by_id(id)
            if target is None:
                raise NotFoundError()

            repo.delete_one(target)
