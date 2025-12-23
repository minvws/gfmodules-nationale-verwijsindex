from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.decorator import repository
from app.db.models.oauth_token import OAuthTokenEntity
from app.db.repository.respository_base import RepositoryBase


@repository(OAuthTokenEntity)
class OAuthRepository(RepositoryBase):
    def get_by_token_sha256(self, token_hash: str) -> OAuthTokenEntity | None:
        stmt = select(OAuthTokenEntity).where(
            OAuthTokenEntity.token_sha256 == token_hash,
        )
        result = self.db_session.execute(stmt).scalars().first()
        return result

    def update_one(self, entity: OAuthTokenEntity) -> OAuthTokenEntity:
        try:
            self.db_session.merge(entity)
            self.db_session.commit()
            return entity
        except SQLAlchemyError as exc:
            self.db_session.rollback()
            raise exc

    def add_one(self, entity: OAuthTokenEntity) -> OAuthTokenEntity:
        try:
            self.db_session.add(entity)
            self.db_session.commit()
            return entity
        except SQLAlchemyError as exc:
            self.db_session.rollback()
            raise exc

    def delete_one(self, entity: OAuthTokenEntity) -> None:
        try:
            self.db_session.delete(entity)
            self.db_session.commit()
        except SQLAlchemyError as exc:
            self.db_session.rollback()
            raise exc
