from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, bay_gio

if TYPE_CHECKING:
    from .attempt import Attempt


class ScoState(Base):
    __tablename__ = "sco_states"
    # moi SCO chi co mot trang thai trong mot attempt
    __table_args__ = (UniqueConstraint("attempt_id", "sco_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"))
    sco_id: Mapped[int] = mapped_column(ForeignKey("scos.id"))
    cmi: Mapped[dict] = mapped_column(JSON, default=dict)  # location, suspend_data, exit...
    lesson_status: Mapped[str] = mapped_column(String(20), default="not attempted")
    score_raw: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    score_min: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    score_max: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    last_seq: Mapped[int] = mapped_column(default=0)  # so thu tu lo luu cuoi
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=bay_gio)

    attempt: Mapped["Attempt"] = relationship(back_populates="sco_states")