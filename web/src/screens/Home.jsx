import data from '../data/mock.json';
import { fmtDay, fmtMoney, fmtNumber } from '../lib/format.js';

// Screen 1 (placeholder). Patterns worth keeping when the agent rebuilds it:
// - all data comes from mock.json, nothing typed into the JSX
// - <bdi> around names that may be English, so punctuation does not jump sides
// - codes with dashes in <span dir="ltr">, or RTL shows 4471-22-0098 as 0098-22-4471
// - numbers and dates go through lib/format.js
// - an empty state exists from day one
export default function Home() {
  const items = data.items;

  return (
    <section>
      <p className="muted">
        هلا <bdi>{data.user.name}</bdi>
      </p>
      <h1>الشاشة الرئيسية</h1>

      {items.length === 0 ? (
        <div className="card empty">
          <p>ما فيه شي هنا للحين.</p>
          <a className="btn" href="#/action">ابدأ أول واحد</a>
        </div>
      ) : (
        <ul className="list grid-md">
          {items.map((item) => (
            <li key={item.id}>
              <a className="card card-link" href={'#/detail/' + item.id}>
                <h2>
                  <bdi>{item.title}</bdi>
                  {item.code && <> <span dir="ltr">{item.code}</span></>}
                </h2>
                <p className="muted">{item.subtitle}</p>
                <div className="row">
                  <span>{fmtMoney(item.price)}</span>
                  <span className="muted">
                    {fmtNumber(item.count)}، {fmtDay(item.date)}
                  </span>
                </div>
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
