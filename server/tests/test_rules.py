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
    # Line 1: sara.y (another account). Lines 2-11: majed.f fails, 12: the success (trigger).
    # Line 13: a later majed.f login, after the incident.
    events = ([("2026-11-23T22:00:00+03:00", "sara.y", ATTACKER, 0)] + burst()
              + [("2026-11-23T23:30:00+03:00", "majed.f", ATTACKER, 1)])

    def check(self, kind, log_ids):
        [finding] = check_findings(self.open_one(), [{"kind": kind, "log_ids": log_ids}])
        return finding

    def test_fake_log_id_is_rejected_and_unconfirmed(self):
        checked = check_findings(self.open_one(), [
            {"kind": "failed_attempts", "log_ids": [2, 3, 99999]},
            {"kind": "seen_before", "log_ids": [99999]},
            {"kind": "duration", "log_ids": []},
            {"kind": "made_up", "log_ids": [2]},
        ])
        self.assertEqual(checked, [
            {"kind": "failed_attempts", "confirmed": True, "log_ids": [2, 3]},
            {"kind": "seen_before", "confirmed": False, "log_ids": []},
            {"kind": "duration", "confirmed": False, "log_ids": []},
        ])

    def test_another_accounts_line_is_rejected(self):
        self.assertEqual(self.check("failed_attempts", [1]), {"kind": "failed_attempts", "confirmed": False, "log_ids": []})

    def test_line_after_the_incident_is_rejected(self):
        self.assertEqual(self.check("duration", [13])["log_ids"], [])

    def test_failed_attempts_takes_only_failures(self):
        self.assertEqual(self.check("failed_attempts", [2, 12])["log_ids"], [2])

    def test_success_time_takes_only_the_trigger(self):
        self.assertEqual(self.check("success_time", [11, 12, 13])["log_ids"], [12])

    def test_seen_before_new_address_takes_only_the_trigger(self):
        self.assertEqual(self.check("seen_before", [2, 12])["log_ids"], [12])

    def test_duplicates_bools_and_text_are_dropped(self):
        self.assertEqual(self.check("failed_attempts", [3, 3, True, "4", None, 2.0, 5])["log_ids"], [3, 5])

    def test_repeated_kind_keeps_the_first(self):
        checked = check_findings(self.open_one(), [
            {"kind": "success_time", "log_ids": [12]},
            {"kind": "success_time", "log_ids": []},
        ])
        self.assertEqual(checked, [{"kind": "success_time", "confirmed": True, "log_ids": [12]}])

    def test_missing_log_ids_is_unconfirmed(self):
        [finding] = check_findings(self.open_one(), [{"kind": "duration"}])
        self.assertFalse(finding["confirmed"])

    def test_unknown_incident_confirms_nothing(self):
        checked = check_findings(999, [{"kind": "failed_attempts", "log_ids": [2]}])
        self.assertEqual(checked, [{"kind": "failed_attempts", "confirmed": False, "log_ids": []}])


class SeenBeforeStrictTest(StoreTestCase):
    # 1: sara.y logged in from the attacker's address before. 2: a failed try from it, not a login.
    events = ([("2026-11-23T20:00:00+03:00", "sara.y", ATTACKER, 1),
               ("2026-11-23T20:05:00+03:00", "sara.y", ATTACKER, 0),
               ("2026-11-23T20:10:00+03:00", "sara.y", "192.0.2.50", 1)] + burst("sara.y"))

    def test_seen_before_takes_only_earlier_logins_from_that_address(self):
        [finding] = check_findings(self.open_one(), [{"kind": "seen_before", "log_ids": [1, 2, 3, 14]}])
        self.assertEqual(finding["log_ids"], [1])
