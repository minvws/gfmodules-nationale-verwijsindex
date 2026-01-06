import uuid

from sqlalchemy import Boolean, DateTime, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class OAuthTokenEntity(Base):
    __tablename__ = "oauth_tokens"

    id: Mapped[uuid.UUID] = mapped_column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    ura_number: Mapped[str] = mapped_column(String(8), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    scopes: Mapped[str] = mapped_column(String, nullable=False, server_default=text("''"))
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<OAuthTokenEntity(id={self.id}, ura_number={self.ura_number}, "
            f"revoked={self.revoked}, scopes={self.scopes!r}, "
            f"expires_at={self.expires_at!r}, created_at={self.created_at!r})>"
        )
