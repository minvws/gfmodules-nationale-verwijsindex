from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, delete, exists, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.decorator import repository
from app.db.models.referral import ReferralEntity
from app.db.repository.respository_base import RepositoryBase


@repository(ReferralEntity)
class ReferralRepository(RepositoryBase):
    def find_one(self, pseudonym: str, ura_number: str, source: str) -> ReferralEntity | None:
        stmt = select(ReferralEntity).where(
            ReferralEntity.ura_number == str(ura_number),
            ReferralEntity.pseudonym == str(pseudonym),
            ReferralEntity.source == str(source),
        )
        result = self.db_session.execute(stmt).scalars().first()
        return result

    def find_by_id(self, id: UUID) -> ReferralEntity | None:
        stmt = select(ReferralEntity).where(ReferralEntity.id == id)
        results = self.db_session.execute(stmt).scalars().first()
        return results

    def find_many(
        self,
        pseudonym: str | None = None,
        ura_number: str | None = None,
        source: str | None = None,
    ) -> Sequence[ReferralEntity]:
        stmt = select(ReferralEntity)

        if ura_number is not None:
            stmt = stmt.where(ReferralEntity.ura_number == ura_number)

        if pseudonym is not None:
            stmt = stmt.where(ReferralEntity.pseudonym == pseudonym)

        if source is not None:
            stmt = stmt.where(ReferralEntity.source == source)

        results = self.db_session.execute(stmt).scalars().all()
        return results

    def delete_many(
        self,
        ura_number: str,
        pseudonym: str | None = None,
        source: str | None = None,
        id: str | UUID | None = None,
    ) -> int:
        stmt = delete(ReferralEntity)

        stmt = stmt.where(ReferralEntity.ura_number == ura_number)

        if pseudonym is not None:
            stmt = stmt.where(ReferralEntity.pseudonym == pseudonym)

        if source is not None:
            stmt = stmt.where(ReferralEntity.source == source)

        if id is not None:
            stmt = stmt.where(ReferralEntity.id == id)

        results = self.db_session.delete_stmt(stmt)  # type: ignore

        return results.rowcount  # type: ignore

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

    def delete(
        self,
        ura_number: str,
        pseudonym: str | None = None,
        source: str | None = None,
    ) -> None:
        try:
            stmt = delete(ReferralEntity).where(ReferralEntity.ura_number == ura_number)
            if pseudonym:
                stmt = stmt.where(ReferralEntity.pseudonym == pseudonym)

            if source:
                stmt = stmt.where(ReferralEntity.source == source)

            self.db_session.delete_stmt(stmt)
            self.db_session.commit()
        except SQLAlchemyError as exc:
            self.db_session.rollback()
            raise exc

    def exists(
        self,
        ura_number: str,
        pseudonym: str | None = None,
        source: str | None = None,
    ) -> bool:
        conditions = [ReferralEntity.ura_number == ura_number]
        if pseudonym:
            conditions.append((ReferralEntity.pseudonym == pseudonym))

        if source:
            conditions.append((ReferralEntity.source == source))

        stmt = select(exists().where(and_(*conditions)))

        results = self.db_session.execute(stmt).scalar()
        return results or False
