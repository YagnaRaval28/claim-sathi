"""wording preference: the user's choice between their uploaded wording and the library (PRD FR-014)

Expand-only: one new column with a default, plus its CHECK constraint.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-24 16:17:15.806269
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("wording_preference", sa.String(length=10), server_default="auto", nullable=False))
    op.create_check_constraint(
        op.f("ck_cases_wording_preference"), "cases", "wording_preference IN ('auto','uploaded','library')"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_cases_wording_preference"), "cases", type_="check")
    op.drop_column("cases", "wording_preference")
