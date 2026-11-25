"""Smoke test: start the real API and call every endpoint, against a temporary database.

Run from the project root, with the venv active:
    python server/tests/smoke_api.py

Not picked up by `unittest discover` (its name does not start with test_),
because it starts a server and takes a few seconds.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORT = 8765  # not 8000, so it never collides with your dev server
BASE = f"http://127.0.0.1:{PORT}"


def call(method, path, body=None):
    """Return (status code, JSON body)."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def check(label, ok):
    print(("PASS " if ok else "FAIL ") + label)
    if not ok:
        raise SystemExit(1)


def main():
    tmp = tempfile.mkdtemp()
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{Path(tmp) / 'smoke.db'}", "PYTHONIOENCODING": "utf-8"}

    # The same steps as the demo, but into the temporary database.
    subprocess.run([sys.executable, "generate_logs.py", "--seed", "7"], cwd=ROOT, env=env, check=True,
                   stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, "detect.py", "--rules-only"], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(50):  # wait up to 10 s for the server to start
            try:
                call("GET", "/api/home")
                break
            except urllib.error.URLError:
                time.sleep(0.2)

        status, home = call("GET", "/api/home")
        check("GET /api/home -> 200", status == 200)
        check("  open incident is majed.f", home["openIncident"]["username"] == "majed.f")
        check("  rule-based report is ready", home["openIncident"]["status"] == "awaiting_decision")
        check("  25 accounts monitored", home["monitor"]["accountsMonitored"] == 25)
        incident_id = home["openIncident"]["id"]

        status, _ = call("GET", "/api/incidents/999")
        check("GET unknown incident -> 404", status == 404)

        status, _ = call("POST", f"/api/incidents/{incident_id}/decision", {"choice": "approve"})
        check("POST decision 'approve' -> 422", status == 422)

        status, report = call("GET", f"/api/incidents/{incident_id}")
        check("GET report when ready -> 200", status == 200)
        check("  10 failures + 1 success in the evidence log",
              [line["event"] for line in report["logs"]].count("LOGIN_FAIL") == 10
              and report["logs"][-1]["event"] == "LOGIN_SUCCESS")
        check("  rules report with 5 confirmed findings",
              report["reportSource"] == "rules" and len(report["findings"]) == 5
              and all(f["confirmed"] and f["evidenceLogIds"] for f in report["findings"]))
        check("  account shown as suspended", report["account"]["status"] == "suspended")

        status, home = call("GET", "/api/home")
        check("  Home: calm strip, card says rules report",
              home["monitor"]["status"] == "ok" and home["openIncident"]["reportSource"] == "rules")

        status, saved = call("POST", f"/api/incidents/{incident_id}/decision", {"choice": "restore"})
        check("POST decision 'restore' -> 200 with time", status == 200 and saved["decidedAt"].endswith("+03:00"))

        status, _ = call("POST", f"/api/incidents/{incident_id}/decision", {"choice": "keep_suspended"})
        check("POST a second decision -> 409", status == 409)

        status, report = call("GET", f"/api/incidents/{incident_id}")
        check("  account is active again after restore", report["account"]["status"] == "active")

        status, home = call("GET", "/api/home")
        check("  Home: no open incident, decision is first in the list",
              home["openIncident"] is None and home["decided"][0]["decision"] == saved)
        print("All smoke checks passed.")
    finally:
        server.terminate()
        server.wait()


if __name__ == "__main__":
    main()
