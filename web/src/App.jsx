import { useEffect, useState } from 'react';
import Home from './features/home/Home.jsx';
import Report from './features/report/Report.jsx';

// Two screens, chosen by the part of the URL after "#" (a "hash router": no library needed):
//   #/                    -> Home
//   #/report/1            -> Report for incident 1
// Anything after "?" is a dev-only state switch, so we can screenshot every design state,
// e.g. #/?state=loading or #/report/1?drop=evt-1489.
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

  const screen =
    section === 'report' ? (
      <Report id={id} params={params} />
    ) : (
      <Home params={params} />
    );

  return <main className="page">{screen}</main>;
}
