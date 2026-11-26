
"""add runtime lifecycle to attempt sco states

Revision ID: 3c58ad0dc19a
Revises: 9f70b52b3cd1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3c58ad0dc19a"
down_revision: str | Sequence[str] | None = "9f70b52b3cd1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "attempt_sco_states",
        sa.Column(
            "runtime_initialized",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "attempt_sco_states",
        sa.Column(
            "runtime_terminated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("attempt_sco_states", "runtime_terminated")
    op.drop_column("attempt_sco_states", "runtime_initialized")
