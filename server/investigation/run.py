"""The one entry point: investigate(incident_id).

1. A run left 'running' for over 3 minutes (its program was killed) is closed as 'interrupted'.
2. If ANTHROPIC_API_KEY is set, the AI is skipped ('api_key_set'), so nothing is billed to a key.
3. Otherwise an attempt starts, and the AI investigates under a 120-second timeout.
4. Valid output: the evidence check runs, the report is saved as 'ai', the attempt as 'ai'.
5. Any failure: the attempt is saved as 'failed' with its reason, and the rule-based
   writer makes the report instead. So the incident always gets a report.
If the admin decided while the AI was working, the late report is dropped ('discarded'):
the decision always wins.
"""

import asyncio
import os
from datetime import datetime, timedelta

from server import store
from server.investigation import agent, rules
from server.investigation.evidence import save_checked_report
from server.investigation.report_model import InvalidReport, validate_report
from server.investigation.steps import StepCounter
from server.investigation.tools import RIYADH, IncidentTools

TIMEOUT_SECONDS = 120
STALE_AFTER = timedelta(minutes=3)  # longer than the timeout, so a live run is never closed


def investigate(incident_id, run_agent=None):
    """Investigate one incident and save a report. For detect.py (not async).

    Returns {"reportSource": "ai" | "rules" | None, "aiFailed": bool, "reason": text or None}.
    Raises store.IncidentNotFound, or store.AttemptAlreadyRunning if a run is going on now.
    run_agent: tests pass a fake here, so they need neither the SDK nor a login.
    """
    return asyncio.run(investigate_async(incident_id, run_agent))


async def investigate_async(incident_id, run_agent=None):
    """The same, for async callers (the retry endpoint in task C)."""
    run_agent = run_agent or agent.run_agent
    data = store.investigation_input(incident_id)
    if data is None:
        raise store.IncidentNotFound(incident_id)

    cutoff = (datetime.now(RIYADH) - STALE_AFTER).isoformat(timespec="seconds")
    store.close_stale_attempts(incident_id, cutoff)

    attempt_id = store.start_attempt(incident_id)
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _fall_back(incident_id, attempt_id, "api_key_set", "ANTHROPIC_API_KEY is set; AI skipped")

    try:
        steps = StepCounter(attempt_id, IncidentTools(incident_id))
        raw = await asyncio.wait_for(run_agent(data, steps), TIMEOUT_SECONDS)
        report = validate_report(raw, data)
    except agent.AgentFailure as failure:
        return _fall_back(incident_id, attempt_id, failure.reason, failure.detail)
    except InvalidReport as error:
        return _fall_back(incident_id, attempt_id, "invalid_output", str(error))
    except TimeoutError:  # asyncio.wait_for raises the built-in TimeoutError (Python 3.11+)
        return _fall_back(incident_id, attempt_id, "timeout", f"no report after {TIMEOUT_SECONDS} s")
    except Exception as error:  # anything else: still close the attempt and still write a report
        return _fall_back(incident_id, attempt_id, "sdk_error", f"{type(error).__name__}: {error}")

    saved = save_checked_report(incident_id, "ai", report["headline_ar"], report["summary_ar"],
                                report["findings"])
    store.finish_attempt(attempt_id, "ai" if saved else "discarded")
    if not saved:
        return {"reportSource": None, "aiFailed": False, "reason": "already decided"}
    return {"reportSource": "ai", "aiFailed": False, "reason": None}


def _fall_back(incident_id, attempt_id, reason, detail):
    """Record the failure, then write the rule-based report (unless already decided)."""
    store.finish_attempt(attempt_id, "failed", reason, str(detail)[:300])
    written = rules.write_report(incident_id)
    return {"reportSource": "rules" if written else None, "aiFailed": True, "reason": reason}
