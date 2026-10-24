"""The Alembic head revision this build ships with (used by /readyz)."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


@cache
def expected_head() -> str | None:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS))
    return ScriptDirectory.from_config(cfg).get_current_head()
