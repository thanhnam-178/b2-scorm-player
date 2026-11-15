from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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