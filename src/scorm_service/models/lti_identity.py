
"""Anh xa danh tinh LTI sang nguoi dung B2."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, bay_gio


class LtiIdentity(Base):
    __tablename__ = "lti_identities"

    issuer: Mapped[str] = mapped_column(String(255), primary_key=True)
    subject: Mapped[str] = mapped_column(String(255), primary_key=True)
    deployment_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    person_code: Mapped[str] = mapped_column(
        ForeignKey("people.person_code"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=bay_gio,
        nullable=False,
    )
