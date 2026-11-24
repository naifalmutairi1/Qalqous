"""Checks that the database itself refuses bad data.

Run from the project root:  python -m unittest discover server/tests
Each test gets a fresh in-memory database, so qalqous.db is never touched.
"""

import sqlite3
import unittest

from db import connect, migrate
from detect import open_incidents


def add_burst(conn, account="majed.f", fails=10):
    """Insert `fails` failed logins and then one success for `account`."""
    rows = [(f"2026-11-23T23:00:{i:02d}+03:00", account, "203.0.113.102", 0) for i in range(fails)]
    rows.append(("2026-11-23T23:02:07+03:00", account, "203.0.113.102", 1))
    conn.executemany(
        "INSERT INTO log_events (time, account, source_ip, success) VALUES (?, ?, ?, ?)", rows
    )


class SchemaTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        self.conn.execute(
            "INSERT INTO accounts (username, display_name, access_ar) VALUES"
            " ('majed.f', 'ماجد', 'موظف عادي: يقرأ ملفات قسم المشتريات')"
        )
        add_burst(self.conn)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def open_one(self):
        opened = open_incidents(self.conn)
        self.assertEqual(len(opened), 1)
        return opened[0][0]

    def mark_ready(self, incident_id):
        """Pretend the investigation finished, so a decision is allowed."""
        self.conn.execute(
            "UPDATE incidents SET status = 'awaiting_decision', report_source = 'rules',"
            " headline_ar = 'عنوان', report_ready_at = '2026-11-23T23:05:00+03:00' WHERE id = ?",
            (incident_id,),
        )

    # --- migrations ---------------------------------------------------------

    def test_user_version_is_1(self):
        self.assertEqual(self.conn.execute("PRAGMA user_version").fetchone()[0], 1)

    def test_migrating_twice_changes_nothing(self):
        migrate(self.conn)  # would fail with "table already exists" if it re-ran 001
        self.assertEqual(self.conn.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0], 1)

    def test_foreign_keys_are_on(self):
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    # --- detection ----------------------------------------------------------

    def test_detection_opens_incident_and_suspends(self):
        incident_id = self.open_one()
        row = self.conn.execute(
            "SELECT status, failed_attempts, ip_seen_before FROM incidents WHERE id = ?",
            (incident_id,),
        ).fetchone()
        self.assertEqual(tuple(row), ("investigating", 10, 0))
        status = self.conn.execute("SELECT status FROM accounts WHERE username = 'majed.f'").fetchone()[0]
        self.assertEqual(status, "suspended")

    def test_running_detection_again_opens_nothing(self):
        self.open_one()
        self.assertEqual(open_incidents(self.conn), [])

    # --- incidents ----------------------------------------------------------

    def test_second_open_incident_for_same_account_is_refused(self):
        self.open_one()
        add_burst(self.conn)  # a new burst, new log line ids
        last = self.conn.execute("SELECT MAX(id) FROM log_events").fetchone()[0]
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO incidents (account, first_fail_log_id, trigger_log_id, source_ip,"
                " failed_attempts, ip_seen_before, access_ar)"
                " VALUES ('majed.f', ?, ?, '203.0.113.102', 10, 0, 'x')",
                (last - 10, last),
            )

    def test_awaiting_decision_without_report_is_refused(self):
        incident_id = self.open_one()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "UPDATE incidents SET status = 'awaiting_decision' WHERE id = ?", (incident_id,)
            )

    # --- decisions ----------------------------------------------------------

    def test_bad_decision_value_is_refused(self):
        incident_id = self.open_one()
        self.mark_ready(incident_id)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO decisions (incident_id, choice) VALUES (?, 'approve')", (incident_id,)
            )

    def test_second_decision_is_refused(self):
        incident_id = self.open_one()
        self.mark_ready(incident_id)
        self.conn.execute(
            "INSERT INTO decisions (incident_id, choice) VALUES (?, 'restore')", (incident_id,)
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO decisions (incident_id, choice) VALUES (?, 'keep_suspended')",
                (incident_id,),
            )

    def test_decision_time_is_iso_riyadh(self):
        incident_id = self.open_one()
        self.mark_ready(incident_id)
        self.conn.execute(
            "INSERT INTO decisions (incident_id, choice) VALUES (?, 'restore')", (incident_id,)
        )
        created = self.conn.execute("SELECT created_at FROM decisions").fetchone()[0]
        self.assertRegex(created, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+03:00$")

    # --- investigation steps ------------------------------------------------

    def test_seventh_step_is_refused(self):
        incident_id = self.open_one()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO investigation_steps (incident_id, step_no, tool, tool_input, tool_output)"
                " VALUES (?, 7, 'search_logs', '{}', '{}')",
                (incident_id,),
            )

    # --- log lines ----------------------------------------------------------

    def test_log_line_must_be_fail_or_success(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO log_events (time, account, source_ip, success)"
                " VALUES ('2026-11-23T23:00:00+03:00', 'majed.f', '192.0.2.1', 2)"
            )


if __name__ == "__main__":
    unittest.main()
