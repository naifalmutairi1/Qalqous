// api.js: the ONLY place the web app talks to the server. Screens call these functions,
// never fetch() directly. In dev, Vite forwards /api to the Python API on 127.0.0.1:8000
// (see vite.config.js), so there is no CORS setup.
//
// Each function returns the JSON body, or throws an ApiError with the HTTP status and the
// server's Arabic message (`detail`), so a screen can show the error banner.

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(method, path, body) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    // The server is not running, or the network failed.
    throw new ApiError(0, 'تعذّر الاتصال بقلقوص.');
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    // FastAPI puts our message in `detail` (a string). For a 422 it is a list of problems instead.
    const message = typeof data?.detail === 'string' ? data.detail : 'حدث خطأ غير متوقع.';
    throw new ApiError(response.status, message);
  }
  return data;
}

// Home: { company, monitor, openIncident | null, decided: [...] newest first }
export const getHome = () => request('GET', '/home');

// Report: one incident with logs, findings and decision. 404 unknown, 409 not ready yet.
export const getIncident = (id) => request('GET', `/incidents/${id}`);

// The Report screen's data, in the same shape it used with mock.json (lib/data.js):
//   { company, incident, account, logs }
// The API sends one object with `account` and `logs` inside it; this is the only place we split it.
// incident.findings is the server's checked list: [{ kind, confirmed, evidenceLogIds }].
export async function getReport(id) {
  const { company, account, logs, ...incident } = await getIncident(id);
  return { company, incident, account, logs };
}

// Decision: choice is 'keep_suspended' or 'restore'. Returns { choice, decidedAt }. 409 if already decided.
export const postDecision = (id, choice) => request('POST', `/incidents/${id}/decision`, { choice });
