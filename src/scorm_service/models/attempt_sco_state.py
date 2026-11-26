
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, bay_gio


class AttemptScoState(Base):
    __tablename__ = "attempt_sco_states"
    __table_args__ = (
        UniqueConstraint("attempt_id", "sco_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE")
    )
    sco_id: Mapped[int] = mapped_column(
        ForeignKey("scos.id", ondelete="CASCADE")
    )

    cmi_data: Mapped[dict] = mapped_column(JSON, default=dict)

    runtime_initialized: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    runtime_terminated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=bay_gio,
        onupdate=bay_gio,
    )
