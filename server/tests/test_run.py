"""Checks investigate(): the AI path, every fallback, and the AI's output check.

No SDK and no login needed: a fake agent stands in for the AI.
"""

import asyncio
import os
from types import SimpleNamespace
from unittest import mock

from helpers import StoreTestCase
from server import store
from server.investigation import agent, run
from server.investigation.agent import AgentFailure
from server.investigation.report_model import InvalidReport, is_arabic, validate_report

# burst(): lines 1-10 are failures from 203.0.113.102, line 11 is the success (trigger).
GOOD = {
    "headline_ar": "أوقفنا حساب majed.f مؤقتاً: احتمال دخول غير مصرّح به",
    "summary_ar": "١٠ محاولات فاشلة ثم دخول ناجح من 203.0.113.102، وهو عنوان جديد. غيّر كلمة المرور.",
    "findings": [
        {"kind": "failed_attempts", "log_ids": list(range(1, 11))},
        {"kind": "success_time", "log_ids": [11]},
        {"kind": "source_ip", "log_ids": list(range(1, 12))},
        {"kind": "duration", "log_ids": [1, 10]},
        {"kind": "seen_before", "log_ids": [11]},
    ],
}


def returns(output):
    """A fake agent that answers at once with `output`."""
    async def fake(data, steps):
        return output
    return fake


def fails(reason):
    async def fake(data, steps):
        raise AgentFailure(reason, "fake failure")
    return fake


def findings_by_kind(incident_id):
    return {f["kind"]: f for f in store.get_incident(incident_id)["findings"]}


class InvestigateTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.incident_id = self.open_one()
        # Never let a test touch a real key, whatever is set on this machine.
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.addCleanup(patcher.stop)

    def investigate(self, fake):
        return run.investigate(self.incident_id, run_agent=fake)

    def attempt(self):
        [only] = store.attempts_of(self.incident_id)
        return only

    # --- the AI path --------------------------------------------------------

    def test_valid_output_is_saved_as_ai(self):
        self.assertEqual(self.investigate(returns(GOOD)), {"reportSource": "ai", "aiFailed": False, "reason": None})
        incident = store.get_incident(self.incident_id)
        self.assertEqual((incident["status"], incident["reportSource"]), ("awaiting_decision", "ai"))
        self.assertEqual(incident["headline"], GOOD["headline_ar"])
        self.assertTrue(all(f["confirmed"] for f in incident["findings"]))
        self.assertEqual(self.attempt()["outcome"], "ai")

    def test_fake_and_wrong_ids_become_unconfirmed(self):
        output = {**GOOD, "findings": [{"kind": "failed_attempts", "log_ids": [11, 99999]},  # a success, a fake
                                       {"kind": "success_time", "log_ids": [11]}]}
        self.investigate(returns(output))
        found = findings_by_kind(self.incident_id)
        self.assertEqual(set(found), {"failed_attempts", "success_time", "source_ip", "duration", "seen_before"})
        self.assertFalse(found["failed_attempts"]["confirmed"])
        self.assertTrue(found["success_time"]["confirmed"])
        self.assertFalse(found["duration"]["confirmed"])  # left out by the AI: «غير مؤكد»

    def test_tool_calls_are_saved_as_steps(self):
        async def fake(data, steps):
            steps.call("count_events", {"success": False})
            steps.call("build_timeline", {})
            return GOOD
        self.investigate(fake)
        saved = store.attempt_steps(self.attempt()["id"])
        self.assertEqual([(s["step_no"], s["tool"]) for s in saved], [(1, "count_events"), (2, "build_timeline")])
        self.assertEqual(saved[0]["tool_output"]["count"], 10)

    def test_looping_agent_is_capped_at_six_steps(self):
        async def fake(data, steps):
            results = [steps.call("count_events", {}) for _ in range(20)]
            self.assertTrue(all(r["is_error"] for r in results[6:]))
            return GOOD
        self.investigate(fake)
        self.assertEqual(len(store.attempt_steps(self.attempt()["id"])), 6)

    # --- every fallback writes the rules report -----------------------------

    def assert_fell_back(self, result, reason):
        self.assertEqual(result, {"reportSource": "rules", "aiFailed": True, "reason": reason})
        incident = store.get_incident(self.incident_id)
        self.assertEqual((incident["status"], incident["reportSource"]), ("awaiting_decision", "rules"))
        self.assertEqual((self.attempt()["outcome"], self.attempt()["failure_reason"]), ("failed", reason))
        self.assertIsNotNone(self.attempt()["finished_at"])

    def test_no_login(self):
        self.assert_fell_back(self.investigate(fails("no_login")), "no_login")

    def test_turn_limit(self):
        self.assert_fell_back(self.investigate(fails("turn_limit")), "turn_limit")

    def test_english_output(self):
        output = {**GOOD, "summary_ar": "Ten failed attempts, then a successful login from a new address."}
        self.assert_fell_back(self.investigate(returns(output)), "invalid_output")

    def test_broken_output(self):
        self.assert_fell_back(self.investigate(returns("not json")), "invalid_output")

    def test_timeout(self):
        async def slow(data, steps):
            await asyncio.sleep(5)
        with mock.patch.object(run, "TIMEOUT_SECONDS", 0.05):
            self.assert_fell_back(self.investigate(slow), "timeout")

    def test_unexpected_crash(self):
        async def crash(data, steps):
            raise KeyError("boom")
        self.assert_fell_back(self.investigate(crash), "sdk_error")
        self.assertIn("KeyError", self.attempt()["failure_detail"])

    def test_api_key_set_skips_the_ai(self):
        called = []
        async def fake(data, steps):
            called.append(True)
            return GOOD
        os.environ["ANTHROPIC_API_KEY"] = "sk-test-not-real"
        self.assert_fell_back(self.investigate(fake), "api_key_set")
        self.assertEqual(called, [])

    # --- races and leftovers ------------------------------------------------

    def test_decision_during_the_run_wins(self):
        self.ready_report(self.incident_id)
        async def decide_meanwhile(data, steps):
            store.record_decision(self.incident_id, "keep_suspended")
            return GOOD
        result = self.investigate(decide_meanwhile)
        self.assertEqual(result["reportSource"], None)
        incident = store.get_incident(self.incident_id)
        self.assertEqual(incident["status"], "decided")
        self.assertEqual(incident["headline"], "عنوان")  # the report the admin decided on is kept
        self.assertEqual(store.attempts_of(self.incident_id)[-1]["outcome"], "discarded")

    def test_a_second_run_at_once_is_refused(self):
        store.start_attempt(self.incident_id)  # a run that is going on right now
        with self.assertRaises(store.AttemptAlreadyRunning):
            self.investigate(returns(GOOD))

    def test_an_old_killed_run_is_closed_as_interrupted(self):
        stale = store.start_attempt(self.incident_id)
        with store._connection() as conn, conn:  # pretend it started 10 minutes ago
            conn.execute("UPDATE investigation_attempts SET created_at = '2000-01-01T00:00:00+03:00' WHERE id = ?",
                         (stale,))
        self.investigate(returns(GOOD))
        first, second = store.attempts_of(self.incident_id)
        self.assertEqual((first["outcome"], first["failure_reason"]), ("failed", "interrupted"))
        self.assertEqual(second["outcome"], "ai")

    def test_unknown_incident(self):
        with self.assertRaises(store.IncidentNotFound):
            run.investigate(999, run_agent=returns(GOOD))


class ReportModelTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.data = store.investigation_input(self.open_one())

    def test_good_output_gets_all_five_kinds(self):
        out = validate_report({**GOOD, "findings": GOOD["findings"][:2]}, self.data)
        self.assertEqual([f["kind"] for f in out["findings"]],
                         ["failed_attempts", "success_time", "source_ip", "duration", "seen_before"])
        self.assertEqual(out["findings"][3]["log_ids"], [])

    def test_refused_shapes(self):
        for label, raw in [
            ("extra field", {**GOOD, "risk": "high"}),
            ("text id", {**GOOD, "findings": [{"kind": "duration", "log_ids": ["1"]}]}),
            ("unknown kind", {**GOOD, "findings": [{"kind": "malware", "log_ids": [1]}]}),
            ("too many ids", {**GOOD, "findings": [{"kind": "duration", "log_ids": list(range(51))}]}),
            ("short headline", {**GOOD, "headline_ar": "حساب"}),
            ("missing summary", {"headline_ar": GOOD["headline_ar"], "findings": []}),
            ("a list", [GOOD]),
        ]:
            with self.subTest(label), self.assertRaises(InvalidReport):
                validate_report(raw, self.data)

    def test_arabic_check(self):
        allowed = {"majed.f", "203.0.113.102"}
        self.assertTrue(is_arabic("دخل majed.f من 203.0.113.102 الساعة ٢٣:٠٢", allowed))
        self.assertTrue(is_arabic("عنوان 2001:db8::7 جديد", allowed))
        self.assertFalse(is_arabic("دخل majed.f بعد brute force", allowed))
        self.assertFalse(is_arabic("majed.f 203.0.113.102", allowed))  # no Arabic at all
        self.assertFalse(is_arabic("حساب sara.y", allowed))  # another account's name is not allowed


class ResultMessageTest(StoreTestCase):
    """How the SDK's final message maps to a report or a failure reason (no SDK needed)."""

    def result(self, subtype="success", is_error=False, structured=None, text="", turns=3):
        return SimpleNamespace(subtype=subtype, is_error=is_error, structured_output=structured,
                               result=text, num_turns=turns)

    def reason(self, message):
        with self.assertRaises(AgentFailure) as caught:
            agent._from_result(message)
        return caught.exception.reason

    def test_success(self):
        self.assertEqual(agent._from_result(self.result(structured=GOOD)), GOOD)

    def test_json_only_in_text(self):
        self.assertEqual(agent._from_result(self.result(text='{"a": 1}')), {"a": 1})

    def test_failures(self):
        self.assertEqual(self.reason(self.result("error_max_turns", True)), "turn_limit")
        self.assertEqual(self.reason(self.result("error_max_structured_output_retries", True)), "invalid_output")
        self.assertEqual(self.reason(self.result("success", text="no json here")), "invalid_output")
        self.assertEqual(self.reason(self.result("error_during_execution", True, text="Not logged in")), "no_login")
        self.assertEqual(self.reason(self.result("error_during_execution", True, text="LOGIN_FAIL x")), "sdk_error")


class SaveReportTest(StoreTestCase):
    def test_no_report_after_the_decision(self):
        incident_id = self.open_one()
        self.ready_report(incident_id)
        store.record_decision(incident_id, "restore")
        self.assertFalse(store.save_report(incident_id, "ai", "عنوان جديد", "ملخص", []))
        incident = store.get_incident(incident_id)
        self.assertEqual((incident["headline"], len(incident["findings"])), ("عنوان", 2))
