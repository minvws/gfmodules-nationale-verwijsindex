import logging
from typing import List

import inject
from fastapi.exceptions import HTTPException

from app.data import ReferralRequestType
from app.db.db import Database
from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository
from app.logger.referral_request_database_logger import ReferralRequestDatabaseLogger
from app.models.data_domain import DataDomain
from app.models.pseudonym import Pseudonym
from app.models.referrals.entry import ReferralEntry
from app.models.referrals.logging import ReferralLoggingPayload
from app.models.ura import UraNumber

logger = logging.getLogger(__name__)


class ReferralService:
    @inject.autoparams()
    def __init__(self, database: Database) -> None:
        self.database = database

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
            entities = referral_repository.query_referrals(
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
        encrypted_lmr_id: str,
        lmr_endpoint: str,
    ) -> ReferralEntry:
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
                    "encrypted_lmr_id": encrypted_lmr_id,
                    "lmr_endpoint": lmr_endpoint,
                },
            )

            audit_logger = ReferralRequestDatabaseLogger(session)
            audit_logger.log(logging_payload)

            if referral_repository.exists(
                pseudonym=str(pseudonym),
                data_domain=str(data_domain),
                ura_number=str(ura_number),
            ):
                raise HTTPException(status_code=409)

            new_referral: ReferralEntity = referral_repository.add_one(
                ReferralEntity(
                    pseudonym=str(pseudonym),
                    data_domain=str(data_domain),
                    ura_number=str(ura_number),
                    encrypted_lmr_id=encrypted_lmr_id,
                    lmr_endpoint=lmr_endpoint,
                )
            )
            return ReferralEntry.from_entity(new_referral)

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

            entities = referral_repository.query_referrals(
                pseudonym=str(pseudonym) if pseudonym else None,
                data_domain=str(data_domain) if data_domain else None,
                ura_number=str(ura_number),
            )
            if not entities:
                raise HTTPException(status_code=404)
            return [ReferralEntry.from_entity(e) for e in entities]
