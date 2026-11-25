"""Checks that the database itself refuses bad data.

Run from the project root:  python -m unittest discover server/tests
These tests write SQL on purpose (through store._connection), to prove that
the database's own rules hold even if our Python code had a bug.
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from helpers import StoreTestCase
from server import store


class SchemaTest(StoreTestCase):
    def sql(self, query, params=()):
        with store._connection() as conn, conn:
            conn.execute(query, params)

    # --- migrations ---------------------------------------------------------

    def test_user_version_is_2(self):
        self.assertEqual(store.schema_version(), 2)

    def test_migrating_again_changes_nothing(self):
        store._migrated = False  # force the migration check to run again
        self.assertEqual(store.schema_version(), 2)  # would fail "table already exists" if a file re-ran

    def test_foreign_keys_are_on(self):
        with store._connection() as conn:
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    # --- incidents ----------------------------------------------------------

    def test_second_open_incident_for_same_account_is_refused(self):
        self.open_one()
        with self.assertRaises(sqlite3.IntegrityError):
            # Log line 1 is not used as a trigger yet, so only the "one open per account" rule can stop this.
            self.sql(
                "INSERT INTO incidents (account, first_fail_log_id, trigger_log_id, source_ip,"
                " failed_attempts, ip_seen_before, access_ar) VALUES ('majed.f', 1, 2, 'x', 5, 0, 'x')"
            )

    def test_awaiting_decision_without_report_is_refused(self):
        incident_id = self.open_one()
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql("UPDATE incidents SET status = 'awaiting_decision' WHERE id = ?", (incident_id,))

    # --- decisions ----------------------------------------------------------

    def test_bad_decision_value_is_refused(self):
        incident_id = self.open_one()
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql("INSERT INTO decisions (incident_id, choice) VALUES (?, 'approve')", (incident_id,))

    def test_second_decision_row_is_refused(self):
        incident_id = self.open_one()
        self.sql("INSERT INTO decisions (incident_id, choice) VALUES (?, 'restore')", (incident_id,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql("INSERT INTO decisions (incident_id, choice) VALUES (?, 'keep_suspended')", (incident_id,))

    # --- investigation attempts and steps -------------------------------------

    def step(self, attempt_id, step_no, tool="search_logs"):
        self.sql(
            "INSERT INTO investigation_steps (attempt_id, step_no, tool, tool_input, tool_output)"
            " VALUES (?, ?, ?, '{}', '{}')",
            (attempt_id, step_no, tool),
        )

    def test_seventh_step_is_refused(self):
        attempt_id = store.start_attempt(self.open_one())
        with self.assertRaises(sqlite3.IntegrityError):
            self.step(attempt_id, 7)

    def test_unknown_tool_is_refused(self):
        attempt_id = store.start_attempt(self.open_one())
        with self.assertRaises(sqlite3.IntegrityError):
            self.step(attempt_id, 1, tool="Bash")

    def test_same_step_number_twice_is_refused(self):
        attempt_id = store.start_attempt(self.open_one())
        self.step(attempt_id, 1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.step(attempt_id, 1)

    def test_retry_starts_again_at_step_1(self):
        incident_id = self.open_one()
        first = store.start_attempt(incident_id)
        self.step(first, 1)
        self.sql("UPDATE investigation_attempts SET outcome = 'failed', failure_reason = 'timeout',"
                 " finished_at = 'x' WHERE id = ?", (first,))
        self.step(store.start_attempt(incident_id), 1)  # no error

    def test_second_running_attempt_is_refused(self):
        incident_id = self.open_one()
        store.start_attempt(incident_id)
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql("INSERT INTO investigation_attempts (incident_id) VALUES (?)", (incident_id,))

    def test_failed_attempt_needs_a_reason(self):
        attempt_id = store.start_attempt(self.open_one())
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql("UPDATE investigation_attempts SET outcome = 'failed', finished_at = 'x' WHERE id = ?",
                     (attempt_id,))

    def test_reason_only_when_failed(self):
        attempt_id = store.start_attempt(self.open_one())
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql("UPDATE investigation_attempts SET outcome = 'ai', failure_reason = 'timeout',"
                     " finished_at = 'x' WHERE id = ?", (attempt_id,))

    def test_unknown_failure_reason_is_refused(self):
        attempt_id = store.start_attempt(self.open_one())
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql("UPDATE investigation_attempts SET outcome = 'failed', failure_reason = 'oops',"
                     " finished_at = 'x' WHERE id = ?", (attempt_id,))

    def test_finished_attempt_needs_a_finish_time(self):
        attempt_id = store.start_attempt(self.open_one())
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql("UPDATE investigation_attempts SET outcome = 'ai' WHERE id = ?", (attempt_id,))

    # --- log lines ----------------------------------------------------------

    def test_log_line_must_be_fail_or_success(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql(
                "INSERT INTO log_events (time, account, source_ip, success)"
                " VALUES ('2026-11-23T23:00:00+03:00', 'majed.f', '192.0.2.1', 2)"
            )

    # --- read-only connection -----------------------------------------------

    def test_read_only_connection_cannot_write(self):
        with store.connect_read_only() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0], 2)
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("DELETE FROM accounts")


class MigrationGuardTest(unittest.TestCase):
    """002 rebuilds investigation_steps. If the old table had rows, it must stop and undo everything."""

    def test_002_stops_if_old_steps_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "old.db"
            # Build a version-1 database by hand, with one old-style step in it.
            conn = sqlite3.connect(path)
            conn.executescript((store.MIGRATIONS_DIR / "001_init.sql").read_text(encoding="utf-8"))
            conn.executescript(
                "PRAGMA user_version = 1;"
                "INSERT INTO accounts (username, display_name, access_ar) VALUES ('a', 'a', 'a');"
                "INSERT INTO log_events (time, account, source_ip, success) VALUES ('t', 'a', 'x', 0), ('t', 'a', 'x', 1);"
                "INSERT INTO incidents (account, first_fail_log_id, trigger_log_id, source_ip, failed_attempts,"
                " ip_seen_before, access_ar) VALUES ('a', 1, 2, 'x', 5, 0, 'a');"
                "INSERT INTO investigation_steps (incident_id, step_no, tool, tool_input, tool_output)"
                " VALUES (1, 1, 'search_logs', '{}', '{}');"
            )
            conn.close()

            store.use_database(path)
            try:
                with self.assertRaises(sqlite3.IntegrityError):
                    store.schema_version()
            finally:
                store.use_database(None)

            conn = sqlite3.connect(path)
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM investigation_steps").fetchone()[0], 1)
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            self.assertNotIn("investigation_attempts", tables)  # the half-done migration was undone
            conn.close()
