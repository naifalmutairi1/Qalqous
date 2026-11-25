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
from server.investigation import run

app = FastAPI(title="Qalqous")

NOT_FOUND = "لا يوجد حادث بهذا الرقم."


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
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    if found["status"] == "investigating":
        raise HTTPException(status_code=409, detail="التقرير لم يجهز بعد.")
    return found


@app.post("/api/incidents/{incident_id}/decision")
def decide(incident_id: int, body: DecisionIn):
    """Save the admin's decision. Allowed once, and only when the report is ready."""
    try:
        return store.record_decision(incident_id, body.choice)
    except store.IncidentNotFound:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    except store.DecisionNotAllowed:
        raise HTTPException(
            status_code=409, detail="لا يمكن تسجيل القرار: سُجّل قرار من قبل، أو أن التقرير لم يجهز بعد."
        )


@app.post("/api/incidents/{incident_id}/investigation")
def retry_investigation(incident_id: int):
    """«أعد المحاولة»: run the AI investigation again. Waits until it ends (usually under 30 s, at most ~2 min).

    A plain `def` on purpose: FastAPI runs it in a worker thread, so Home and Report keep
    answering while the AI works, and run.investigate() makes its own event loop there.
    If the AI fails again, the rules report stays: still 200, with aiFailed = true.
    """
    found = store.incident_state(incident_id)
    if found is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    if found["status"] == "decided":
        raise HTTPException(status_code=409, detail="سُجّل القرار، لا حاجة لإعادة التحقيق.")
    if found["reportSource"] == "ai":
        raise HTTPException(status_code=409, detail="التقرير التفصيلي جاهز.")
    try:
        result = run.investigate(incident_id)
    except store.AttemptAlreadyRunning:
        raise HTTPException(status_code=409, detail="التحقيق يعمل الآن.")
    except store.IncidentNotFound:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    if result["reportSource"] is None:  # the admin decided while the AI was working: the decision wins
        raise HTTPException(status_code=409, detail="سُجّل القرار، لا حاجة لإعادة التحقيق.")
    return {"reportSource": result["reportSource"], "aiFailed": result["aiFailed"]}
