import { useEffect, useState } from 'react';
import Home from './features/home/Home.jsx';
import Report from './features/report/Report.jsx';

// Two screens, chosen by the part of the URL after "#" (a "hash router": no library needed):
//   #/                    -> Home
//   #/report/1            -> Report for incident 1 (Home's mock links use inc-0014)
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

  // Home is still on mock data and merges in decisions made in this session. The Report now saves
  // its decision on the server, so there are none to pass. This goes when Home is connected.
  const decisions = {};

  const screen =
    section === 'report' ? (
      <Report id={id} params={params} />
    ) : (
      <Home params={params} decisions={decisions} />
    );

  return <main className="page">{screen}</main>;
}
