import logging
import time
from functools import cached_property
from typing import List

from fastapi.exceptions import HTTPException

from app.db.db import Database
from app.db.repository.ura_number_allowlist_repository import (
    UraNumberAllowlistRepository,
)
from app.models.ura import UraNumber

logger = logging.getLogger(__name__)


class AllowlistedUraMiddleware:
    def __init__(
        self,
        db: Database,
        allowlist_cache_in_seconds: int,
    ):
        self._db = db
        self._cached = 0.0
        self._allowlist_cache_in_seconds = allowlist_cache_in_seconds

    @cached_property
    def __allowlist(self) -> List[UraNumber]:
        logger.debug("Initializing allowlist from DB")
        self._cached = time.time()
        with self._db.get_db_session() as db_session:
            allowlist_repository = db_session.get_repository(UraNumberAllowlistRepository)
            return [entry.ura_number for entry in allowlist_repository.get_all()]

    @property
    def allowlist(self) -> List[UraNumber]:
        allowlist = self.__allowlist
        if time.time() - self._cached > self._allowlist_cache_in_seconds:
            logger.debug("Allowlist expired. Clear allowlist and reinitialize")
            del self.__dict__["_AllowlistedUraMiddleware__allowlist"]
            allowlist = self.__allowlist
        return allowlist

    def filter(self, ura_number: UraNumber) -> UraNumber:
        if ura_number not in self.allowlist:
            logger.debug(f"URA with ura_number(str({ura_number})) is not in the allowlist")
            raise HTTPException(status_code=403, detail="URA number not in allowlist")
        return ura_number
