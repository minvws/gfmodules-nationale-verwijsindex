from typing import Any, List, Sequence

from sqlalchemy import and_, exists, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.decorator import repository
from app.db.models.key_info import KeyInfoEntity
from app.db.repository.respository_base import RepositoryBase


@repository(KeyInfoEntity)
class KeyInfoRepository(RepositoryBase):
    def find_one(self, label: str) -> KeyInfoEntity | None:
        stmt = select(KeyInfoEntity).where(and_(KeyInfoEntity.label == label, KeyInfoEntity.deleted_at.is_(None)))
        result = self.db_session.session.execute(stmt).scalar()
        return result

    def add_one(self, key_info: KeyInfoEntity) -> KeyInfoEntity:
        try:
            self.db_session.add(key_info)
            self.db_session.commit()
            return key_info
        except SQLAlchemyError as exc:
            self.db_session.rollback()
            raise exc

    def find_many(self, mechanism: str | None = None) -> Sequence[KeyInfoEntity]:
        conditions: List[Any] = [KeyInfoEntity.deleted_at.is_(None)]
        stmt = select(KeyInfoEntity)
        if mechanism:
            conditions.append(KeyInfoEntity.mechanism == mechanism)

        stmt = stmt.where(and_(*conditions))
        results = self.db_session.execute(stmt).scalars().all()
        return results

    def exists(self, label: str) -> bool:
        stmt = select(exists().where(and_(KeyInfoEntity.label == label, KeyInfoEntity.deleted_at.is_(None))))
        result = self.db_session.execute(stmt).scalar()
        return result or False
