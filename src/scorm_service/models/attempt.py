from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, bay_gio

if TYPE_CHECKING:
    from .sco_state import ScoState


class Attempt(Base):
    __tablename__ = "attempts"
    # mot nguoi chi co mot attempt tren mot phien ban goi
    __table_args__ = (UniqueConstraint("person_code", "package_version_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    person_code: Mapped[str] = mapped_column(ForeignKey("people.person_code"))
    package_version_id: Mapped[int] = mapped_column(ForeignKey("package_versions.id"))
    status: Mapped[str] = mapped_column(String(20), default="not attempted")
    score_raw: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    score_max: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=bay_gio)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sco_states: Mapped[list["ScoState"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )