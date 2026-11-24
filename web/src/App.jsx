import { useEffect, useState } from 'react';
import Home from './features/home/Home.jsx';
import Report from './features/report/Report.jsx';

// Two screens, chosen by the part of the URL after "#" (a "hash router": no library needed):
//   #/                    -> Home
//   #/report/inc-0014     -> Report for one incident
// Anything after "?" is a dev-only state switch, so we can screenshot every design state
// without a backend, e.g. #/?state=loading or #/report/inc-0014?source=rules.
function readHash() {
  const raw = window.location.hash.replace(/^#/, '') || '/';
  const [path, query = ''] = raw.split('?');
  return { path, params: new URLSearchParams(query) };
}

function useHashRoute() {
  const [route, setRoute] = useState(readHash);
  useEffect(() => {
    const onChange = () => {
      setRoute(readHash());
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return route;
}

export default function App() {
  const { path, params } = useHashRoute();
  const [, section, id] = path.split('/');

  // Decisions made in this session, by incident id: { choice, decidedAt }.
  // Kept here (not inside Report) so Home can show a decision made on the Report.
  // Mock only: they are lost on reload until the backend saves them (Day 3).
  const [decisions, setDecisions] = useState({});
  const decide = (incidentId, choice) =>
    setDecisions((d) => ({ ...d, [incidentId]: { choice, decidedAt: new Date().toISOString() } }));

  const screen =
    section === 'report' ? (
      <Report id={id} params={params} decisions={decisions} onDecide={decide} />
    ) : (
      <Home params={params} decisions={decisions} />
    );

  return <main className="page">{screen}</main>;
}
