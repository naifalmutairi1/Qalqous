"""The exact report the AI must return, and our own check of it.

The AI is asked for this JSON shape (OUTPUT_SCHEMA goes to the SDK), and then our code checks
it AGAIN with a Pydantic model, because we never trust model output blindly:

    {"headline_ar": "...", "summary_ar": "...",
     "findings": [{"kind": "failed_attempts", "log_ids": [1479, 1480]}, ...]}

If the check fails, the investigation counts as failed ('invalid_output') and the
rule-based writer runs instead. The log ids are checked later, by evidence.py.
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError

from server.investigation.evidence import FINDING_KINDS

MAX_LOG_IDS = 50

# Handed to the SDK as output_format. Kept by hand (not generated) so it is easy to read.
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "headline_ar": {"type": "string", "description": "One Arabic sentence, 10-120 characters."},
        "summary_ar": {"type": "string", "description": "Two or three short Arabic sentences, 20-400 characters."},
        "findings": {
            "type": "array",
            "maxItems": len(FINDING_KINDS),
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": list(FINDING_KINDS)},
                    "log_ids": {"type": "array", "items": {"type": "integer"}, "maxItems": MAX_LOG_IDS},
                },
                "required": ["kind", "log_ids"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["headline_ar", "summary_ar", "findings"],
    "additionalProperties": False,
}


class InvalidReport(Exception):
    """The AI's output failed our check. The message is a short English reason, for you only."""


class FindingOut(BaseModel):
    model_config = ConfigDict(extra="forbid")  # an unexpected field is an error, not ignored
    kind: Literal[FINDING_KINDS]
    log_ids: list[StrictInt] = Field(max_length=MAX_LOG_IDS)  # StrictInt: "12" or 12.0 is refused


class ReportOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    headline_ar: str = Field(min_length=10, max_length=120)
    summary_ar: str = Field(min_length=20, max_length=400)
    findings: list[FindingOut] = Field(max_length=len(FINDING_KINDS))


ARABIC_LETTER = re.compile(r"[ء-ي]")
LATIN_LETTER = re.compile(r"[A-Za-z]")
IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
IPV6 = re.compile(r"\b[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,7}\b")


def is_arabic(text, allowed_words):
    """True if the text is Arabic. Allowed English: the username and IP addresses.

    We remove those (and anything that looks like an IP), then any Latin letter left
    means the AI wrote English, and the report is refused.
    """
    for word in sorted(allowed_words, key=len, reverse=True):  # longest first, so parts don't break it
        text = text.replace(word, " ")
    text = IPV6.sub(" ", IPV4.sub(" ", text))
    return bool(ARABIC_LETTER.search(text)) and not LATIN_LETTER.search(text)


def validate_report(raw, data):
    """Check the AI's output. Returns a plain dict with all five kinds, or raises InvalidReport.

    raw: the dict the AI returned. data: store.investigation_input(...) for the incident.
    A kind the AI left out is added with no log lines, so the Report shows it «غير مؤكد».
    """
    if not isinstance(raw, dict):
        raise InvalidReport("output is not a JSON object")
    try:
        report = ReportOut.model_validate(raw)
    except ValidationError as error:
        first = error.errors()[0]
        raise InvalidReport(f"{'.'.join(map(str, first['loc']))}: {first['msg']}") from None

    allowed_words = {data["account"]} | {line["source_ip"] for line in data["lines"]}
    for name in ("headline_ar", "summary_ar"):
        if not is_arabic(getattr(report, name), allowed_words):
            raise InvalidReport(f"{name} is not Arabic")

    given = {}
    for finding in report.findings:
        given.setdefault(finding.kind, finding.log_ids)  # a repeated kind: the first one wins
    return {
        "headline_ar": report.headline_ar.strip(),
        "summary_ar": report.summary_ar.strip(),
        "findings": [{"kind": kind, "log_ids": given.get(kind, [])} for kind in FINDING_KINDS],
    }
