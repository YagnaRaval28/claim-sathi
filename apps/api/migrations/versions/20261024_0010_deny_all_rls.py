"""deny-all row-level security on every table (system-design §3.7 "Supabase hardening")

Supabase can expose the public schema through its Data API to the `anon` and `authenticated` roles. We never use
that API, so every table gets RLS with no policies (deny-all) and those roles lose all table privileges, now and
for tables created later. The app connects as the table owner, which RLS does not restrict. On plain Postgres
(local, CI) the Supabase roles don't exist and only RLS is enabled.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-24 18:10:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

HARDEN = """
DO $$
DECLARE t record;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tablename);
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
    REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
    REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon, authenticated;
  END IF;
END $$;
"""


def upgrade() -> None:
    op.execute(HARDEN)


def downgrade() -> None:
    # Forward-only in practice (engineering standards): turning protection off is never automated.
    pass
