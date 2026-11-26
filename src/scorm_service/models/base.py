from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


def bay_gio() -> datetime:
    return datetime.now(UTC)  # luu gio UTC theo ho so


class Base(DeclarativeBase):
    pass