import logging
import time
from functools import cached_property
from typing import List

from fastapi.exceptions import HTTPException
from starlette.requests import Request

from app.db.db import Database
from app.db.repository.ura_number_allowlist_repository import (
    UraNumberAllowlistRepository,
)
from app.models.ura import UraNumber
from app.ura.ura_middleware.ura_middleware import UraMiddleware

logger = logging.getLogger(__name__)


class AllowlistedUraMiddleware(UraMiddleware):
    def __init__(
        self,
        db: Database,
        ura_middleware: UraMiddleware,
        allowlist_cache_in_seconds: int,
    ):
        self._db = db
        self._ura_middleware = ura_middleware
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

    def _validate(self, ura_number: UraNumber) -> UraNumber:
        if ura_number not in self.allowlist:
            logger.debug(f"URA with ura_number(str({ura_number})) is not in the allowlist")
            raise HTTPException(status_code=403, detail="URA number not in allowlist")
        return ura_number

    def authenticated_ura(self, request: Request) -> UraNumber:
        return self._validate(self._ura_middleware.authenticated_ura(request))
