"""Checks the investigator's three read-only tools and the 6-step cap. No AI needed."""

from helpers import ATTACKER, StoreTestCase, burst
from server import store
from server.investigation.steps import LIMIT_REACHED, MAX_STEPS, StepCounter
from server.investigation.tools import IncidentTools, ToolInputError

HOME_IP = "192.0.2.10"

# 1: majed.f's normal login earlier that evening.   2: sara.y (another account).
# 3-12: ten failures from the attacker.   13: the success (trigger).   14: a login after the incident.
EVENTS = ([("2026-11-23T20:00:00+03:00", "majed.f", HOME_IP, 1),
           ("2026-11-23T22:00:00+03:00", "sara.y", ATTACKER, 0)]
          + burst()
          + [("2026-11-23T23:30:00+03:00", "majed.f", ATTACKER, 1)])


def ids(result):
    return [line["log_id"] for line in result["lines"]]


class ToolsTest(StoreTestCase):
    events = EVENTS

    def setUp(self):
        super().setUp()
        self.incident_id = self.open_one()
        self.tools = IncidentTools(self.incident_id)

    # --- search_logs ----------------------------------------------------------

    def test_search_sees_only_this_account_up_to_the_trigger(self):
        found = self.tools.search_logs()
        self.assertEqual(ids(found), [1] + list(range(3, 14)))  # not 2 (sara.y), not 14 (after)
        self.assertEqual(found["account"], "majed.f")
        self.assertEqual((found["total"], found["shown"]), (12, 12))

    def test_search_line_shape(self):
        first = self.tools.search_logs()["lines"][0]
        self.assertEqual(first, {"log_id": 1, "time": "2026-11-23T20:00:00+03:00",
                                 "event": "LOGIN_SUCCESS", "source_ip": HOME_IP})

    def test_search_filters(self):
        self.assertEqual(ids(self.tools.run("search_logs", {"success": True})), [1, 13])
        self.assertEqual(ids(self.tools.run("search_logs", {"source_ip": HOME_IP})), [1])
        self.assertEqual(ids(self.tools.run("search_logs", {"from_time": "2026-11-23T23:00:05+03:00",
                                                            "to_time": "2026-11-23T23:00:07+03:00"})), [8, 9, 10])

    def test_time_without_offset_is_riyadh_time(self):
        found = self.tools.run("search_logs", {"from_time": "2026-11-23T23:02:00"})
        self.assertEqual(ids(found), [13])

    def test_time_in_utc_is_converted(self):
        found = self.tools.run("search_logs", {"to_time": "2026-11-23T17:00:00Z"})  # = 20:00 Riyadh
        self.assertEqual(ids(found), [1])

    # --- count_events ---------------------------------------------------------

    def test_count(self):
        self.assertEqual(self.tools.run("count_events", {}), {"account": "majed.f", "count": 12})
        self.assertEqual(self.tools.run("count_events", {"success": False, "source_ip": ATTACKER})["count"], 10)

    # --- build_timeline -------------------------------------------------------

    def test_timeline_is_the_incident_with_gaps(self):
        timeline = self.tools.run("build_timeline", {})["lines"]
        self.assertEqual([line["log_id"] for line in timeline], list(range(3, 14)))
        self.assertIsNone(timeline[0]["seconds_since_previous"])
        self.assertEqual(timeline[1]["seconds_since_previous"], 1)
        self.assertEqual(timeline[-1]["seconds_since_previous"], 118)  # 23:00:09 -> 23:02:07

    # --- bad input ------------------------------------------------------------

    def test_bad_input_is_refused(self):
        for tool, tool_input in [
            ("search_logs", {"account": "sara.y"}),     # cannot widen the scope
            ("search_logs", {"success": "yes"}),
            ("search_logs", {"success": 1}),
            ("search_logs", {"from_time": "yesterday"}),
            ("search_logs", {"source_ip": 42}),
            ("count_events", {"to_time": 5}),
            ("build_timeline", {"source_ip": ATTACKER}),
            ("search_logs", "all of them"),
        ]:
            with self.subTest(tool=tool, tool_input=tool_input), self.assertRaises(ToolInputError):
                self.tools.run(tool, tool_input)

    def test_unknown_incident(self):
        with self.assertRaises(store.IncidentNotFound):
            IncidentTools(999)

    def test_tools_change_nothing(self):
        before = store.get_incident(self.incident_id)
        for tool in ("search_logs", "count_events", "build_timeline"):
            self.tools.run(tool, {})
        self.assertEqual(store.get_incident(self.incident_id), before)


class SearchLimitTest(StoreTestCase):
    events = burst(fails=60)

    def test_search_shows_at_most_50_but_counts_all(self):
        found = IncidentTools(self.open_one()).search_logs()
        self.assertEqual((found["total"], found["shown"], len(found["lines"])), (61, 50, 50))


class StepCounterTest(StoreTestCase):
    events = EVENTS

    def setUp(self):
        super().setUp()
        self.incident_id = self.open_one()
        self.attempt_id = store.start_attempt(self.incident_id)
        self.steps = StepCounter(self.attempt_id, IncidentTools(self.incident_id))

    def test_six_steps_run_and_are_saved_the_seventh_is_refused(self):
        for _ in range(MAX_STEPS):
            self.assertFalse(self.steps.call("count_events", {})["is_error"])
        seventh = self.steps.call("search_logs", {})
        self.assertEqual(seventh, {"is_error": True, "output": {"error": LIMIT_REACHED}})
        saved = store.attempt_steps(self.attempt_id)
        self.assertEqual([s["step_no"] for s in saved], [1, 2, 3, 4, 5, 6])
        self.assertEqual(saved[0]["tool_output"], {"account": "majed.f", "count": 12})

    def test_sixth_step_says_it_was_the_last(self):
        for _ in range(MAX_STEPS - 1):
            self.assertNotIn("note", self.steps.call("count_events", {})["output"])
        self.assertIn("last step", self.steps.call("count_events", {})["output"]["note"])

    def test_bad_input_uses_a_step_and_is_saved(self):
        result = self.steps.call("search_logs", {"success": "yes"})
        self.assertTrue(result["is_error"])
        self.assertEqual(self.steps.used, 1)
        [saved] = store.attempt_steps(self.attempt_id)
        self.assertEqual(saved["tool_input"], {"success": "yes"})
        self.assertIn("error", saved["tool_output"])

    def test_unknown_tool_is_our_bug(self):
        with self.assertRaises(ValueError):
            self.steps.call("Bash", {"command": "dir"})
        self.assertEqual(self.steps.used, 0)

    def test_a_retry_gets_a_fresh_counter(self):
        for _ in range(MAX_STEPS + 2):
            self.steps.call("count_events", {})
        with store._connection() as conn, conn:  # end the first attempt by hand (task B does this)
            conn.execute("UPDATE investigation_attempts SET outcome = 'failed', failure_reason = 'turn_limit',"
                         " finished_at = 'x' WHERE id = ?", (self.attempt_id,))
        second = store.start_attempt(self.incident_id)
        retry = StepCounter(second, IncidentTools(self.incident_id))
        self.assertFalse(retry.call("build_timeline", {})["is_error"])
        self.assertEqual([s["step_no"] for s in store.attempt_steps(second)], [1])

    def test_two_running_attempts_are_refused(self):
        with self.assertRaises(store.AttemptAlreadyRunning):
            store.start_attempt(self.incident_id)

    def test_attempt_for_unknown_incident(self):
        with self.assertRaises(store.IncidentNotFound):
            store.start_attempt(999)
