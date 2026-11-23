"""Database setup for Qalqous.

Everything is stored in one SQLite file (qalqous.db) next to this script.
SQLite comes with Python, so there is nothing extra to install.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "qalqous.db"

# One table per thing the PRD says we must remember.
SCHEMA = """
CREATE TABLE IF NOT EXISTS log_events (
    id          INTEGER PRIMARY KEY,   -- the "log line ID" that findings point to
    time        TEXT NOT NULL,         -- e.g. 2026-11-21 23:41:07
    account     TEXT NOT NULL,
    source_ip   TEXT NOT NULL,
    success     INTEGER NOT NULL       -- 1 = login worked, 0 = failed
);

CREATE TABLE IF NOT EXISTS incidents (
    id          INTEGER PRIMARY KEY,
    status      TEXT NOT NULL,         -- open / investigated
    opened_at   TEXT NOT NULL,
    account     TEXT NOT NULL,
    source_ip   TEXT NOT NULL,
    trigger_log_id INTEGER NOT NULL REFERENCES log_events(id)  -- the success that set off the alarm
);

CREATE TABLE IF NOT EXISTS investigation_steps (
    id          INTEGER PRIMARY KEY,
    incident_id INTEGER NOT NULL REFERENCES incidents(id),
    step_no     INTEGER NOT NULL,
    tool        TEXT NOT NULL,
    tool_input  TEXT NOT NULL,
    tool_output TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id              INTEGER PRIMARY KEY,
    incident_id     INTEGER NOT NULL REFERENCES incidents(id),
    text_ar         TEXT NOT NULL,     -- the finding, in Arabic
    evidence_log_id INTEGER REFERENCES log_events(id),  -- NULL = no evidence
    confirmed       INTEGER NOT NULL   -- 0 means the report shows "unconfirmed"
);

CREATE TABLE IF NOT EXISTS actions (
    id          INTEGER PRIMARY KEY,
    incident_id INTEGER NOT NULL REFERENCES incidents(id),
    proposal_ar TEXT NOT NULL,
    decision    TEXT,                  -- NULL until the admin picks approve / reject
    decided_at  TEXT
);
"""


def connect():
    """Open the database and make sure all tables exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us read columns by name: row["account"]
    conn.executescript(SCHEMA)
    return conn
