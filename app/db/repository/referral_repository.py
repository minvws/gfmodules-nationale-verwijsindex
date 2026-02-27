from typing import List, Sequence
from uuid import UUID

from sqlalchemy import and_, delete, exists, or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.decorator import repository
from app.db.models.referral import ReferralEntity
from app.db.repository.respository_base import RepositoryBase


@repository(ReferralEntity)
class ReferralRepository(RepositoryBase):
    def find_one(self, pseudonym: str, data_domain: str, ura_number: str, source: str) -> ReferralEntity | None:
        stmt = select(ReferralEntity).where(
            ReferralEntity.ura_number == str(ura_number),
            ReferralEntity.data_domain == str(data_domain),
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
        data_domain: str | None = None,
        ura_number: str | None = None,
        source: str | None = None,
        organization_type: str | None = None,
    ) -> Sequence[ReferralEntity]:
        stmt = select(ReferralEntity)

        if ura_number is not None:
            stmt = stmt.where(ReferralEntity.ura_number == ura_number)

        if pseudonym is not None:
            stmt = stmt.where(ReferralEntity.pseudonym == pseudonym)

        if data_domain is not None:
            stmt = stmt.where(ReferralEntity.data_domain == data_domain)

        if source is not None:
            stmt = stmt.where(ReferralEntity.source == source)

        if organization_type is not None:
            stmt = stmt.where(ReferralEntity.organization_type == organization_type)

        results = self.db_session.execute(stmt).scalars().all()
        return results

    def find(
        self,
        pseudonym: str,
        data_domain: str,
        org_types: List[str] = [],
    ) -> Sequence[ReferralEntity]:
        stmt = select(ReferralEntity).where(
            ReferralEntity.pseudonym == pseudonym,
            ReferralEntity.data_domain == data_domain,
        )

        org_filter_condition = []
        for t in org_types:
            org_filter_condition.append(ReferralEntity.organization_type == t)

        if len(org_filter_condition) > 0:
            stmt = stmt.where(or_(*org_filter_condition))

        results = self.db_session.execute(stmt).scalars().all()

        return results

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
        data_domain: str | None = None,
        source: str | None = None,
    ) -> None:
        try:
            stmt = delete(ReferralEntity).where(ReferralEntity.ura_number == ura_number)
            if pseudonym:
                stmt = stmt.where(ReferralEntity.pseudonym == pseudonym)

            if data_domain:
                stmt = stmt.where(ReferralEntity.data_domain == data_domain)

            if source:
                stmt = stmt.where(ReferralEntity.source == source)

            self.db_session.session.execute(stmt)
            self.db_session.commit()
        except SQLAlchemyError as exc:
            self.db_session.rollback()
            raise exc

    def exists(
        self,
        ura_number: str,
        pseudonym: str | None = None,
        data_domain: str | None = None,
        source: str | None = None,
    ) -> bool:
        conditions = [(ReferralEntity.ura_number == ura_number)]
        if pseudonym:
            conditions.append((ReferralEntity.pseudonym == pseudonym))

        if data_domain:
            conditions.append((ReferralEntity.data_domain == data_domain))

        if source:
            conditions.append((ReferralEntity.source == source))

        stmt = select(exists().where(and_(*conditions)))

        results = self.db_session.session.execute(stmt).scalar()
        return results or False
