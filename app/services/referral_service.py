from typing import List

from fastapi.exceptions import HTTPException
from app.data import Pseudonym, DataDomain, UraNumber
from app.db.db import Database
from app.db.models.referral import ReferralEntity
from app.db.repository.referral_repository import ReferralRepository
from app.response_models.referrals import ReferralEntry


class ReferralService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_referrals_by_domain_and_pseudonym(
        self, pseudonym: Pseudonym, data_domain: DataDomain
    ) -> List[ReferralEntry]:
        """
        Method that gets all the referrals by pseudonym and data domain
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)
            entities = referral_repository.query_referrals(pseudonym=pseudonym,data_domain=data_domain, ura_number=None)
            if not entities:
                raise HTTPException(status_code=404)
            return [self.hydrate_referral(entity) for entity in entities]

    def add_one_referral(
        self, pseudonym: Pseudonym, data_domain: DataDomain, ura_number: UraNumber
    ) -> ReferralEntry:
        """
        Method that adds a referral to the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)
            referral_entity = ReferralEntity(
                pseudonym=str(pseudonym),
                data_domain=str(data_domain),
                ura_number=str(ura_number),
            )
            return self.hydrate_referral(referral_repository.add_one(referral_entity))

    def delete_one_referral(
        self, pseudonym: Pseudonym, data_domain: DataDomain, ura_number: UraNumber
    ) -> None:
        """
        Method that removes a referral from the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)
            referral = referral_repository.find_one(pseudonym=pseudonym, data_domain=data_domain, ura_number=ura_number)
            if referral is None:
                raise HTTPException(status_code=404)

            return referral_repository.delete_one(referral)


    def query_referrals(
        self, pseudonym: Pseudonym | None, data_domain: DataDomain | None, ura_number: UraNumber
    ) -> List[ReferralEntry]:
        """
        Method that removes a referral from the database
        """
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRepository)
            entities = referral_repository.query_referrals(pseudonym=pseudonym, data_domain=data_domain, ura_number=ura_number)
            if not entities:
                raise HTTPException(status_code=404)
            return [self.hydrate_referral(entity) for entity in entities]


    @staticmethod
    def hydrate_referral(entity: ReferralEntity) -> ReferralEntry:
        data_domain = DataDomain.from_str(entity.data_domain)
        if data_domain is None:
            raise ValueError("Invalid data domain")

        return ReferralEntry(
            ura_number=UraNumber(entity.ura_number),
            pseudonym=Pseudonym(entity.pseudonym),
            data_domain=data_domain,
        )
