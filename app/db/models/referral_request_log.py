from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.data_models.logging import ReferralRequestType
from app.db.models.base import Base


class ReferralRequestLogEntry(Base):
    __tablename__ = "referral_request_logs"

    id: Mapped[int] = mapped_column("id", primary_key=True, autoincrement=True)
    endpoint: Mapped[str] = mapped_column("endpoint", String)

    request_type: Mapped[ReferralRequestType]
    payload: Mapped[dict[str, Any]] = mapped_column("payload", JSON)

    ura_number: Mapped[str] = mapped_column("ura_number", String)
    requesting_uzi_number: Mapped[str] = mapped_column("requesting_uzi_number", String)
