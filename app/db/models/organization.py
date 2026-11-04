from datetime import datetime
from uuid import UUID

from sqlalchemy import TIMESTAMP, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.models.base import Base


class OrganizationEntity(Base):
    """
    Organizations managed by the nvi-beheer-api. NVI only reads this table.
    """

    __tablename__ = "organizations"
    __table_args__ = ({"schema": "admin"},)

    id: Mapped[UUID] = mapped_column("id", Uuid, primary_key=True)
    external_id: Mapped[str] = mapped_column("external_id", String)
    deleted_at: Mapped[datetime | None] = mapped_column("deleted_at", TIMESTAMP)
