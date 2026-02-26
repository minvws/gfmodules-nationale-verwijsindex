from uuid import UUID, uuid4

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.models.base import Base


class ReferralEntity(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        UniqueConstraint(
            "ura_number",
            "pseudonym",
            "data_domain",
            "source",
            name="providers_unique_idx",
        ),
    )

    id: Mapped[UUID] = mapped_column("id", Uuid, primary_key=True, default=uuid4)
    ura_number: Mapped[str] = mapped_column("ura_number", String)
    pseudonym: Mapped[str] = mapped_column("pseudonym", String)
    data_domain: Mapped[str] = mapped_column("data_domain", String)
    source: Mapped[str] = mapped_column("source", String)
    organization_type: Mapped[str] = mapped_column("organization_type", String)

    def __repr__(self) -> str:
        return f"<ReferralEntity(ura_number={self.ura_number}, pseudonym={self.pseudonym}, data_domain={self.data_domain}, source={self.source}, organization_type={self.organization_type}>"
