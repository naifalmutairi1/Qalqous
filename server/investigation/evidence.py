"""The evidence check: every finding must point to a real log line.

Both investigators (rules now, Claude later) save their report through save_checked_report.
A log id that does not exist is dropped. A finding left with no log line is saved
as confirmed = False, and the Report shows «(غير مؤكد)» next to it.
"""

from server import store

FINDING_KINDS = ("failed_attempts", "success_time", "source_ip", "duration", "seen_before")


def check_findings(findings):
    """Return the findings with fake log ids removed and `confirmed` set from what is left.

    findings: [{"kind": "failed_attempts", "log_ids": [1479, ...]}, ...]
    An unknown kind is dropped: the database would refuse it anyway.
    """
    findings = [f for f in findings if f["kind"] in FINDING_KINDS]
    cited = {log_id for f in findings for log_id in f["log_ids"] if isinstance(log_id, int)}
    real = store.known_log_ids(cited)
    checked = []
    for finding in findings:
        # dict.fromkeys keeps the order and removes duplicates.
        log_ids = [i for i in dict.fromkeys(finding["log_ids"]) if i in real]
        checked.append({"kind": finding["kind"], "confirmed": bool(log_ids), "log_ids": log_ids})
    return checked


def save_checked_report(incident_id, report_source, headline_ar, summary_ar, findings):
    """Check the evidence, then store the report. The incident becomes awaiting_decision."""
    store.save_report(incident_id, report_source, headline_ar, summary_ar, check_findings(findings))
