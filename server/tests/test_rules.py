"""Checks the rule-based report writer and the evidence check."""

from helpers import ATTACKER, StoreTestCase, burst
from server import store
from server.investigation import rules
from server.investigation.evidence import check_findings


def findings_by_kind(incident):
    return {f["kind"]: f for f in incident["findings"]}


class RuleReportTest(StoreTestCase):
    def test_report_is_written_and_awaits_decision(self):
        incident_id = self.open_one()
        self.assertTrue(rules.write_report(incident_id))
        incident = store.get_incident(incident_id)
        self.assertEqual(incident["status"], "awaiting_decision")
        self.assertEqual(incident["reportSource"], "rules")
        self.assertEqual(incident["headline"], "أوقفنا حساب majed.f مؤقتاً: احتمال دخول غير مصرّح به")
        self.assertIn("١٠ محاولات", incident["summary"])

    def test_every_finding_points_to_log_lines(self):
        incident_id = self.open_one()
        rules.write_report(incident_id)
        found = findings_by_kind(store.get_incident(incident_id))
        self.assertEqual(set(found), {"failed_attempts", "success_time", "source_ip", "duration", "seen_before"})
        self.assertTrue(all(f["confirmed"] for f in found.values()))
        self.assertEqual(len(found["failed_attempts"]["evidenceLogIds"]), 10)
        self.assertEqual(found["success_time"]["evidenceLogIds"], ["evt-11"])  # the 11th line
        self.assertEqual(found["duration"]["evidenceLogIds"], ["evt-1", "evt-10"])

    def test_decision_allowed_after_report(self):
        incident_id = self.open_one()
        rules.write_report(incident_id)
        self.assertEqual(store.record_decision(incident_id, "restore")["choice"], "restore")

    def test_unknown_incident(self):
        self.assertFalse(rules.write_report(999))


class SeenBeforeEvidenceTest(StoreTestCase):
    # Line 1: an earlier normal login of sara.y from the same address.
    events = [("2026-11-23T20:00:00+03:00", "sara.y", ATTACKER, 1)] + burst("sara.y")

    def test_seen_before_points_to_the_earlier_login(self):
        incident_id = self.open_one()
        rules.write_report(incident_id)
        found = findings_by_kind(store.get_incident(incident_id))
        self.assertEqual(found["seen_before"]["evidenceLogIds"], ["evt-1"])
        self.assertIn("من قبل", store.get_incident(incident_id)["summary"])


class EvidenceCheckTest(StoreTestCase):
    def test_fake_log_id_is_rejected_and_unconfirmed(self):
        checked = check_findings([
            {"kind": "failed_attempts", "log_ids": [1, 2, 99999]},
            {"kind": "seen_before", "log_ids": [99999]},
            {"kind": "duration", "log_ids": []},
            {"kind": "made_up", "log_ids": [1]},
        ])
        self.assertEqual(checked, [
            {"kind": "failed_attempts", "confirmed": True, "log_ids": [1, 2]},
            {"kind": "seen_before", "confirmed": False, "log_ids": []},
            {"kind": "duration", "confirmed": False, "log_ids": []},
        ])
