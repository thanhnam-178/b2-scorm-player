from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint, Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import date, datetime, timezone



def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)  # luu gio UTC theo ho so


class Base(DeclarativeBase):
    pass


class PackageVersion(Base):
    __tablename__ = "package_versions"
    __table_args__ = (UniqueConstraint("package", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    package: Mapped[str] = mapped_column(String(200))
    version: Mapped[int]
    scorm_version: Mapped[str] = mapped_column(String(20))
    sha256: Mapped[str] = mapped_column(String(64))
    storage_prefix: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="ready")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_bay_gio)

    scos: Mapped[list["Sco"]] = relationship(
        back_populates="package_version", cascade="all, delete-orphan"
    )


class Sco(Base):
    __tablename__ = "scos"

    id: Mapped[int] = mapped_column(primary_key=True)
    package_version_id: Mapped[int] = mapped_column(
        ForeignKey("package_versions.id", ondelete="CASCADE")
    )
    identifier: Mapped[str] = mapped_column(String(200))
    title: Mapped[str | None] = mapped_column(String(300))
    href: Mapped[str | None] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(default=0)
    params: Mapped[dict] = mapped_column(JSON, default=dict)

    package_version: Mapped["PackageVersion"] = relationship(back_populates="scos")




class Term(Base):
    __tablename__ = "terms"

    term_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))  # open / locked


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


class Person(Base):
    __tablename__ = "people"

    person_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    family_name: Mapped[str] = mapped_column(String(100))
    given_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200))
    person_type: Mapped[str] = mapped_column(String(20))  # student / staff
    program_code: Mapped[str | None] = mapped_column(String(30))
    cohort: Mapped[int | None]


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