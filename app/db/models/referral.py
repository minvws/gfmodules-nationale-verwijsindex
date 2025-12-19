from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class ReferralEntity(Base):
    __tablename__ = "referrals"

    ura_number: Mapped[str] = mapped_column("ura_number", String, primary_key=True)
    pseudonym: Mapped[str] = mapped_column("pseudonym", String, primary_key=True)
    data_domain: Mapped[str] = mapped_column("data_domain", String, primary_key=True)
    organization_type: Mapped[Optional[str]] = mapped_column("organization_type", String, nullable=True)

    def __repr__(self) -> str:
        return f"<ReferralEntity(ura_number={self.ura_number}, pseudonym={self.pseudonym}, data_domain={self.data_domain}, organization_type={self.organization_type}>"
