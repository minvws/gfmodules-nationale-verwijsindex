from typing import Sequence

from sqlalchemy import select, insert, delete

from app.data import UraNumber, DataDomain, Pseudonym
from app.db.decorator import repository
from app.db.models.referral import ReferralEntity
from app.db.repository.respository_base import RepositoryBase


@repository(ReferralEntity)
class ReferralRepository(RepositoryBase):
    def find_many_referrals(
        self, pseudonym: Pseudonym, data_domain: DataDomain
    ) -> Sequence[ReferralEntity]:
        """
        find many referrals with pseudonym and data domain
        """
        stmt = (
            select(ReferralEntity)
            .where(ReferralEntity.pseudonym == str(pseudonym))
            .where(ReferralEntity.data_domain == str(data_domain))
        )
        return self.db_session.execute(stmt).scalars().all()    # type: ignore

    def add_one(self, pseudonym: Pseudonym, data_domain: DataDomain, ura_number: UraNumber) -> bool:
        stmt = insert(ReferralEntity).values(
            pseudonym=str(pseudonym), data_domain=str(data_domain), ura_number=str(ura_number)
        )
        result = self.db_session.execute(stmt)
        self.db_session.commit()
        if result.rowcount == 1:
            return True
        return False

    def delete_one(self, pseudonym: Pseudonym, data_domain: DataDomain, ura_number: UraNumber) -> bool:
        stmt = (
            delete(ReferralEntity)
            .where(ReferralEntity.pseudonym == str(pseudonym))
            .where(ReferralEntity.data_domain == str(data_domain))
            .where(ReferralEntity.ura_number == str(ura_number))
        )
        result = self.db_session.execute(stmt)
        self.db_session.commit()
        if result.rowcount == 0:
            return False
        return True
