"""store.py: the ONLY file that opens the database.

The API routes, detect.py, generate_logs.py and (later) the investigator call
the functions below. They never write SQL themselves. If we move to
Postgres/Supabase later, this file is what gets rewritten; its callers stay.

Things here that are SQLite-only (each marked "SQLite-only" below):
- sqlite3 connections and "?" placeholders (Postgres drivers use %s)
- PRAGMA foreign_keys (Postgres always checks foreign keys)
- PRAGMA user_version to track migrations (Postgres: a schema_migrations table)
- read-only connections via "file:...?mode=ro" (Postgres: a read-only role)
- 0/1 for true/false (Postgres has a real boolean); we turn them into True/False here
The SQL itself sticks to what both understand: INSERT ... RETURNING, CHECKs,
no SQLite date functions in queries (Python does the date math).
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from server import config

MIGRATIONS_DIR = config.ROOT / "server" / "migrations"

_database_path = config.DATABASE_PATH
_migrated = False  # migrations run once per process, on the first connection


class IncidentNotFound(Exception):
    pass


class DecisionNotAllowed(Exception):
    """The incident is still being investigated, or already has a decision."""


def use_database(path):
    """Point the store at another file. Used by tests so they never touch qalqous.db."""
    global _database_path, _migrated
    _database_path = path
    _migrated = False


# --- connections and migrations ------------------------------------------------


def _migrate(conn):
    """Run every migration file whose number is above the database's user_version.

    SQLite-only: PRAGMA user_version and executescript.
    """
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        number = int(path.name.split("_")[0])  # "001_init.sql" -> 1
        if number <= current:
            continue
        sql = path.read_text(encoding="utf-8")
        # BEGIN ... COMMIT makes each file all-or-nothing.
        try:
            conn.executescript(f"BEGIN;\n{sql}\nPRAGMA user_version = {number};\nCOMMIT;")
        except sqlite3.Error:
            conn.rollback()
            raise


@contextmanager
def _connection():
    """Open a connection, use it, always close it.

    Each call gets its own connection: FastAPI runs requests on several threads,
    and one SQLite connection must not be shared between threads.
    Tests also use this to check the database's own rules directly.
    """
    global _migrated
    conn = sqlite3.connect(_database_path)
    conn.row_factory = sqlite3.Row  # read columns by name: row["account"]
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite-only: off unless asked, per connection
    try:
        if not _migrated:
            _migrate(conn)
            _migrated = True
        yield conn
    finally:
        conn.close()


@contextmanager
def connect_read_only():
    """A connection that cannot change anything. For the investigator's tools.

    SQLite-only: the "mode=ro" URI. Postgres would use a read-only role.
    """
    with _connection():  # make sure migrations ran first
        pass
    conn = sqlite3.connect(f"{_database_path.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def schema_version():
    with _connection() as conn:
        return conn.execute("PRAGMA user_version").fetchone()[0]  # SQLite-only


# --- small helpers ---------------------------------------------------------------


def _log_label(log_id):
    """Log line ids are shown as codes: 1489 -> "evt-1489"."""
    return f"evt-{log_id}"


def _log_line(row):
    return {
        "id": _log_label(row["id"]),
        "at": row["time"],
        "event": "LOGIN_SUCCESS" if row["success"] else "LOGIN_FAIL",
        "username": row["account"],
        "ip": row["source_ip"],
    }


def _evidence_rows(conn, incident):
    """Every line for this account from the first failure to the triggering success."""
    return conn.execute(
        "SELECT id, time, account, source_ip, success FROM log_events"
        " WHERE account = ? AND id BETWEEN ? AND ? ORDER BY time, id",
        (incident["account"], incident["first_fail_log_id"], incident["trigger_log_id"]),
    ).fetchall()


# --- fake logs (generate_logs.py) --------------------------------------------------


def reset_and_load(accounts, events):
    """Wipe everything and load new fake data, in one transaction.

    accounts: [(username, display_name, access_ar)]
    events:   [(time, account, source_ip, success)]
    """
    with _connection() as conn, conn:  # the second "conn" = one transaction
        # Children first: foreign keys refuse to delete a row something points to.
        for table in ["finding_evidence", "findings", "investigation_steps", "decisions",
                      "incidents", "log_events", "accounts"]:
            conn.execute(f"DELETE FROM {table}")
        conn.executemany(
            "INSERT INTO accounts (username, display_name, access_ar) VALUES (?, ?, ?)", accounts
        )
        conn.executemany(
            "INSERT INTO log_events (time, account, source_ip, success) VALUES (?, ?, ?, ?)", events
        )


# --- detection (detect.py) ---------------------------------------------------------


def logins_by_account():
    """All log lines, grouped by account, oldest first: {account: [line, ...]}."""
    with _connection() as conn:
        rows = conn.execute(
            "SELECT id, time, account, source_ip, success FROM log_events ORDER BY account, time, id"
        ).fetchall()
    grouped = {}
    for row in rows:
        grouped.setdefault(row["account"], []).append(dict(row))
    return grouped


def open_incident(account, first_fail_log_id, trigger_log_id, failed_attempts):
    """Open an incident and suspend the account (simulated), in one transaction.

    Returns the new incident id, or None if this success was already used or
    the account already has an undecided incident.
    """
    with _connection() as conn, conn:
        already = conn.execute(
            "SELECT id FROM incidents WHERE trigger_log_id = ? OR (account = ? AND status <> 'decided')",
            (trigger_log_id, account),
        ).fetchone()
        if already:
            return None
        trigger = conn.execute(
            "SELECT source_ip FROM log_events WHERE id = ?", (trigger_log_id,)
        ).fetchone()
        # Seen before = this account had a successful login from this IP earlier.
        seen_before = conn.execute(
            "SELECT 1 FROM log_events WHERE account = ? AND source_ip = ? AND success = 1 AND id < ?",
            (account, trigger["source_ip"], trigger_log_id),
        ).fetchone() is not None
        access = conn.execute(
            "SELECT access_ar FROM accounts WHERE username = ?", (account,)
        ).fetchone()["access_ar"]
        incident_id = conn.execute(
            "INSERT INTO incidents (account, first_fail_log_id, trigger_log_id, source_ip,"
            " failed_attempts, ip_seen_before, access_ar) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id",
            (account, first_fail_log_id, trigger_log_id, trigger["source_ip"],
             failed_attempts, 1 if seen_before else 0, access),
        ).fetchone()["id"]
        conn.execute("UPDATE accounts SET status = 'suspended' WHERE username = ?", (account,))
        return incident_id


def count_incidents():
    with _connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]


# --- investigation (rule-based writer now, the Claude investigator later) ----------


def investigation_input(incident_id):
    """What an investigator needs to write a report, or None if there is no such incident.

    lines: this incident's log lines (first failure to the triggering success), oldest first,
    as {"id": 1479, "time": ..., "source_ip": ..., "success": True}.
    seen_before_log_id: an earlier successful login of this account from the same address,
    or None. It backs the "seen before" finding when the answer is yes.
    """
    with _connection() as conn:
        incident = conn.execute(
            "SELECT id, account, first_fail_log_id, trigger_log_id, source_ip, failed_attempts,"
            " ip_seen_before FROM incidents WHERE id = ?",
            (incident_id,),
        ).fetchone()
        if incident is None:
            return None
        lines = _evidence_rows(conn, incident)
        earlier = conn.execute(
            "SELECT id FROM log_events WHERE account = ? AND source_ip = ? AND success = 1 AND id < ?"
            " ORDER BY id DESC LIMIT 1",
            (incident["account"], incident["source_ip"], incident["trigger_log_id"]),
        ).fetchone()
    return {
        "id": incident["id"],
        "account": incident["account"],
        "trigger_log_id": incident["trigger_log_id"],
        "source_ip": incident["source_ip"],
        "failed_attempts": incident["failed_attempts"],
        "ip_seen_before": bool(incident["ip_seen_before"]),
        "lines": [
            {"id": row["id"], "time": row["time"], "source_ip": row["source_ip"], "success": bool(row["success"])}
            for row in lines
        ],
        "seen_before_log_id": earlier["id"] if earlier else None,
    }


def known_log_ids(log_ids):
    """Which of these ids are real log lines. The evidence check uses it."""
    ids = list(log_ids)
    if not ids:
        return set()
    with _connection() as conn:
        placeholders = ", ".join("?" for _ in ids)  # SQLite-only: "?" placeholders
        rows = conn.execute(f"SELECT id FROM log_events WHERE id IN ({placeholders})", ids).fetchall()
    return {row["id"] for row in rows}


def save_report(incident_id, report_source, headline_ar, summary_ar, findings):
    """Store a finished report and move the incident to awaiting_decision.

    findings: [{"kind": "failed_attempts", "confirmed": True, "log_ids": [1479, ...]}, ...]
    A retry replaces the previous report's findings.
    """
    with _connection() as conn, conn:
        conn.execute(
            "DELETE FROM finding_evidence WHERE finding_id IN"
            " (SELECT id FROM findings WHERE incident_id = ?)", (incident_id,)
        )
        conn.execute("DELETE FROM findings WHERE incident_id = ?", (incident_id,))
        for finding in findings:
            finding_id = conn.execute(
                "INSERT INTO findings (incident_id, kind, confirmed) VALUES (?, ?, ?) RETURNING id",
                (incident_id, finding["kind"], 1 if finding["confirmed"] else 0),
            ).fetchone()["id"]
            conn.executemany(
                "INSERT INTO finding_evidence (finding_id, log_id) VALUES (?, ?)",
                [(finding_id, log_id) for log_id in finding["log_ids"]],
            )
        # Python makes the time, so this query has no SQLite-only date function.
        conn.execute(
            "UPDATE incidents SET status = 'awaiting_decision', report_source = ?, headline_ar = ?,"
            " summary_ar = ?, report_ready_at = ? WHERE id = ? AND status <> 'decided'",
            (report_source, headline_ar, summary_ar, _now(), incident_id),
        )


def _now():
    """Now, in Riyadh time, as 2026-11-24T20:40:10+03:00 (Riyadh has no daylight saving)."""
    return datetime.now(timezone(timedelta(hours=3))).isoformat(timespec="seconds")


# --- Home screen ---------------------------------------------------------------------


def home_summary():
    """Everything the Home screen shows, in one call."""
    with _connection() as conn:
        accounts = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        last_check = conn.execute("SELECT MAX(created_at) FROM log_events").fetchone()[0]
        # The demo has one attack; if there were more, Home shows the oldest.
        open_row = conn.execute(
            "SELECT id FROM incidents WHERE status <> 'decided' ORDER BY created_at, id LIMIT 1"
        ).fetchone()
        decided_rows = conn.execute(
            "SELECT i.id, i.account, i.created_at, d.choice, d.created_at AS decided_at"
            " FROM incidents i JOIN decisions d ON d.incident_id = i.id"
            " ORDER BY d.created_at DESC, d.id DESC"
        ).fetchall()
        open_incident_card = _incident_card(conn, open_row["id"]) if open_row else None

    # "error" (the AI investigation failed) is not used yet: there is no AI investigator, so a
    # rules report is the normal case. Home still tags its card «تقرير أساسي» (from reportSource).
    # Project rule: once the AI exists, "error" means an AI attempt actually failed.
    if open_incident_card is not None and open_incident_card["status"] == "investigating":
        status = "investigating"
    else:
        status = "ok"

    return {
        "company": config.COMPANY,
        "monitor": {"accountsMonitored": accounts, "lastCheckAt": last_check, "status": status},
        "openIncident": open_incident_card,
        # Newest decision first. The first one is «آخر قرار».
        "decided": [
            {
                "id": row["id"],
                "username": row["account"],
                "openedAt": row["created_at"],
                "decision": {"choice": row["choice"], "decidedAt": row["decided_at"]},
            }
            for row in decided_rows
        ],
    }


def _incident_card(conn, incident_id):
    """The short version of an incident, for the Home card."""
    row = conn.execute(
        "SELECT i.id, i.account, i.status, i.report_source, i.created_at, i.failed_attempts,"
        " i.ip_seen_before, i.access_ar, l.time AS success_at"
        " FROM incidents i JOIN log_events l ON l.id = i.trigger_log_id WHERE i.id = ?",
        (incident_id,),
    ).fetchone()
    return {
        "id": row["id"],
        "username": row["account"],
        "status": row["status"],
        "reportSource": row["report_source"],
        "openedAt": row["created_at"],
        "successAt": row["success_at"],
        "failedAttempts": row["failed_attempts"],
        "ipSeenBefore": bool(row["ip_seen_before"]),
        "access": row["access_ar"],
    }


# --- Report screen ---------------------------------------------------------------------


def get_incident(incident_id):
    """One incident with everything the Report shows, or None if there is no such incident."""
    with _connection() as conn:
        incident = conn.execute(
            "SELECT id, created_at, account, status, first_fail_log_id, trigger_log_id, source_ip,"
            " failed_attempts, ip_seen_before, access_ar, report_source, headline_ar, summary_ar,"
            " report_ready_at FROM incidents WHERE id = ?",
            (incident_id,),
        ).fetchone()
        if incident is None:
            return None
        account = conn.execute(
            "SELECT username, display_name, status FROM accounts WHERE username = ?",
            (incident["account"],),
        ).fetchone()
        lines = _evidence_rows(conn, incident)
        finding_rows = conn.execute(
            "SELECT f.id, f.kind, f.confirmed, e.log_id FROM findings f"
            " LEFT JOIN finding_evidence e ON e.finding_id = f.id"
            " WHERE f.incident_id = ? ORDER BY f.id, e.log_id",
            (incident_id,),
        ).fetchall()
        decision = conn.execute(
            "SELECT choice, created_at FROM decisions WHERE incident_id = ?", (incident_id,)
        ).fetchone()

    fails = [line for line in lines if not line["success"]]
    trigger = next(line for line in lines if line["id"] == incident["trigger_log_id"])

    findings = {}
    for row in finding_rows:
        finding = findings.setdefault(
            row["id"], {"kind": row["kind"], "confirmed": bool(row["confirmed"]), "evidenceLogIds": []}
        )
        if row["log_id"] is not None:
            finding["evidenceLogIds"].append(_log_label(row["log_id"]))

    return {
        "company": config.COMPANY,
        "id": incident["id"],
        "username": incident["account"],
        "status": incident["status"],
        "reportSource": incident["report_source"],
        "headline": incident["headline_ar"],
        "summary": incident["summary_ar"],
        "openedAt": incident["created_at"],
        "reportReadyAt": incident["report_ready_at"],
        "failedAttempts": incident["failed_attempts"],
        "firstFailAt": fails[0]["time"] if fails else None,
        "lastFailAt": fails[-1]["time"] if fails else None,
        "successAt": trigger["time"],
        "sourceIp": incident["source_ip"],
        "ipSeenBefore": bool(incident["ip_seen_before"]),
        "access": incident["access_ar"],
        "account": {
            "username": account["username"],
            "displayName": account["display_name"],
            "status": account["status"],
        },
        "evidenceLogIds": [_log_label(line["id"]) for line in lines],
        "logs": [_log_line(line) for line in lines],
        "findings": list(findings.values()),
        "decision": (
            {"choice": decision["choice"], "decidedAt": decision["created_at"]} if decision else None
        ),
    }


# --- the decision ------------------------------------------------------------------------


def record_decision(incident_id, choice):
    """Save the admin's decision, once per incident, in one transaction.

    restore -> the simulated account becomes active again.
    keep_suspended -> it stays suspended.
    Returns {"choice", "decidedAt"}.
    """
    with _connection() as conn:
        try:
            with conn:  # one transaction: all three writes, or none
                row = conn.execute(
                    "SELECT account, status FROM incidents WHERE id = ?", (incident_id,)
                ).fetchone()
                if row is None:
                    raise IncidentNotFound(incident_id)
                if row["status"] != "awaiting_decision":
                    raise DecisionNotAllowed(incident_id)
                decided_at = conn.execute(
                    "INSERT INTO decisions (incident_id, choice) VALUES (?, ?) RETURNING created_at",
                    (incident_id, choice),
                ).fetchone()["created_at"]
                conn.execute("UPDATE incidents SET status = 'decided' WHERE id = ?", (incident_id,))
                new_status = "active" if choice == "restore" else "suspended"
                conn.execute(
                    "UPDATE accounts SET status = ? WHERE username = ?", (new_status, row["account"])
                )
        except sqlite3.IntegrityError as error:
            # Two clicks at the same moment: the second hits UNIQUE(incident_id).
            raise DecisionNotAllowed(incident_id) from error
    return {"choice": choice, "decidedAt": decided_at}
