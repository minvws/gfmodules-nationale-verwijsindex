from typing import Sequence, cast

from sqlalchemy import select

from app.db.decorator import repository
from app.db.models.ura_number_allowlist import UraNumberAllowlistEntity
from app.db.repository.respository_base import RepositoryBase
from app.db.session import DbSession


@repository(UraNumberAllowlistEntity)
class UraNumberAllowlistRepository(RepositoryBase):
    def __init__(self, db_session: DbSession):
        super().__init__(db_session)

    def get_all(self) -> Sequence[UraNumberAllowlistEntity]:
        stmt = select(UraNumberAllowlistEntity)
        results = self.db_session.execute(stmt).scalars().all()
        return results

        return cast(
            Sequence[UraNumberAllowlistEntity],
            self.db_session.execute(select(UraNumberAllowlistEntity)).scalars().all(),
        )
