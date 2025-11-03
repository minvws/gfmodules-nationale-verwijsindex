import logging
from typing import List

from fastapi import HTTPException

from app.data import DataDomain, Pseudonym, UraNumber
from app.data_models.referrals import ReferralEntry
from app.db.db import Database
from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository

logger = logging.getLogger(__name__)


class ReferralEntityService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def add_one_referral(
        self,
        pseudonym: Pseudonym,
        data_domain: DataDomain,
        ura_number: UraNumber,
        encrypted_lmr_id: str,
    ) -> ReferralEntry:
        """
        Method that adds a referral to the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)
            if (
                referral_repository.find_one(pseudonym=pseudonym, data_domain=data_domain, ura_number=ura_number)
                is not None
            ):
                logger.info(
                    f"Referral already exists for pseudonym {str(pseudonym)}, data domain {str(data_domain)}, and URA number {str(ura_number)}"
                )
                raise HTTPException(status_code=409)

            referral_entity = ReferralEntity(
                pseudonym=str(pseudonym),
                data_domain=str(data_domain),
                ura_number=str(ura_number),
                encrypted_lmr_id=encrypted_lmr_id,
            )
            return self.hydrate_referral(referral_repository.add_one(referral_entity))

    def delete_one_referral(
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
            referral = referral_repository.find_one(pseudonym=pseudonym, data_domain=data_domain, ura_number=ura_number)
            if referral is None:
                logger.info("Referral not found")
                raise HTTPException(status_code=404)

            referral_repository.delete_one(referral)

    def query_referrals(
        self,
        pseudonym: Pseudonym | None = None,
        data_domain: DataDomain | None = None,
        ura_number: UraNumber | None = None,
    ) -> List[ReferralEntry]:
        """
        Method that queries referrals from the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)

            entities = referral_repository.query_referrals(
                pseudonym=pseudonym,
                data_domain=data_domain,
                ura_number=ura_number,
            )
            if not entities:
                logger.info("No referrals found")
                raise HTTPException(status_code=404)
            return [self.hydrate_referral(entity) for entity in entities]

    @staticmethod
    def hydrate_referral(entity: ReferralEntity) -> ReferralEntry:
        data_domain = entity.data_domain
        if data_domain is None:
            raise ValueError("Invalid data domain")

        return ReferralEntry(
            ura_number=UraNumber(entity.ura_number),
            pseudonym=Pseudonym(value=entity.pseudonym),
            data_domain=DataDomain(value=data_domain),
            encrypted_lmr_id=entity.encrypted_lmr_id,
        )
