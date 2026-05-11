import logging
from typing import Sequence
from uuid import UUID

from app.db.db import Database
from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository
from app.models.pseudonym import Pseudonym
from app.models.ura import UraNumber
from app.services.exceptions import ConflictError
from app.services.fhir.exceptions import FHIRException, NotFoundException

logger = logging.getLogger(__name__)


class ReferralService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_by_id(self, id: UUID) -> ReferralEntity:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            referral = repo.find_by_id(id)

            if referral is None:
                raise NotFoundException

            return referral

    def add_one(
        self,
        pseudonym: Pseudonym,
        ura_number: UraNumber,
        source: str,
        organization_type: str | None = None,
    ) -> ReferralEntity:
        """
        Method that adds a referral to the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)

            if referral_repository.exists(
                pseudonym=str(pseudonym),
                ura_number=str(ura_number),
                source=source,
            ):
                raise ConflictError()

            new_referral: ReferralEntity = referral_repository.add_one(
                ReferralEntity(
                    pseudonym=str(pseudonym),
                    ura_number=str(ura_number),
                    source=source,
                    organization_type=organization_type,
                )
            )
            return new_referral

    def get_one(
        self,
        pseudonym: Pseudonym,
        ura_number: UraNumber,
        source: str,
    ) -> ReferralEntity | None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            referral = repo.find_one(
                pseudonym=str(pseudonym),
                ura_number=str(ura_number),
                source=source,
            )

        return referral

    def get_many(
        self,
        ura_number: UraNumber | None = None,
        pseudonym: Pseudonym | None = None,
        source: str | None = None,
    ) -> Sequence[ReferralEntity]:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            referrals = repo.find_many(
                ura_number=str(ura_number) if ura_number else None,
                pseudonym=str(pseudonym) if pseudonym else None,
                source=source,
            )

        return referrals

    def delete_many(
        self,
        ura_number: UraNumber,
        pseudonym: Pseudonym | None = None,
        source: str | None = None,
        id: str | UUID | None = None,
    ) -> int:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            affected_rows = repo.delete_many(
                ura_number=str(ura_number),
                pseudonym=str(pseudonym) if pseudonym else None,
                source=source,
                id=id,
            )

            session.commit()

        return affected_rows

    def delete_one(
        self,
        pseudonym: Pseudonym,
        ura_number: UraNumber,
        source: str,
    ) -> None:
        """
        Method that removes a referral from the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)
            referral = referral_repository.find_one(
                pseudonym=str(pseudonym),
                ura_number=str(ura_number),
                source=source,
            )
            if referral is None:
                raise FHIRException(
                    status_code=404,
                    severity="error",
                    code="not-found",
                    msg="Record does not exist",
                )

            referral_repository.delete_one(referral)

    def delete_by_id(self, id: UUID) -> None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            target = repo.find_by_id(id)
            if target is None:
                raise NotFoundException

            repo.delete_one(target)
