// demo.js: the API's stand-in for the public demo (built with VITE_DEMO=1). No network at all.
// It answers with the same shapes as the real API (see api.js), from data/demo.json, and keeps
// the visitor's decision in memory only: a reload (or «إعادة العرض») starts the demo again.
import demoData from '../data/demo.json';

// The visitor's copy, made on first use so the decision changes this copy and never the imported file.
// Made lazily on purpose: with no code running at import time, a normal build drops this whole file.
let copy = null;
const incidents = () => (copy ??= structuredClone(demoData.incidents));

// The same Arabic messages and status codes as the server (server/main.py).
const NOT_FOUND = { status: 404, message: 'لا يوجد حادث بهذا الرقم.' };

function find(id) {
  const incident = incidents().find((i) => String(i.id) === String(id));
  if (!incident) throw NOT_FOUND;
  return incident;
}

// Now, in Riyadh time, as the server writes it: 2026-11-25T21:40:10+03:00 (Riyadh has no daylight saving).
function nowRiyadh() {
  const shifted = new Date(Date.now() + 3 * 60 * 60 * 1000);
  return `${shifted.toISOString().slice(0, 19)}+03:00`;
}

// The short version of an incident, for the Home card (server/store.py _incident_card).
function card(i) {
  const { id, username, status, reportSource, openedAt, successAt, failedAttempts, ipSeenBefore, access } = i;
  return { id, username, status, reportSource, openedAt, successAt, failedAttempts, ipSeenBefore, access };
}

export function home() {
  const open = incidents().find((i) => i.status !== 'decided');
  const decided = incidents()
    .filter((i) => i.decision)
    .sort((a, b) => b.decision.decidedAt.localeCompare(a.decision.decidedAt)); // newest decision first
  return {
    company: demoData.company,
    monitor: { ...demoData.monitor, status: 'ok' },
    openIncident: open ? card(open) : null,
    decided: decided.map((i) => ({ id: i.id, username: i.username, openedAt: i.openedAt, decision: i.decision })),
  };
}

export function incident(id) {
  return structuredClone({ company: demoData.company, ...find(id) });
}

export function decide(id, choice) {
  const i = find(id);
  if (i.status !== 'awaiting_decision') {
    throw { status: 409, message: 'لا يمكن تسجيل القرار: سُجّل قرار من قبل، أو أن التقرير لم يجهز بعد.' };
  }
  i.decision = { choice, decidedAt: nowRiyadh() };
  i.status = 'decided';
  i.account.status = choice === 'restore' ? 'active' : 'suspended';
  return { ...i.decision };
}

export function retry(id) {
  find(id);
  throw { status: 409, message: 'التقرير التفصيلي جاهز.' }; // never reached: the demo has no failed investigation
}
