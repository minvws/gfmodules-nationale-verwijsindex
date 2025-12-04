from typing import List

from sqlalchemy import exists, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.decorator import repository
from app.db.models.referral import ReferralEntity
from app.db.repository.respository_base import RepositoryBase


@repository(ReferralEntity)
class ReferralRepository(RepositoryBase):
    def find_one(self, pseudonym: str, data_domain: str, ura_number: str) -> ReferralEntity | None:
        stmt = select(ReferralEntity).where(
            ReferralEntity.ura_number == str(ura_number),
            ReferralEntity.data_domain == str(data_domain),
            ReferralEntity.pseudonym == str(pseudonym),
        )
        result = self.db_session.execute(stmt).scalars().first()
        if result is None:
            return None
        if isinstance(result, ReferralEntity):
            return result
        raise TypeError("Result not of type ReferralEntity")

    def query_referrals(
        self,
        pseudonym: str | None = None,
        data_domain: str | None = None,
        ura_number: str | None = None,
    ) -> List[ReferralEntity]:
        stmt = select(ReferralEntity)

        if ura_number is not None:
            stmt = stmt.where(ReferralEntity.ura_number == ura_number)

        if pseudonym is not None:
            stmt = stmt.where(ReferralEntity.pseudonym == pseudonym)

        if data_domain is not None:
            stmt = stmt.where(ReferralEntity.data_domain == data_domain)

        result = self.db_session.execute(stmt).scalars().all()
        if isinstance(result, List):
            return result
        raise TypeError("Result not of type ReferralEntity")

    def add_one(self, referral_entity: ReferralEntity) -> ReferralEntity:
        try:
            self.db_session.add(referral_entity)
            self.db_session.commit()
            return referral_entity
        except SQLAlchemyError as exc:
            self.db_session.rollback()
            raise exc

    def delete_one(self, referral_entity: ReferralEntity) -> None:
        try:
            self.db_session.delete(referral_entity)
            self.db_session.commit()
        except SQLAlchemyError as exc:
            self.db_session.rollback()
            raise exc

    def exists(self, pseudonym: str, data_domain: str, ura_number: str) -> bool:
        stmt = select(
            exists().where(
                ReferralEntity.pseudonym == pseudonym,
                ReferralEntity.data_domain == data_domain,
                ReferralEntity.ura_number == ura_number,
            )
        )
        results = self.db_session.session.execute(stmt).scalar()
        return results or False
