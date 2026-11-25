"""The investigator's three read-only tools: search_logs, count_events, build_timeline.

They are plain Python here, with no SDK, so unittest can check them without Claude.
(Task B wraps them for claude-agent-sdk.)

Each investigation makes its own IncidentTools, tied to one incident. Claude chooses only
the filters; it can never change the account or read past the triggering success.
They read through store.py's read-only connection and change nothing.
"""

from datetime import datetime, timedelta, timezone

from server import store

RIYADH = timezone(timedelta(hours=3))
SEARCH_LIMIT = 50  # at most this many lines per search_logs call
TOOL_NAMES = ("search_logs", "count_events", "build_timeline")


class ToolInputError(Exception):
    """Claude sent a filter we cannot use. The message goes back to Claude (in English)."""


def _event(success):
    return "LOGIN_SUCCESS" if success else "LOGIN_FAIL"


def _for_claude(line):
    """A log line as Claude sees it: plain values, the id as a bare integer."""
    return {"log_id": line["id"], "time": line["time"], "event": _event(line["success"]),
            "source_ip": line["source_ip"]}


def _time(value, name):
    """Check a time filter and write it the way the logs do: 2026-11-23T23:00:00+03:00.

    A time without an offset is read as Riyadh time. Text comparison in SQL then gives the
    right order, because every stored time has the same format and offset.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise ToolInputError(f"{name} must be an ISO 8601 time text")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ToolInputError(f"{name} is not an ISO 8601 time: {value[:40]}") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=RIYADH)
    return parsed.astimezone(RIYADH).isoformat(timespec="seconds")


def _filters(tool_input):
    """The optional filters shared by search_logs and count_events, checked."""
    unknown = set(tool_input) - {"source_ip", "success", "from_time", "to_time"}
    if unknown:
        raise ToolInputError(f"unknown filter: {', '.join(sorted(unknown))}")
    source_ip = tool_input.get("source_ip")
    if source_ip is not None and (not isinstance(source_ip, str) or len(source_ip) > 64):
        raise ToolInputError("source_ip must be a short text")
    success = tool_input.get("success")
    if success is not None and not isinstance(success, bool):
        raise ToolInputError("success must be true or false")
    return {
        "source_ip": source_ip,
        "success": success,
        "from_time": _time(tool_input.get("from_time"), "from_time"),
        "to_time": _time(tool_input.get("to_time"), "to_time"),
    }


class IncidentTools:
    """The three tools for one incident. Raises store.IncidentNotFound for an unknown id."""

    def __init__(self, incident_id):
        scope = store.incident_scope(incident_id)
        if scope is None:
            raise store.IncidentNotFound(incident_id)
        self.account = scope["account"]
        self.first_fail_log_id = scope["first_fail_log_id"]
        self.trigger_log_id = scope["trigger_log_id"]

    def run(self, tool, tool_input):
        """Run one tool by name. tool_input is the dict Claude sent. Returns a dict."""
        if not isinstance(tool_input, dict):
            raise ToolInputError("input must be an object")
        if tool == "search_logs":
            return self.search_logs(**_filters(tool_input))
        if tool == "count_events":
            return self.count_events(**_filters(tool_input))
        if tool == "build_timeline":
            if tool_input:
                raise ToolInputError("build_timeline takes no input")
            return self.build_timeline()
        raise ValueError(f"unknown tool: {tool}")  # our bug, not Claude's: the SDK offers only the three

    def search_logs(self, source_ip=None, success=None, from_time=None, to_time=None):
        """This account's lines up to the triggering success, oldest first, at most 50."""
        found = store.account_logs(self.account, self.trigger_log_id, source_ip=source_ip,
                                   success=success, from_time=from_time, to_time=to_time,
                                   limit=SEARCH_LIMIT)
        return {
            "account": self.account,
            "total": found["total"],
            "shown": len(found["lines"]),
            "lines": [_for_claude(line) for line in found["lines"]],
        }

    def count_events(self, source_ip=None, success=None, from_time=None, to_time=None):
        """How many of this account's lines (up to the triggering success) match."""
        found = store.account_logs(self.account, self.trigger_log_id, source_ip=source_ip,
                                   success=success, from_time=from_time, to_time=to_time, limit=0)
        return {"account": self.account, "count": found["total"]}

    def build_timeline(self):
        """The incident's lines in order (first failure to the triggering success),
        with the seconds since the line before."""
        found = store.account_logs(self.account, self.trigger_log_id,
                                   from_log_id=self.first_fail_log_id, limit=1000)
        timeline = []
        previous = None
        for line in found["lines"]:
            at = datetime.fromisoformat(line["time"])
            entry = _for_claude(line)
            entry["seconds_since_previous"] = None if previous is None else int((at - previous).total_seconds())
            timeline.append(entry)
            previous = at
        return {"account": self.account, "lines": timeline}
