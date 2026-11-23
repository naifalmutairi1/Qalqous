import data from '../data/mock.json';
import { fmtDay, fmtMoney, fmtTime } from '../lib/format.js';

// Screen 2 (placeholder): one item. Note the back link: the arrow is directional,
// so it carries .icon-directional and flips in RTL. "Back" sits at the start side (the right).
export default function Detail({ id }) {
  const item = data.items.find((x) => x.id === id);

  if (!item) {
    return (
      <div className="card empty">
        <p className="error">ما لقينا هذا العنصر.</p>
        <a className="btn" href="#/">ارجع للرئيسية</a>
      </div>
    );
  }

  return (
    <section>
      <a href="#/" className="muted">
        <span className="icon-directional" aria-hidden="true" style={{ display: 'inline-block' }}>&larr;</span> رجوع
      </a>
      <h1>
        <bdi>{item.title}</bdi>
        {item.code && <> <span dir="ltr">{item.code}</span></>}
      </h1>
      <div className="card">
        <p>{item.subtitle}</p>
        <p className="muted">
          {fmtDay(item.date)}، {fmtTime(item.date)}
        </p>
        <p>{fmtMoney(item.price)}</p>
      </div>
    </section>
  );
}
