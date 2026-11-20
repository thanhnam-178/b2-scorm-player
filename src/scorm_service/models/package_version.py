from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, bay_gio

if TYPE_CHECKING:
    from .sco import Sco


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=bay_gio)

    scos: Mapped[list["Sco"]] = relationship(
        back_populates="package_version", cascade="all, delete-orphan"
    )