// findings.js: which log lines back each fact on the Report (HANDOFF.md rule 5a).
// The five facts on screen ARE the findings. A fact with no backing line is "unconfirmed"
// and the screen shows «(غير مؤكد)» next to it. Nothing here is trusted without a log line.
//
// incident: the incident. logs: its evidence lines ({ id, at, event, username, ip }).
// Returns, for each fact, the IDs of the log lines that back it (empty array = unconfirmed).

const sameMoment = (a, b) => new Date(a).getTime() === new Date(b).getTime();
const ids = (lines) => lines.map((l) => l.id);

// The server's name for each fact (server/investigation/evidence.py).
const SERVER_KIND = {
  attempts: 'failed_attempts',
  successTime: 'success_time',
  sourceIp: 'source_ip',
  duration: 'duration',
  seenBefore: 'seen_before',
};

// True if the server checked this fact and found a real log line for it.
// A fact the server has no finding for counts as unconfirmed.
export function serverConfirmed(incident, fact) {
  return (incident.findings ?? []).some((f) => f.kind === SERVER_KIND[fact] && f.confirmed);
}

export function evidenceForFacts(incident, logs) {
  const fails = logs.filter((l) => l.event === 'LOGIN_FAIL');
  const successes = logs.filter((l) => l.event === 'LOGIN_SUCCESS');
  const fromIp = logs.filter((l) => l.ip === incident.sourceIp);

  return {
    attempts: ids(fails),
    successTime: ids(successes.filter((l) => sameMoment(l.at, incident.successAt))),
    sourceIp: ids(fromIp),
    // Both ends of the burst must exist in the log.
    duration: (() => {
      const first = fails.find((l) => sameMoment(l.at, incident.firstFailAt));
      const last = fails.find((l) => sameMoment(l.at, incident.lastFailAt));
      return first && last ? ids([first, last]) : [];
    })(),
    seenBefore: ids(successes.filter((l) => l.ip === incident.sourceIp)),
  };
}
