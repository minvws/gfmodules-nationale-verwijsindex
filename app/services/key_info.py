import logging
from datetime import datetime
from typing import List

from app.db.db import Database
from app.db.models.key_info import KeyInfoEntity
from app.db.repository.key_info_repository import KeyInfoRepository
from app.services.exceptions import (
    ConflictError,
    ForbiddedError,
    InvalidKeyInfoError,
    NotFoundError,
)

logger = logging.Logger(__name__)


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

    def get_active_key(self) -> KeyInfoEntity:
        with self.database.get_db_session() as session:
            repo = session.get_repository(KeyInfoRepository)
            active_key_info = repo.find_active()
            if len(active_key_info) != 1:
                logger.debug("Only one active KeyInfo is allowed, check database to fix issue")
                raise InvalidKeyInfoError()

            return active_key_info[0]

    def get_one_or_none(self, label: str) -> KeyInfoEntity | None:
        with self.database.get_db_session() as session:
            repo = session.get_repository(KeyInfoRepository)
            return repo.find_one(label)

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
