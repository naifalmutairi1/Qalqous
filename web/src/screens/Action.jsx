import { useState } from 'react';

// Screen 3 (placeholder): the main action (a booking, an order, a new entry...).
// Inputs that take what the user types get dir="auto": Arabic or English, both sit right.
// No backend today: "sending" only shows a message. Day 3 connects it for real.
export default function Action() {
  const [name, setName] = useState('');
  const [sent, setSent] = useState(false);

  if (sent) {
    return (
      <div className="card empty">
        <h2>وصل!</h2>
        <p>
          تم، يا <bdi>{name}</bdi>. (هذي بيانات تجريبية، ما انرسل شي فعلًا.)
        </p>
        <a className="btn" href="#/">ارجع للرئيسية</a>
      </div>
    );
  }

  return (
    <section>
      <h1>الفعل الرئيسي</h1>
      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) setSent(true);
        }}
      >
        <div className="field">
          <label htmlFor="name">اسمك</label>
          <input id="name" dir="auto" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <button className="btn" type="submit" disabled={!name.trim()}>
          أرسل
        </button>
      </form>
    </section>
  );
}
