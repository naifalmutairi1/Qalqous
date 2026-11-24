"""Shared test setup: each test gets its own temporary database file."""

import tempfile
import unittest
from pathlib import Path

import detect
from server import store

ACCOUNTS = [
    ("majed.f", "ماجد بن فهد بن عبدالرحمن العتيبي", "موظف عادي: يقرأ ملفات قسم المشتريات"),
    ("sara.y", "Sarah Young", "موظفة عادية: تقرأ ملفات قسم الحسابات"),
]
ATTACKER = "203.0.113.102"


def burst(account="majed.f", ip=ATTACKER, fails=10, hour=23):
    """`fails` failed logins, then one success, all within 3 minutes."""
    lines = [(f"2026-11-23T{hour}:00:{i:02d}+03:00", account, ip, 0) for i in range(fails)]
    lines.append((f"2026-11-23T{hour}:02:07+03:00", account, ip, 1))
    return lines


class StoreTestCase(unittest.TestCase):
    """Loads two accounts and one attack on majed.f into a fresh database."""

    events = burst()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        store.use_database(Path(self._tmp.name) / "test.db")
        store.reset_and_load(ACCOUNTS, self.events)

    def tearDown(self):
        store.use_database(None)
        self._tmp.cleanup()

    def open_one(self):
        opened = detect.open_incidents()
        self.assertEqual(len(opened), 1)
        return opened[0][0]

    def ready_report(self, incident_id, source="rules"):
        """Pretend the investigation finished, so a decision is allowed."""
        store.save_report(incident_id, source, "عنوان", "ملخص", [
            {"kind": "failed_attempts", "confirmed": True, "log_ids": [1, 2]},
            {"kind": "seen_before", "confirmed": False, "log_ids": []},
        ])
