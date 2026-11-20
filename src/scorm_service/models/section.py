from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Section(Base):
    __tablename__ = "sections"

    section_code: Mapped[str] = mapped_column(String(50), primary_key=True)
    term_code: Mapped[str] = mapped_column(ForeignKey("terms.term_code"))
    course_code: Mapped[str] = mapped_column(String(20))
    course_name: Mapped[str] = mapped_column(String(200))
    syllabus_version: Mapped[str | None] = mapped_column(String(20))
    faculty_code: Mapped[str | None] = mapped_column(String(20))
    faculty_name: Mapped[str | None] = mapped_column(String(200))
    credits: Mapped[int | None]
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))