// data.js: the only place screens read mock.json. Day 3 replaces these functions with
// calls to the API (lib/api.js), so the screens do not need to change.
import mock from '../data/mock.json';

export const company = mock.company;
// Mock only: the monitor's last check is "3 minutes ago" relative to now, so the demo reads
// «آخر فحص قبل ٣ دقائق» on any day. The fixed date in mock.json would make monitoring look stopped.
// Day 3: the API returns the real lastCheckAt.
export const monitor = {
  ...mock.monitor,
  lastCheckAt: new Date(Date.now() - 3 * 60 * 1000).toISOString(),
};
export const incidents = mock.incidents;

export const getIncident = (id) => mock.incidents.find((i) => i.id === id) ?? null;
export const getAccount = (username) => mock.accounts.find((a) => a.username === username) ?? null;

// The incident's evidence lines, oldest first.
export function getEvidenceLogs(incident) {
  const ids = new Set(incident.evidenceLogIds);
  return mock.logs
    .filter((line) => ids.has(line.id))
    .sort((a, b) => new Date(a.at) - new Date(b.at));
}

// First word of a person's name, for short sentences: «ماجد» from «ماجد بن فهد ...», «Sarah» from «Sarah Kelly».
export const firstName = (account) => (account?.displayName ?? '').split(' ')[0];
