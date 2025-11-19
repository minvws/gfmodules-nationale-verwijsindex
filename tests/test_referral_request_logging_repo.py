from unittest import TestCase

from sqlalchemy import func, select

from app.data import ReferralRequestType
from app.db.db import Database
from app.db.models.referral_request_log import ReferralRequestLogEntry
from app.db.repository.referral_request_logging_repository import (
    ReferralRequestLoggingRepository,
)
from app.db.session import DbSession
from app.models.referrals import ReferralLoggingPayload
from app.models.ura import UraNumber
from tests.test_config import get_test_config

TESTING_URA = UraNumber(123)


class ReferralRequestLoggingRepositoryTest(TestCase):
    _repo: ReferralRequestLoggingRepository
    _session: DbSession

    def setUp(self) -> None:
        config = get_test_config()
        self._db = Database(config.database)
        self._db.generate_tables()

        with self._db.get_db_session() as session:
            self._session = session

    def test_add(self):
        logging_payload = ReferralLoggingPayload(
            endpoint="https://test",
            requesting_uzi_number="123",
            ura_number=TESTING_URA,
            request_type=ReferralRequestType.CREATE,
            payload={},
        )

        repo = ReferralRequestLoggingRepository(self._session)
        repo.add_one(logging_payload)

        statement = select(func.count(ReferralRequestLogEntry.id))
        count = self._session.session.execute(statement).scalar()

        assert count == 1
