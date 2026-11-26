
"""add lti identities

Revision ID: 114b413bc9c2
Revises: 3c58ad0dc19a
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "114b413bc9c2"
down_revision: str | Sequence[str] | None = "3c58ad0dc19a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lti_identities",
        sa.Column("issuer", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("deployment_id", sa.String(length=255), nullable=False),
        sa.Column("person_code", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["person_code"],
            ["people.person_code"],
        ),
        sa.PrimaryKeyConstraint(
            "issuer",
            "subject",
            "deployment_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("lti_identities")
