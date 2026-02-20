import logging
from typing import Sequence
from uuid import UUID

import inject
from fastapi.exceptions import HTTPException

from app.db.db import Database
from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository
from app.exceptions.fhir_exception import FHIRException, NotFoundException
from app.models.data_domain import DataDomain
from app.models.pseudonym import Pseudonym
from app.models.ura import UraNumber

logger = logging.getLogger(__name__)


class ReferralService:
    @inject.autoparams()
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
        data_domain: DataDomain,
        ura_number: UraNumber,
        organization_type: str | None = None,
    ) -> ReferralEntity:
        """
        Method that adds a referral to the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)

            if referral_repository.exists(
                pseudonym=str(pseudonym),
                data_domain=str(data_domain),
                ura_number=str(ura_number),
            ):
                raise FHIRException(
                    status_code=409,
                    code="conflict",
                    severity="error",
                    msg="NVIDataReference already exists",
                )

            new_referral: ReferralEntity = referral_repository.add_one(
                ReferralEntity(
                    pseudonym=str(pseudonym),
                    data_domain=str(data_domain),
                    ura_number=str(ura_number),
                    organization_type=organization_type,
                )
            )
            return new_referral

    def get_one(
        self,
        pseudonym: Pseudonym,
        data_domain: DataDomain,
        ura_number: UraNumber,
    ) -> ReferralEntity | None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            referral = repo.find_one(
                pseudonym=str(pseudonym),
                data_domain=str(data_domain),
                ura_number=str(ura_number),
            )

        if referral:
            return referral

        return None

    def delete_one(
        self,
        pseudonym: Pseudonym,
        data_domain: DataDomain,
        ura_number: UraNumber,
    ) -> None:
        """
        Method that removes a referral from the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)
            referral = referral_repository.find_one(
                pseudonym=str(pseudonym),
                data_domain=str(data_domain),
                ura_number=str(ura_number),
            )
            if referral is None:
                raise HTTPException(status_code=404)

            referral_repository.delete_one(referral)

    def get_registrations(
        self,
        ura_number: UraNumber,
        data_domain: DataDomain | None = None,
        pseudonym: Pseudonym | None = None,
    ) -> Sequence[ReferralEntity]:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            data = repo.find_many(
                ura_number=str(ura_number),
                data_domain=str(data_domain) if data_domain else None,
                pseudonym=str(pseudonym) if pseudonym else None,
            )

        return data

    def delete_patient_registrations(self, ura_number: UraNumber, pseudonym: Pseudonym) -> None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            exists = repo.exists(ura_number=str(ura_number), pseudonym=str(pseudonym))
            if not exists:
                raise NotFoundException

            repo.delete(ura_number=str(ura_number), pseudonym=str(pseudonym))

    def delete_specific_registration(
        self, ura_number: UraNumber, data_domain: DataDomain, pseudonym: Pseudonym
    ) -> None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            exists = repo.exists(
                ura_number=str(ura_number),
                data_domain=str(data_domain),
                pseudonym=str(pseudonym),
            )
            if not exists:
                raise NotFoundException

            repo.delete(
                ura_number=str(ura_number),
                pseudonym=str(pseudonym),
                data_domain=str(data_domain),
            )

    def delete_specific_organization(self, ura_number: UraNumber) -> None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            org_exists = repo.exists(ura_number=str(ura_number))
            if not org_exists:
                raise NotFoundException

            repo.delete(ura_number=str(ura_number))

    def delete_by_id(self, id: UUID) -> None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            target = repo.find_by_id(id)
            if target is None:
                raise NotFoundException

            repo.delete_one(target)
