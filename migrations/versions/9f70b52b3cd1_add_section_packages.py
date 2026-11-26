
"""add section packages

Revision ID: 9f70b52b3cd1
Revises: c400018c83a8
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9f70b52b3cd1"
down_revision: str | Sequence[str] | None = "c400018c83a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the section-package many-to-many table."""
    op.create_table(
        "section_packages",
        sa.Column("section_code", sa.String(length=50), nullable=False),
        sa.Column("package_version_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["section_code"],
            ["sections.section_code"],
        ),
        sa.ForeignKeyConstraint(
            ["package_version_id"],
            ["package_versions.id"],
        ),
        sa.PrimaryKeyConstraint("section_code", "package_version_id"),
    )


def downgrade() -> None:
    """Drop the section-package association table."""
    op.drop_table("section_packages")
