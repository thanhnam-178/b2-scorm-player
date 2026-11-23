from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RuntimeSession(Base):
    __tablename__ = "runtime_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"))
    sco_id: Mapped[int] = mapped_column(ForeignKey("scos.id"))
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    code_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    code_used: Mapped[bool] = mapped_column(default=False)
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))