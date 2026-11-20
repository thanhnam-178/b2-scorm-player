from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


def bay_gio() -> datetime:
    return datetime.now(timezone.utc)  # luu gio UTC theo ho so


class Base(DeclarativeBase):
    pass