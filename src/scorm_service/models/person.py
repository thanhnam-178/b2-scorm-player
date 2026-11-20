from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Person(Base):
    __tablename__ = "people"

    person_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    family_name: Mapped[str] = mapped_column(String(100))
    given_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200))
    person_type: Mapped[str] = mapped_column(String(20))  # student / staff
    program_code: Mapped[str | None] = mapped_column(String(30))
    cohort: Mapped[int | None]