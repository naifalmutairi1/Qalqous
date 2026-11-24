"""The Qalqous API: what the Home and Report screens call.

Run from the project root (127.0.0.1 = this laptop only, never the network):
    uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload

Routes only check the request and turn store errors into HTTP answers.
All database work happens in store.py.
"""

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from server import store

app = FastAPI(title="Qalqous")


class DecisionIn(BaseModel):
    # Literal = only these two exact values. Anything else gets an automatic 422 error.
    choice: Literal["keep_suspended", "restore"]


@app.get("/api/home")
def home():
    """Status strip, the open incident (or none), last decision and previous reports."""
    return store.home_summary()


@app.get("/api/incidents/{incident_id}")
def incident(incident_id: int):
    """One full report: facts, findings, evidence log lines and the decision if any."""
    found = store.get_incident(incident_id)
    if found is None:
        raise HTTPException(status_code=404, detail="لا يوجد حادث بهذا الرقم.")
    if found["status"] == "investigating":
        raise HTTPException(status_code=409, detail="التقرير لم يجهز بعد.")
    return found


@app.post("/api/incidents/{incident_id}/decision")
def decide(incident_id: int, body: DecisionIn):
    """Save the admin's decision. Allowed once, and only when the report is ready."""
    try:
        return store.record_decision(incident_id, body.choice)
    except store.IncidentNotFound:
        raise HTTPException(status_code=404, detail="لا يوجد حادث بهذا الرقم.")
    except store.DecisionNotAllowed:
        raise HTTPException(
            status_code=409, detail="لا يمكن تسجيل القرار: سُجّل قرار من قبل، أو أن التقرير لم يجهز بعد."
        )
