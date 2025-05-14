from typing import Sequence, cast

from sqlalchemy import select

from app.db.decorator import repository
from app.db.models.ura_number_whitelist import UraNumberWhitelistEntity
from app.db.repository.respository_base import RepositoryBase
from app.db.session import DbSession


@repository(UraNumberWhitelistEntity)
class UraNumberWhitelistRepository(RepositoryBase):
    def __init__(self, db_session: DbSession):
        super().__init__(db_session)

    def get_all(self) -> Sequence[UraNumberWhitelistEntity]:
        return cast(
            Sequence[UraNumberWhitelistEntity],
            self.db_session.execute(select(UraNumberWhitelistEntity)).scalars().all(),
        )
