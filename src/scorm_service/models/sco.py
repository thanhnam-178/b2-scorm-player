from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .package_version import PackageVersion


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