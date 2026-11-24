"""The rule-based report writer: the fallback from CLAUDE.md. No AI, only templates.

It reads the incident's log lines (through store.py), points each of the five findings
at the lines that prove it, and saves with report_source = 'rules'.
"""

from server import store
from server.investigation.evidence import save_checked_report

# 0-9 -> ٠-٩, for the Arabic text we store (the UI shows Arabic-Indic digits too).
ARABIC_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def attempts_word(n):
    """Arabic counted noun: 3-10 take the plural «محاولات», 11 and up the singular «محاولة»."""
    return "محاولات" if 3 <= n <= 10 else "محاولة"


def build_findings(data):
    """The five findings, each with the log line ids that back it."""
    lines = data["lines"]
    fails = [line["id"] for line in lines if not line["success"]]
    trigger = [line["id"] for line in lines if line["id"] == data["trigger_log_id"]]
    from_ip = [line["id"] for line in lines if line["source_ip"] == data["source_ip"]]

    if data["ip_seen_before"]:
        # Proof: the earlier successful login from the same address.
        seen = [data["seen_before_log_id"]] if data["seen_before_log_id"] else []
    else:
        # "First time" cannot be shown by a past line; the successful login shows the new address.
        seen = trigger

    return [
        {"kind": "failed_attempts", "log_ids": fails},
        {"kind": "success_time", "log_ids": trigger},
        {"kind": "source_ip", "log_ids": from_ip},
        {"kind": "duration", "log_ids": [fails[0], fails[-1]] if fails else []},
        {"kind": "seen_before", "log_ids": seen},
    ]


def write_report(incident_id):
    """Write and save the rule-based report. Returns False if there is no such incident."""
    data = store.investigation_input(incident_id)
    if data is None:
        return False

    n = data["failed_attempts"]
    where = "من عنوان دخل منه هذا الحساب من قبل" if data["ip_seen_before"] else "من عنوان جديد"
    headline = f"أوقفنا حساب {data['account']} مؤقتاً: احتمال دخول غير مصرّح به"
    summary = f"{str(n).translate(ARABIC_DIGITS)} {attempts_word(n)} فاشلة ثم دخول ناجح {where}."

    save_checked_report(incident_id, "rules", headline, summary, build_findings(data))
    return True
