import logging
from typing import List
from uuid import UUID

import inject
from fastapi.exceptions import HTTPException

from app.data import ReferralRequestType
from app.db.db import Database
from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository
from app.exceptions.fhir_exception import FHIRException
from app.logger.referral_request_database_logger import ReferralRequestDatabaseLogger
from app.models.data_domain import DataDomain
from app.models.fhir.resources.data_reference.resource import NVIDataReferenceOutput
from app.models.pseudonym import Pseudonym
from app.models.referrals.entry import ReferralEntry
from app.models.referrals.logging import ReferralLoggingPayload
from app.models.ura import UraNumber

logger = logging.getLogger(__name__)
NOT_FOUND_EXCEPTION = FHIRException(
    status_code=404,
    code="not-found",
    severity="error",
    msg="NVIDataReference not found",
)


class ReferralService:
    @inject.autoparams()
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_by_id(self, id: UUID) -> NVIDataReferenceOutput:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            referral = repo.find_by_id(id)

            if referral is None:
                raise NOT_FOUND_EXCEPTION

            return NVIDataReferenceOutput.from_referral(referral)

    def get_referrals_by_domain_and_pseudonym(
        self,
        pseudonym: Pseudonym,
        data_domain: DataDomain,
    ) -> List[ReferralEntry]:
        """
        Method that gets all the referrals by pseudonym and data domain
        """

        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)
            entities = referral_repository.find_many(
                pseudonym=str(pseudonym), data_domain=str(data_domain), ura_number=None
            )
            if not entities:
                logger.info(f"No referrals found for pseudonym {str(pseudonym)} and data domain {str(data_domain)}")
                raise HTTPException(status_code=404)
            return [ReferralEntry.from_entity(e) for e in entities]

    def add_one(
        self,
        pseudonym: Pseudonym,
        data_domain: DataDomain,
        ura_number: UraNumber,
        uzi_number: str,
        request_url: str,
        organization_type: str | None = None,
    ) -> NVIDataReferenceOutput:
        """
        Method that adds a referral to the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)
            logging_payload = ReferralLoggingPayload(
                ura_number=ura_number,
                requesting_uzi_number=uzi_number,
                endpoint=request_url,
                request_type=ReferralRequestType.CREATE,
                payload={
                    "pseudonym": str(pseudonym),
                    "data_domain": str(data_domain),
                    "organization_type": organization_type,
                },
            )

            audit_logger = ReferralRequestDatabaseLogger(session)
            audit_logger.log(logging_payload)

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
            return NVIDataReferenceOutput.from_referral(new_referral)

    def get_one(
        self,
        pseudonym: Pseudonym,
        data_domain: DataDomain,
        ura_number: UraNumber,
    ) -> NVIDataReferenceOutput | None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            referral = repo.find_one(
                pseudonym=str(pseudonym),
                data_domain=str(data_domain),
                ura_number=str(ura_number),
            )

        if referral:
            return NVIDataReferenceOutput.from_referral(referral)

        return None

    def delete_one(
        self,
        pseudonym: Pseudonym,
        data_domain: DataDomain,
        ura_number: UraNumber,
        request_url: str,
    ) -> None:
        """
        Method that removes a referral from the database
        """
        with self.database.get_db_session() as session:
            logging_payload = ReferralLoggingPayload(
                ura_number=ura_number,
                requesting_uzi_number="000000",
                endpoint=request_url,
                request_type=ReferralRequestType.DELETE,
                payload={
                    "pseudonym": str(pseudonym),
                    "data_domain": str(data_domain),
                    "ura_number": str(ura_number),
                },
            )

            # Inject interface with DI when shared package is used (https://github.com/minvws/gfmodules-national-referral-index/issues/42)
            audit_logger = ReferralRequestDatabaseLogger(session)
            audit_logger.log(logging_payload)

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
    ) -> List[NVIDataReferenceOutput]:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            data = repo.find_many(
                ura_number=str(ura_number),
                data_domain=str(data_domain) if data_domain else None,
                pseudonym=str(pseudonym) if pseudonym else None,
            )

        return [NVIDataReferenceOutput.from_referral(e) for e in data]

    def delete_patient_registrations(self, ura_number: UraNumber, pseudonym: Pseudonym) -> None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            exists = repo.exists(ura_number=str(ura_number), pseudonym=str(pseudonym))
            if not exists:
                raise NOT_FOUND_EXCEPTION

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
                raise NOT_FOUND_EXCEPTION

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
                raise NOT_FOUND_EXCEPTION

            repo.delete(ura_number=str(ura_number))

    def delete_by_id(self, id: UUID) -> None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(ReferralRepository)
            target = repo.find_by_id(id)
            if target is None:
                raise NOT_FOUND_EXCEPTION

            repo.delete_one(target)

    def query_referrals(
        self,
        pseudonym: Pseudonym | None,
        data_domain: DataDomain | None,
        ura_number: UraNumber,
        request_url: str,
    ) -> List[ReferralEntry]:
        """
        Method that queries referrals from the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)
            logging_payload = ReferralLoggingPayload(
                ura_number=ura_number,
                requesting_uzi_number="000000",
                endpoint=request_url,
                request_type=ReferralRequestType.QUERY,
                payload={
                    "pseudonym": str(pseudonym) if pseudonym else None,
                    "data_domain": str(data_domain) if data_domain else None,
                    "ura_number": str(ura_number),
                },
            )
            # Inject interface with DI when shared package is used (https://github.com/minvws/gfmodules-national-referral-index/issues/42)
            audit_logger = ReferralRequestDatabaseLogger(session)
            audit_logger.log(logging_payload)

            entities = referral_repository.find_many(
                pseudonym=str(pseudonym) if pseudonym else None,
                data_domain=str(data_domain) if data_domain else None,
                ura_number=str(ura_number),
            )
            if not entities:
                raise HTTPException(status_code=404)
            return [ReferralEntry.from_entity(e) for e in entities]
