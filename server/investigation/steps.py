"""The hard cap on the investigation: at most 6 tool calls (steps) per attempt.

Counted in OUR code, not by the SDK: the SDK's max_turns counts turns, and the AI can make
several tool calls in one turn. So every call goes through StepCounter.call:
  calls 1-6 run the tool and are saved to investigation_steps (with their step number);
  call 7 and later are refused without running, and not saved (step_no is capped at 6).
A call with bad input still uses up a step, so the AI cannot loop on mistakes for free.
"""

from server import store
from server.investigation.tools import TOOL_NAMES, ToolInputError

MAX_STEPS = 6
LIMIT_REACHED = "Step limit reached. Write the report now."


class StepCounter:
    """One counter for one attempt. tools = IncidentTools for the same incident."""

    def __init__(self, attempt_id, tools):
        self.attempt_id = attempt_id
        self.tools = tools
        self.used = 0

    def call(self, tool, tool_input):
        """Run one tool call. Returns {"is_error": bool, "output": dict}.

        The number is taken before anything else happens. The SDK runs our tools on one
        event loop, and this method never waits in between, so two calls in the same
        turn can never get the same number. That is why no lock is needed.
        """
        if tool not in TOOL_NAMES:
            raise ValueError(f"unknown tool: {tool}")
        if self.used >= MAX_STEPS:
            return {"is_error": True, "output": {"error": LIMIT_REACHED}}
        self.used += 1
        step_no = self.used

        try:
            result = {"is_error": False, "output": self.tools.run(tool, tool_input)}
        except ToolInputError as error:
            result = {"is_error": True, "output": {"error": str(error)}}

        store.save_step(self.attempt_id, step_no, tool, tool_input, result["output"])
        if not result["is_error"] and step_no == MAX_STEPS:
            result["output"]["note"] = "This was the last step. Write the report now."
        return result
