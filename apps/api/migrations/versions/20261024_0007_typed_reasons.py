"""typed decision reasons: the user can type a reason the letter states (PRD FR-019)

Expand-only: one new column with a default, so existing rows and running code are unaffected.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-24 10:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "decision_reasons", sa.Column("user_entered", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("decision_reasons", "user_entered")
