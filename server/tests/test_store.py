"""Checks the store functions that detection, Home, Report and the decision use."""

import detect
from helpers import ATTACKER, StoreTestCase, burst
from server import store

ISO_RIYADH = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+03:00$"


def account_status(username):
    with store._connection() as conn:
        return conn.execute("SELECT status FROM accounts WHERE username = ?", (username,)).fetchone()[0]


class DetectionTest(StoreTestCase):
    def test_opens_incident_and_suspends(self):
        incident_id = self.open_one()
        incident = store.get_incident(incident_id)
        self.assertEqual(incident["status"], "investigating")
        self.assertEqual(incident["failedAttempts"], 10)
        self.assertFalse(incident["ipSeenBefore"])
        self.assertEqual(account_status("majed.f"), "suspended")

    def test_running_again_opens_nothing(self):
        self.open_one()
        self.assertEqual(detect.open_incidents(), [])


class SeenBeforeTest(StoreTestCase):
    # sara.y logged in from the same IP earlier that night, then the burst came.
    events = [("2026-11-23T20:00:00+03:00", "sara.y", ATTACKER, 1)] + burst("sara.y")

    def test_ip_seen_before(self):
        incident = store.get_incident(self.open_one())
        self.assertTrue(incident["ipSeenBefore"])


class HomeTest(StoreTestCase):
    def test_investigating(self):
        incident_id = self.open_one()
        home = store.home_summary()
        self.assertEqual(home["monitor"]["accountsMonitored"], 2)
        self.assertEqual(home["monitor"]["status"], "investigating")
        self.assertRegex(home["monitor"]["lastCheckAt"], ISO_RIYADH)
        self.assertEqual(home["openIncident"]["id"], incident_id)
        self.assertEqual(home["openIncident"]["username"], "majed.f")
        self.assertEqual(home["decided"], [])

    def test_rules_report_shows_ok_status(self):
        # No AI investigator yet, so a rules report is normal, not a failure (project rule).
        self.ready_report(self.open_one(), source="rules")
        home = store.home_summary()
        self.assertEqual(home["monitor"]["status"], "ok")
        self.assertEqual(home["openIncident"]["reportSource"], "rules")

    def test_ai_report_shows_ok_status(self):
        self.ready_report(self.open_one(), source="ai")
        self.assertEqual(store.home_summary()["monitor"]["status"], "ok")

    def test_no_incidents(self):
        home = store.home_summary()
        self.assertIsNone(home["openIncident"])
        self.assertEqual(home["monitor"]["status"], "ok")

    def test_after_decision(self):
        incident_id = self.open_one()
        self.ready_report(incident_id)
        store.record_decision(incident_id, "restore")
        home = store.home_summary()
        self.assertIsNone(home["openIncident"])
        self.assertEqual(home["decided"][0]["id"], incident_id)
        self.assertEqual(home["decided"][0]["decision"]["choice"], "restore")


class ReportTest(StoreTestCase):
    def test_unknown_incident(self):
        self.assertIsNone(store.get_incident(999))

    def test_report_shape(self):
        incident_id = self.open_one()
        self.ready_report(incident_id)
        report = store.get_incident(incident_id)
        self.assertEqual(report["account"]["displayName"], "ماجد بن فهد بن عبدالرحمن العتيبي")
        self.assertEqual(len(report["logs"]), 11)
        self.assertEqual(report["logs"][0], {
            "id": "evt-1", "at": "2026-11-23T23:00:00+03:00", "event": "LOGIN_FAIL",
            "username": "majed.f", "ip": ATTACKER,
        })
        self.assertEqual(report["logs"][-1]["event"], "LOGIN_SUCCESS")
        self.assertEqual(report["firstFailAt"], "2026-11-23T23:00:00+03:00")
        self.assertEqual(report["lastFailAt"], "2026-11-23T23:00:09+03:00")
        self.assertEqual(report["successAt"], "2026-11-23T23:02:07+03:00")
        self.assertEqual(report["findings"], [
            {"kind": "failed_attempts", "confirmed": True, "evidenceLogIds": ["evt-1", "evt-2"]},
            {"kind": "seen_before", "confirmed": False, "evidenceLogIds": []},
        ])
        self.assertIsNone(report["decision"])


class DecisionTest(StoreTestCase):
    def test_not_allowed_while_investigating(self):
        incident_id = self.open_one()
        with self.assertRaises(store.DecisionNotAllowed):
            store.record_decision(incident_id, "restore")

    def test_unknown_incident(self):
        with self.assertRaises(store.IncidentNotFound):
            store.record_decision(999, "restore")

    def test_restore_reactivates_account(self):
        incident_id = self.open_one()
        self.ready_report(incident_id)
        saved = store.record_decision(incident_id, "restore")
        self.assertEqual(saved["choice"], "restore")
        self.assertRegex(saved["decidedAt"], ISO_RIYADH)
        self.assertEqual(account_status("majed.f"), "active")
        self.assertEqual(store.get_incident(incident_id)["status"], "decided")
        self.assertEqual(store.get_incident(incident_id)["decision"], saved)

    def test_keep_suspended_keeps_account_suspended(self):
        incident_id = self.open_one()
        self.ready_report(incident_id)
        store.record_decision(incident_id, "keep_suspended")
        self.assertEqual(account_status("majed.f"), "suspended")

    def test_only_once(self):
        incident_id = self.open_one()
        self.ready_report(incident_id)
        store.record_decision(incident_id, "keep_suspended")
        with self.assertRaises(store.DecisionNotAllowed):
            store.record_decision(incident_id, "restore")
        self.assertEqual(account_status("majed.f"), "suspended")  # the second try changed nothing
