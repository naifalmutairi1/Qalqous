"""Detect suspicious logins and open incidents.

Rule (agreed in the plan): for one account, 5 or more FAILED logins
within the 10 minutes before a SUCCESSFUL login.

Run:  python detect.py               the AI investigates each new incident (up to 2 minutes),
                                    with the rule-based report if that fails.
      python detect.py --rules-only  no AI: the rule-based report only (tests, no login).
"""

import sys
from datetime import datetime, timedelta

from server import store
from server.investigation import rules
from server.investigation.run import investigate

MIN_FAILURES = 5
WINDOW = timedelta(minutes=10)


def parse(time_text):
    return datetime.fromisoformat(time_text)  # reads 2026-11-21T23:41:07+03:00


def find_suspicious():
    """Return a list of (account, success_line, failure_lines) that match the rule."""
    matches = []
    for account, lines in store.logins_by_account().items():
        recent_failures = []  # failures since this account's last success
        for line in lines:
            if not line["success"]:
                recent_failures.append(line)
                continue

            # A success: count the failures that happened in the 10 minutes before it.
            success_time = parse(line["time"])
            in_window = [f for f in recent_failures if success_time - parse(f["time"]) <= WINDOW]
            if len(in_window) >= MIN_FAILURES:
                matches.append((account, line, in_window))
            recent_failures = []  # a success "resets" the count

    return matches


def open_incidents():
    """Open one incident per match and suspend the account (simulated data only).

    Running again does not create duplicates (store.open_incident skips them).
    """
    opened = []
    for account, success, failures in find_suspicious():
        incident_id = store.open_incident(account, failures[0]["id"], success["id"], len(failures))
        if incident_id is not None:
            opened.append((incident_id, account, success, failures))
    return opened


def main():
    rules_only = "--rules-only" in sys.argv[1:]
    opened = open_incidents()
    if not opened:
        print("No new incidents.")
    for incident_id, account, success, failures in opened:
        print(f"Incident #{incident_id} opened: account={account}, address={success['source_ip']}")
        print(f"  {len(failures)} failures (log lines {failures[0]['id']}-{failures[-1]['id']}),"
              f" then success at log line {success['id']} ({success['time']})")
        print(f"  Account {account} is now suspended (simulated).")
        if rules_only:
            rules.write_report(incident_id)
            print("  Rule-based report written (--rules-only); waiting for the admin's decision.")
            continue
        print("  The AI is investigating (up to 2 minutes)...", flush=True)
        result = investigate(incident_id)
        if result["aiFailed"]:
            print(f"  The AI investigation failed ({result['reason']}); rule-based report written instead.")
        else:
            print("  AI report written; waiting for the admin's decision.")
    print(f"Incidents in database: {store.count_incidents()}")


if __name__ == "__main__":
    main()
