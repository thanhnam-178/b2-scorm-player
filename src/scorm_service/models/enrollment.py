from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Enrollment(Base):
    __tablename__ = "enrollments"

    section_code: Mapped[str] = mapped_column(
        ForeignKey("sections.section_code"), primary_key=True
    )
    person_code: Mapped[str] = mapped_column(
        ForeignKey("people.person_code"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(30))  # student / editingteacher / teacher
    group_code: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))  # registered / cancelled / withdrawn
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))