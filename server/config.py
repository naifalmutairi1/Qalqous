"""Settings, read once from environment variables and checked at startup.

If a setting is wrong, the program stops right away with a clear message,
instead of failing later in a confusing way.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # the project folder

# One company, one admin, no login: these are constants, not database rows.
COMPANY = {"name": "Najd Build Contracting", "timezone": "Asia/Riyadh"}

DEFAULT_DATABASE_URL = "sqlite:///qalqous.db"


def _database_path():
    """Turn DATABASE_URL into a file path. Only SQLite is supported for now."""
    url = os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        sys.exit(
            f"DATABASE_URL must start with {prefix} (got {url.split(':')[0]}://...). "
            "Only SQLite works today; Postgres/Supabase is a later task (see CLAUDE.md)."
        )
    path = Path(url[len(prefix):])
    return path if path.is_absolute() else ROOT / path  # relative paths start at the project folder


DATABASE_PATH = _database_path()

# CLAUDE.md: if this is set, the Agent SDK may bill this key instead of the Claude Code login.
if os.environ.get("ANTHROPIC_API_KEY"):
    print("Warning: ANTHROPIC_API_KEY is set. Unset it to use your Claude Code login.", file=sys.stderr)
