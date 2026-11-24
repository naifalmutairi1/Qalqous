import './FactRow.css';

// Fact rows (DESIGN.md 5.5): label on the start side, value next to it, a thin line between rows.
// Uses a description list (<dl>): the right HTML for label/value pairs, read correctly by screen readers.
export function FactList({ children }) {
  return <dl className="facts">{children}</dl>;
}

// unconfirmed: no log line backs this value; «(غير مؤكد)» is shown after it.
export default function FactRow({ label, children, unconfirmed = false }) {
  return (
    <div className="fact">
      <dt className="fact__label">{label}</dt>
      <dd className="fact__value">
        {children}
        {unconfirmed && <> <span className="unconfirmed">(غير مؤكد)</span></>}
      </dd>
    </div>
  );
}
