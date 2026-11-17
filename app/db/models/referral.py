from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.models.base import Base
from app.db.models.organization import OrganizationEntity

if TYPE_CHECKING:
    from app.db.models.key_info import KeyInfoEntity


class ReferralEntity(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        Index("referrals_organization_pseudonym_source_key", "organization_id", "pseudonym", "source", unique=True),
        Index("referrals_pseudonym_idx", "pseudonym"),
        Index("referrals_organization_created_at_id_idx", "organization_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column("id", Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column("organization_id", Uuid, ForeignKey(OrganizationEntity.id))
    pseudonym: Mapped[str] = mapped_column("pseudonym", String)
    source: Mapped[str] = mapped_column("source", String)
    key_id: Mapped[UUID] = mapped_column("key_id", Uuid, ForeignKey("keys_info.id"))
    created_at: Mapped[datetime] = mapped_column("created_at", TIMESTAMP, default=datetime.now)

    key_info: Mapped["KeyInfoEntity"] = relationship(back_populates="referrals")
    # Loaded eagerly: referrals are used after their session is closed, and every response carries the URA number
    organization: Mapped[OrganizationEntity] = relationship(lazy="joined", innerjoin=True)

    @property
    def ura_number(self) -> str:
        return self.organization.external_id
