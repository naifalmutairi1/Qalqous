"""Checks the Home status strip and the retry endpoint («أعد المحاولة»). No SDK or login needed.

The route function is called directly (no HTTP server); run.investigate is replaced by a
fake, or given a fake agent, so the AI never runs.
"""

import os
from unittest import mock

from fastapi import HTTPException

from helpers import StoreTestCase
from server import main, store
from server.investigation import run
from test_run import GOOD, fails, returns


def home_status():
    return store.home_summary()["monitor"]["status"]


def set_attempt(attempt_id, **columns):
    """Change an attempt by hand (tests only)."""
    sets = ", ".join(f"{name} = ?" for name in columns)
    with store._connection() as conn, conn:
        conn.execute(f"UPDATE investigation_attempts SET {sets} WHERE id = ?", (*columns.values(), attempt_id))


OLD = "2000-01-01T00:00:00+03:00"  # long before the 3-minute cut-off


class HomeStatusTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.incident_id = self.open_one()

    def test_no_attempt_and_no_report_is_investigating(self):
        self.assertEqual(home_status(), "investigating")

    def test_rules_only_report_is_calm(self):
        self.ready_report(self.incident_id, source="rules")  # like detect.py --rules-only: no attempt
        self.assertEqual(home_status(), "ok")

    def test_running_attempt_is_investigating_even_with_a_report(self):
        self.ready_report(self.incident_id, source="rules")
        store.start_attempt(self.incident_id)  # a retry is going on
        self.assertEqual(home_status(), "investigating")

    def test_failed_attempt_with_rules_report_is_error(self):
        attempt_id = store.start_attempt(self.incident_id)
        self.ready_report(self.incident_id, source="rules")
        store.finish_attempt(attempt_id, "failed", "no_login")
        self.assertEqual(home_status(), "error")

    def test_ai_report_is_calm(self):
        attempt_id = store.start_attempt(self.incident_id)
        self.ready_report(self.incident_id, source="ai")
        store.finish_attempt(attempt_id, "ai")
        self.assertEqual(home_status(), "ok")

    def test_killed_run_without_report_is_error(self):
        set_attempt(store.start_attempt(self.incident_id), created_at=OLD)
        self.assertEqual(home_status(), "error")

    def test_only_the_latest_attempt_counts(self):
        first = store.start_attempt(self.incident_id)
        store.finish_attempt(first, "failed", "timeout")
        second = store.start_attempt(self.incident_id)
        self.ready_report(self.incident_id, source="ai")
        store.finish_attempt(second, "ai")
        self.assertEqual(home_status(), "ok")


class RetryEndpointTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.incident_id = self.open_one()
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.addCleanup(patcher.stop)

    def retry(self, fake_agent=None):
        """Call the endpoint; the real run.investigate runs, with a fake agent instead of the AI."""
        real = run.investigate
        with mock.patch.object(run, "investigate", lambda i: real(i, run_agent=fake_agent)):
            return main.retry_investigation(self.incident_id)

    def assert_refused(self, status, detail, fake_agent=None, incident_id=None):
        with self.assertRaises(HTTPException) as caught:
            if incident_id is None:
                self.retry(fake_agent or returns(GOOD))
            else:
                main.retry_investigation(incident_id)
        self.assertEqual((caught.exception.status_code, caught.exception.detail), (status, detail))

    def fail_once(self):
        """The first AI attempt failed: a rules report and the error strip."""
        run.investigate(self.incident_id, run_agent=fails("no_login"))
        self.assertEqual(home_status(), "error")

    def test_retry_after_a_failure_gives_the_ai_report(self):
        self.fail_once()
        self.assertEqual(self.retry(returns(GOOD)), {"reportSource": "ai", "aiFailed": False})
        self.assertEqual(store.get_incident(self.incident_id)["reportSource"], "ai")
        self.assertEqual(home_status(), "ok")

    def test_second_failure_keeps_the_rules_report(self):
        self.fail_once()
        self.assertEqual(self.retry(fails("timeout")), {"reportSource": "rules", "aiFailed": True})
        incident = store.get_incident(self.incident_id)
        self.assertEqual((incident["status"], incident["reportSource"]), ("awaiting_decision", "rules"))
        self.assertEqual(home_status(), "error")

    def test_retry_after_a_killed_run_writes_a_report(self):
        set_attempt(store.start_attempt(self.incident_id), created_at=OLD)
        self.assertEqual(self.retry(returns(GOOD))["reportSource"], "ai")
        reasons = [a["failure_reason"] for a in store.attempts_of(self.incident_id)]
        self.assertEqual(reasons, ["interrupted", None])

    def test_unknown_incident(self):
        self.assert_refused(404, "لا يوجد حادث بهذا الرقم.", incident_id=999)

    def test_already_decided(self):
        self.fail_once()
        store.record_decision(self.incident_id, "restore")
        self.assert_refused(409, "سُجّل القرار، لا حاجة لإعادة التحقيق.")

    def test_already_an_ai_report(self):
        run.investigate(self.incident_id, run_agent=returns(GOOD))
        self.assert_refused(409, "التقرير التفصيلي جاهز.")

    def test_a_run_is_going_on(self):
        self.fail_once()
        store.start_attempt(self.incident_id)
        self.assert_refused(409, "التحقيق يعمل الآن.")

    def test_decision_during_the_retry_wins(self):
        self.fail_once()
        async def decide_meanwhile(data, steps):
            store.record_decision(self.incident_id, "keep_suspended")
            return GOOD
        self.assert_refused(409, "سُجّل القرار، لا حاجة لإعادة التحقيق.", fake_agent=decide_meanwhile)
        self.assertEqual(store.get_incident(self.incident_id)["decision"]["choice"], "keep_suspended")
