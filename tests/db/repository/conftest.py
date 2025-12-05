import pytest

from app.db.db import Database
from app.db.repository.referral_repository import ReferralRepository


@pytest.fixture()
def referrals_repo(database: Database) -> ReferralRepository:
    return ReferralRepository(db_session=database.get_db_session())
