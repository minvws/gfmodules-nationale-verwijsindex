from sqlalchemy import insert

from app.data_models.logging import ReferralLoggingPayload
from app.db.decorator import repository
from app.db.models.referral_request_log import ReferralRequestLogEntry
from app.db.repository.respository_base import RepositoryBase


@repository(ReferralRequestLogEntry)
class ReferralRequestLoggingRepository(RepositoryBase):
    def add_one(self, payload: ReferralLoggingPayload) -> None:
        stmt = insert(ReferralRequestLogEntry).values(
            ura_number=str(payload.requesting_ura_number),
            requesting_uzi_number=payload.requesting_uzi_number,
            endpoint=payload.endpoint,
            request_type=payload.request_type,
            payload=payload.payload,
        )
        self.db_session.execute(stmt)
        self.db_session.commit()
