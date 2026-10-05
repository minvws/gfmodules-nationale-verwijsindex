from typing import TypeVar

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    def __repr__(self) -> str:
        props = ", ".join([f"{c.key}={self.__getattribute__(c.key)}" for c in self.__table__.columns])

        return f"<{self.__class__.__name__}=({props})>"


TBase = TypeVar("TBase", bound=Base)
