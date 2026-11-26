
"""Lien ket nhieu-nhieu giua section va package version."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SectionPackage(Base):
    __tablename__ = "section_packages"

    section_code: Mapped[str] = mapped_column(
        ForeignKey("sections.section_code"),
        primary_key=True,
    )
    package_version_id: Mapped[int] = mapped_column(
        ForeignKey("package_versions.id"),
        primary_key=True,
    )
