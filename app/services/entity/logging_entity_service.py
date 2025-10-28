import logging

from app.data_models.logging import ReferralLoggingPayload
from app.db.db import Database
from app.db.repository.referral_request_logging_repository import ReferralRequestLoggingRepository

logger = logging.getLogger(__name__)


class LoggingEntityService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def log(self, log: ReferralLoggingPayload) -> None:
        with self.database.get_db_session() as session:
            referral_repository = session.get_repository(ReferralRequestLoggingRepository)
            try:
                referral_repository.add_one(log)
            except Exception as exc:
                logger.error(f"Failed to log referral: {exc}")
