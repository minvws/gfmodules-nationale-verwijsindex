import logging
from typing import List
from uuid import UUID

import inject
from fastapi.exceptions import HTTPException

from app.db.db import Database
from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository
from app.exceptions.fhir_exception import FHIRException, NotFoundException
from app.models.data_domain import DataDomain
from app.models.fhir.resources.data_reference.resource import NVIDataReferenceOutput
from app.models.pseudonym import Pseudonym
from app.models.ura import UraNumber

logger = logging.getLogger(__name__)


class ReferralService:
    @inject.autoparams()
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_by_id(self, id: UUID) -> NVIDataReferenceOutput:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            referral = repo.find_by_id(id)

            if referral is None:
                raise NotFoundException

            return NVIDataReferenceOutput.from_referral(referral)

    def add_one(
        self,
        pseudonym: Pseudonym,
        data_domain: DataDomain,
        ura_number: UraNumber,
        source: str,
        organization_type: str | None = None,
    ) -> NVIDataReferenceOutput:
        """
        Method that adds a referral to the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)

            if referral_repository.exists(
                pseudonym=str(pseudonym),
                data_domain=str(data_domain),
                ura_number=str(ura_number),
                source=source,
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
                    source=source,
                    organization_type=organization_type,
                )
            )
            return NVIDataReferenceOutput.from_referral(new_referral)

    def get_one(
        self,
        pseudonym: Pseudonym,
        data_domain: DataDomain,
        ura_number: UraNumber,
        source: str,
    ) -> NVIDataReferenceOutput | None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            referral = repo.find_one(
                pseudonym=str(pseudonym),
                data_domain=str(data_domain),
                ura_number=str(ura_number),
                source=source,
            )

        if referral:
            return NVIDataReferenceOutput.from_referral(referral)

        return None

    def delete_one(
        self,
        pseudonym: Pseudonym,
        data_domain: DataDomain,
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
                data_domain=str(data_domain),
                ura_number=str(ura_number),
                source=source,
            )
            if referral is None:
                raise HTTPException(status_code=404)

            referral_repository.delete_one(referral)

    def get_registrations(
        self,
        ura_number: UraNumber,
        data_domain: DataDomain | None = None,
        pseudonym: Pseudonym | None = None,
        source: str | None = None,
    ) -> List[NVIDataReferenceOutput]:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            data = repo.find_many(
                ura_number=str(ura_number),
                data_domain=str(data_domain) if data_domain else None,
                pseudonym=str(pseudonym) if pseudonym else None,
                source=source,
            )

        return [NVIDataReferenceOutput.from_referral(e) for e in data]

    def delete_patient_registrations(self, ura_number: UraNumber, pseudonym: Pseudonym) -> None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            exists = repo.exists(ura_number=str(ura_number), pseudonym=str(pseudonym))
            if not exists:
                raise NotFoundException

            repo.delete(ura_number=str(ura_number), pseudonym=str(pseudonym))

    def delete_specific_registration(
        self,
        ura_number: UraNumber,
        data_domain: DataDomain,
        pseudonym: Pseudonym,
        source: str,
    ) -> None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            exists = repo.exists(
                ura_number=str(ura_number),
                data_domain=str(data_domain),
                pseudonym=str(pseudonym),
                source=source,
            )
            if not exists:
                raise NotFoundException

            repo.delete(
                ura_number=str(ura_number),
                pseudonym=str(pseudonym),
                data_domain=str(data_domain),
                source=source,
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
