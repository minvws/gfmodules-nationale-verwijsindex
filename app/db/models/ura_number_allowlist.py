from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.data import UraNumber
from app.db.models.base import Base


class UraNumberAllowlistEntity(Base):
    __tablename__ = "ura_number_allowlist"

    _ura_number: Mapped[str] = mapped_column("ura_number", String, primary_key=True)
    description: Mapped[str | None] = mapped_column("description", String)

    def __init__(self, ura_number: UraNumber, description: str | None = None):
        super().__init__()
        self._ura_number = str(ura_number)
        self.description = description

    @property
    def ura_number(self) -> UraNumber:
        return UraNumber(self._ura_number)

    @ura_number.setter
    def ura_number(self, value: UraNumber) -> None:
        self._ura_number = str(value)

    def __repr__(self) -> str:
        return f"<UraNumberAllowlistEntity(ura_number={self.ura_number}, description={self.description})>)"
