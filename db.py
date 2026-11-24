"""Database setup for Qalqous.

Everything is stored in one SQLite file (qalqous.db) next to this script.
SQLite comes with Python, so there is nothing extra to install.

The schema lives only in server/migrations/ as numbered SQL files
(001_init.sql, 002_..., ...). SQLite keeps one number, PRAGMA user_version,
that says which file ran last. connect() runs only the files above it.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "qalqous.db"
MIGRATIONS_DIR = Path(__file__).parent / "server" / "migrations"


def migrate(conn):
    """Run every migration file whose number is above the database's user_version."""
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        number = int(path.name.split("_")[0])  # "001_init.sql" -> 1
        if number <= current:
            continue
        sql = path.read_text(encoding="utf-8")
        # BEGIN ... COMMIT makes each file all-or-nothing: if one line fails,
        # none of the file is applied and user_version stays the same.
        try:
            conn.executescript(f"BEGIN;\n{sql}\nPRAGMA user_version = {number};\nCOMMIT;")
        except sqlite3.Error:
            conn.rollback()
            raise


def connect(path=DB_PATH):
    """Open the database and bring its schema up to date."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row  # lets us read columns by name: row["account"]
    # SQLite ignores REFERENCES (foreign keys) unless this is on, per connection.
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn
