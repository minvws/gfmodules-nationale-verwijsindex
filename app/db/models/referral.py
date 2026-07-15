from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.models.base import Base

if TYPE_CHECKING:
    from app.db.models.key_info import KeyInfoEntity


class ReferralEntity(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        UniqueConstraint(
            "ura_number",
            "pseudonym",
            "source",
            name="providers_unique_idx",
        ),
    )

    id: Mapped[UUID] = mapped_column("id", Uuid, primary_key=True, default=uuid4)
    ura_number: Mapped[str] = mapped_column("ura_number", String)
    pseudonym: Mapped[str] = mapped_column("pseudonym", String)
    source: Mapped[str] = mapped_column("source", String)
    organization_type: Mapped[Optional[str]] = mapped_column("organization_type", String)
    key_id: Mapped[UUID] = mapped_column("key_id", Uuid, ForeignKey("keys_info.id"))
    created_at: Mapped[datetime] = mapped_column("created_at", TIMESTAMP, default=datetime.now)

    key_info: Mapped["KeyInfoEntity"] = relationship(back_populates="referrals")
