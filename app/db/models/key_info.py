from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, cast
from uuid import UUID, uuid4

from sqlalchemy import (
    TIMESTAMP,
    SQLColumnExpression,
    String,
    exists,
    text,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.models.base import Base

if TYPE_CHECKING:
    from app.db.models.referral import ReferralEntity


class KeyInfoEntity(Base):
    __tablename__ = "keys_info"

    id: Mapped[UUID] = mapped_column("id", Uuid, primary_key=True, default=uuid4)
    label: Mapped[str] = mapped_column("label", String, unique=True)
    mechanism: Mapped[str] = mapped_column("mechanism", String)
    created_at: Mapped[datetime] = mapped_column("created_at", TIMESTAMP, default=datetime.now)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        "deleted_at",
        TIMESTAMP,
    )

    referrals: Mapped[List["ReferralEntity"]] = relationship(back_populates="key_info")

    @hybrid_property
    def has_referrals(self) -> bool:
        return len(self.referrals) > 0

    @has_referrals.inplace.expression
    @classmethod
    def _has_referrals(cls) -> SQLColumnExpression[bool]:
        return cast(
            SQLColumnExpression[bool],
            exists()  # plain text sql is used here to mitigate python circular imports
            .where(text("referrals.key_info_id = key_infos.id"))
            .where(text("referrals.is_deleted = False"))
            .select_from(text("referrals"))
            .scalar_subquery(),
        )
