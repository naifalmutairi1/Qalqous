"""Detect suspicious logins and open incidents.

Rule (agreed in the plan): for one account, 5 or more FAILED logins
within the 10 minutes before a SUCCESSFUL login.

Run:  python detect.py
"""

from datetime import datetime, timedelta

from db import connect

MIN_FAILURES = 5
WINDOW = timedelta(minutes=10)


def parse(time_text):
    return datetime.fromisoformat(time_text)  # reads 2026-11-21T23:41:07+03:00


def find_suspicious(conn):
    """Return a list of (account, success_row, failure_rows) that match the rule."""
    matches = []
    accounts = [r["account"] for r in conn.execute("SELECT DISTINCT account FROM log_events")]

    for account in accounts:
        rows = conn.execute(
            "SELECT * FROM log_events WHERE account = ? ORDER BY time, id", (account,)
        ).fetchall()

        recent_failures = []  # failures since this account's last success
        for row in rows:
            if not row["success"]:
                recent_failures.append(row)
                continue

            # A success: count the failures that happened in the 10 minutes before it.
            success_time = parse(row["time"])
            in_window = [f for f in recent_failures if success_time - parse(f["time"]) <= WINDOW]
            if len(in_window) >= MIN_FAILURES:
                matches.append((account, row, in_window))
            recent_failures = []  # a success "resets" the count

    return matches


def ip_seen_before(conn, account, ip, before_log_id):
    """True if this account logged in successfully from this IP earlier in the logs."""
    row = conn.execute(
        "SELECT 1 FROM log_events WHERE account = ? AND source_ip = ? AND success = 1 AND id < ?",
        (account, ip, before_log_id),
    ).fetchone()
    return row is not None


def open_incidents(conn):
    """Open one incident per match and suspend the account (simulated data only).

    Running again does not create duplicates: a success line already used
    is skipped, and so is an account that already has an undecided incident.
    """
    opened = []
    for account, success, failures in find_suspicious(conn):
        already = conn.execute(
            "SELECT id FROM incidents WHERE trigger_log_id = ? OR (account = ? AND status != 'decided')",
            (success["id"], account),
        ).fetchone()
        if already:
            continue
        access = conn.execute(
            "SELECT access_ar FROM accounts WHERE username = ?", (account,)
        ).fetchone()["access_ar"]
        # "with conn" is one transaction: the incident and the suspension
        # are saved together, or neither is.
        with conn:
            cur = conn.execute(
                "INSERT INTO incidents (account, first_fail_log_id, trigger_log_id, source_ip,"
                " failed_attempts, ip_seen_before, access_ar) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    account,
                    failures[0]["id"],
                    success["id"],
                    success["source_ip"],
                    len(failures),
                    1 if ip_seen_before(conn, account, success["source_ip"], success["id"]) else 0,
                    access,
                ),
            )
            conn.execute("UPDATE accounts SET status = 'suspended' WHERE username = ?", (account,))
        opened.append((cur.lastrowid, account, success, failures))
    return opened


def main():
    conn = connect()
    opened = open_incidents(conn)
    if not opened:
        print("No new incidents.")
    for incident_id, account, success, failures in opened:
        print(f"Incident #{incident_id} opened: account={account}, address={success['source_ip']}")
        print(f"  {len(failures)} failures (log lines {failures[0]['id']}-{failures[-1]['id']}),"
              f" then success at log line {success['id']} ({success['time']})")
        print(f"  Account {account} is now suspended (simulated).")
    total = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    print(f"Incidents in database: {total}")


if __name__ == "__main__":
    main()
