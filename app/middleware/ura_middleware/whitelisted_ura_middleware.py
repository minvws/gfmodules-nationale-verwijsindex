import logging
import time
from functools import cached_property
from typing import List

from fastapi.exceptions import HTTPException
from starlette.requests import Request

from app.data import UraNumber
from app.db.db import Database
from app.db.repository.ura_number_whitelist_repository import UraNumberWhitelistRepository
from app.middleware.ura_middleware.ura_middleware import UraMiddleware

logger = logging.getLogger(__name__)


class WhitelistedUraMiddleware(UraMiddleware):
    def __init__(self, db: Database, ura_middleware: UraMiddleware, whitelist_cache_in_seconds: int):
        self._db = db
        self._ura_middleware = ura_middleware
        self._cached = 0.0
        self._whitelist_cache_in_seconds = whitelist_cache_in_seconds

    @cached_property
    def __whitelist(self) -> List[UraNumber]:
        logger.debug("Initializing whitelist from DB")
        self._cached = time.time()
        with self._db.get_db_session() as db_session:
            whitelist_repository = db_session.get_repository(UraNumberWhitelistRepository)
            return [entry.ura_number for entry in whitelist_repository.get_all()]

    @property
    def whitelist(self) -> List[UraNumber]:
        whitelist = self.__whitelist
        if time.time() - self._cached > self._whitelist_cache_in_seconds:
            logger.debug("Whitelist expired. Clear whitelist and reinitialize")
            del self.__dict__["__whitelist"]
            whitelist = self.__whitelist
        return whitelist

    def _validate(self, ura_number: UraNumber) -> UraNumber:
        if ura_number not in self.whitelist:
            logger.debug(f"URA with ura_number(str({ura_number})) is not in the whitelist")
            raise HTTPException(status_code=403, detail="URA number not in whitelist")
        return ura_number

    def authenticated_ura(self, request: Request) -> UraNumber:
        return self._validate(self._ura_middleware.authenticated_ura(request))
