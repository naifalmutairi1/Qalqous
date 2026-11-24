"""Checks that the database itself refuses bad data.

Run from the project root:  python -m unittest discover server/tests
These tests write SQL on purpose (through store._connection), to prove that
the database's own rules hold even if our Python code had a bug.
"""

import sqlite3

from helpers import StoreTestCase
from server import store


class SchemaTest(StoreTestCase):
    def sql(self, query, params=()):
        with store._connection() as conn, conn:
            conn.execute(query, params)

    # --- migrations ---------------------------------------------------------

    def test_user_version_is_1(self):
        self.assertEqual(store.schema_version(), 1)

    def test_migrating_again_changes_nothing(self):
        store._migrated = False  # force the migration check to run again
        self.assertEqual(store.schema_version(), 1)  # would fail "table already exists" if 001 re-ran

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

    # --- investigation steps ------------------------------------------------

    def test_seventh_step_is_refused(self):
        incident_id = self.open_one()
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql(
                "INSERT INTO investigation_steps (incident_id, step_no, tool, tool_input, tool_output)"
                " VALUES (?, 7, 'search_logs', '{}', '{}')",
                (incident_id,),
            )

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
