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
    return datetime.strptime(time_text, "%Y-%m-%d %H:%M:%S")


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


def open_incidents(conn):
    """Open one incident per match. Running again does not create duplicates."""
    opened = []
    for account, success, failures in find_suspicious(conn):
        already = conn.execute(
            "SELECT id FROM incidents WHERE trigger_log_id = ?", (success["id"],)
        ).fetchone()
        if already:
            continue
        cur = conn.execute(
            "INSERT INTO incidents (status, opened_at, account, source_ip, trigger_log_id) "
            "VALUES ('open', ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), account, success["source_ip"], success["id"]),
        )
        opened.append((cur.lastrowid, account, success, failures))
    conn.commit()
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
    total = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    print(f"Incidents in database: {total}")


if __name__ == "__main__":
    main()
