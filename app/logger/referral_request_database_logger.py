from app.db.repository.referral_request_logging_repository import (
    ReferralRequestLoggingRepository,
)
from app.db.session import DbSession
from app.referral_request_payload import ReferralLoggingPayload

from app.referral_request_logger import ReferralRequestLogger


class ReferralRequestDatabaseLogger(ReferralRequestLogger):
    _database_session: DbSession

    def __init__(self, database_session: DbSession) -> None:
        self._database_session = database_session

    def log(self, referral: ReferralLoggingPayload) -> None:
        repo = ReferralRequestLoggingRepository(self._database_session)
        repo.add_one(referral)

    def log_query(self, referral: ReferralLoggingPayload) -> None:
        return self.log(referral)
