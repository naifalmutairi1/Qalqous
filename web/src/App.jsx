import { useEffect, useState } from 'react';
import Home from './screens/Home.jsx';
import Detail from './screens/Detail.jsx';
import Action from './screens/Action.jsx';

// Three placeholder screens = your 3 key screens. Rename them to match design/wireframes.md.
// Routing is a tiny hash switch (#/, #/detail/1, #/action): no library needed for 3 screens.
const SCREENS = [
  { path: '/', label: 'الرئيسية' },
  { path: '/detail/1', label: 'التفاصيل' },
  { path: '/action', label: 'الفعل الرئيسي' },
];

function useHashPath() {
  const read = () => window.location.hash.replace(/^#/, '') || '/';
  const [path, setPath] = useState(read);
  useEffect(() => {
    const onChange = () => setPath(read());
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return path;
}

export default function App() {
  const path = useHashPath();
  const [, section, id] = path.split('/');

  let screen = <Home />;
  if (section === 'detail') screen = <Detail id={id} />;
  if (section === 'action') screen = <Action />;

  return (
    <>
      <div className="starter-banner">
        هذا هيكل رمادي عن قصد. الشكل يجي من DESIGN.md حقك. (يختفي الشريط لما تعبّي tokens.css)
      </div>
      <div className="shell">
        <nav className="nav" aria-label="الشاشات">
          {SCREENS.map((s) => {
            const current = s.path === '/' ? path === '/' : path.startsWith('/' + s.path.split('/')[1]);
            return (
              <a key={s.path} href={'#' + s.path} aria-current={current ? 'page' : undefined}>
                {s.label}
              </a>
            );
          })}
        </nav>
        <main>{screen}</main>
      </div>
    </>
  );
}
