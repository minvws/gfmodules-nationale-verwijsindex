from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.data import UraNumber
from app.db.models.base import Base


class UraNumberWhitelistEntity(Base):
    __tablename__ = "ura_number_whitelist"

    _ura_number: Mapped[str] = mapped_column("ura_number", String, primary_key=True)

    def __init__(self, ura_number: UraNumber):
        super().__init__()
        self._ura_number = str(ura_number)

    @property
    def ura_number(self) -> UraNumber:
        return UraNumber(self._ura_number)

    @ura_number.setter
    def ura_number(self, value: UraNumber) -> None:
        self._ura_number = str(value)

    def __repr__(self) -> str:
        return f"<UraNumberWhitelistEntity(ura_number={self.ura_number})"
