"""The evidence check: every finding must point to a real log line of THIS incident.

Both investigators (rules and Claude) save their report through save_checked_report.
A log id is kept only if it belongs to the incident and fits the finding's kind:

  failed_attempts  a LOGIN_FAIL line of the incident
  success_time     the triggering success line only
  source_ip        an incident line from the incident's address
  duration         any incident line (the first and last ones show the time span)
  seen_before      if the address was seen before: an earlier successful login of this
                   account from that address; if not: the triggering success line,
                   which shows the new address (the same rule the rules writer uses)

"The incident's lines" = this account's lines from first_fail_log_id to trigger_log_id.
Any other id (another account, outside the range, made up, not a number) is dropped.
A finding left with no log line is saved as confirmed = False, and the Report shows «(غير مؤكد)».
"""

from server import store

FINDING_KINDS = ("failed_attempts", "success_time", "source_ip", "duration", "seen_before")


def allowed_log_ids(data):
    """For each kind, the set of log ids that may back it. data = store.investigation_input(...)."""
    lines = data["lines"]
    trigger = {data["trigger_log_id"]}
    return {
        "failed_attempts": {line["id"] for line in lines if not line["success"]},
        "success_time": trigger,
        "source_ip": {line["id"] for line in lines if line["source_ip"] == data["source_ip"]},
        "duration": {line["id"] for line in lines},
        "seen_before": set(data["seen_before_log_ids"]) if data["ip_seen_before"] else trigger,
    }


def check_findings(incident_id, findings):
    """Return the findings with unfit log ids removed and `confirmed` set from what is left.

    findings: [{"kind": "failed_attempts", "log_ids": [1479, ...]}, ...]
    An unknown kind is dropped (the database would refuse it anyway); so is a repeated kind
    (the first one wins). If there is no such incident, nothing can be confirmed.
    """
    data = store.investigation_input(incident_id)
    allowed = allowed_log_ids(data) if data else {}
    checked = []
    for finding in findings:
        kind = finding.get("kind")
        if kind not in FINDING_KINDS or any(c["kind"] == kind for c in checked):
            continue
        fits = allowed.get(kind, set())
        # bool is a kind of int in Python (True == 1), so it is refused by name.
        cited = [i for i in finding.get("log_ids") or [] if isinstance(i, int) and not isinstance(i, bool)]
        # dict.fromkeys keeps the order and removes duplicates.
        log_ids = [i for i in dict.fromkeys(cited) if i in fits]
        checked.append({"kind": kind, "confirmed": bool(log_ids), "log_ids": log_ids})
    return checked


def save_checked_report(incident_id, report_source, headline_ar, summary_ar, findings):
    """Check the evidence, then store the report. The incident becomes awaiting_decision."""
    store.save_report(incident_id, report_source, headline_ar, summary_ar,
                      check_findings(incident_id, findings))
