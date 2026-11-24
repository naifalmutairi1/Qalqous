import './NumberTile.css';

// Number tile (DESIGN.md 5.4): a big value with a caption under it. Not interactive.
// tech: the value is a technical value (an IP), shown in the monospace font, left-to-right.
// unconfirmed: no log line backs this value; «(غير مؤكد)» is shown next to it.
export default function NumberTile({ value, caption, tech = false, unconfirmed = false }) {
  return (
    <div className="tile">
      <span className="tile__line">
        {tech ? (
          <span className="tile__value tile__value--tech tech" dir="ltr">
            {value}
          </span>
        ) : (
          <span className="tile__value">{value}</span>
        )}
        {unconfirmed && <span className="unconfirmed">(غير مؤكد)</span>}
      </span>
      <span className="tile__caption">{caption}</span>
    </div>
  );
}

// Row of tiles: up to 3 side by side, stacked on a phone.
export function TileRow({ children }) {
  return <div className="tile-row">{children}</div>;
}
