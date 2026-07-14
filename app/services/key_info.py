from datetime import datetime
from typing import List

from app.db.db import Database
from app.db.models.key_info import KeyInfoEntity
from app.db.repository.key_info_repository import KeyInfoRepository
from app.services.exceptions import ConflictError, ForbiddedError, NotFoundError


class KeyInfoService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_one(self, label: str) -> KeyInfoEntity:
        with self.database.get_db_session() as session:
            repo = session.get_repository(KeyInfoRepository)
            key_info = repo.find_one(label)

            if key_info is None:
                raise NotFoundError

            return key_info

    def get_many(self, mechanism: str | None = None) -> List[KeyInfoEntity]:
        with self.database.get_db_session() as session:
            repo = session.get_repository(KeyInfoRepository)
            return list(repo.find_many(mechanism))

    def add_one(self, label: str, mechanism: str) -> KeyInfoEntity:
        with self.database.get_db_session() as session:
            repo = session.get_repository(KeyInfoRepository)
            if repo.exists(label):
                raise ConflictError()

            new_key_info = repo.add_one(KeyInfoEntity(label=label, mechanism=mechanism))

            return new_key_info

    def delete_one(self, label: str) -> None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(KeyInfoRepository)
            target = repo.find_one(label=label)

            if target is None:
                raise NotFoundError()

            if target.has_referrals:
                raise ForbiddedError("Key label has referrals associated with it")

            target.deleted_at = datetime.now()
            session.add(target)
            session.commit()
