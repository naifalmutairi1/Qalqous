"""The investigation: reads one incident's log lines and writes the Arabic report.

rules.py writes it from fixed templates (no AI). The Claude investigator comes later
and saves through the same evidence check in evidence.py.
tools.py holds Claude's three read-only tools; steps.py caps them at 6 calls per attempt.
"""
