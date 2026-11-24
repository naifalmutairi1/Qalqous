import './IncidentCard.css';

// Incident card (DESIGN.md 5.6): a white card on sand.
// Order: tag (optional, e.g. «تقرير أساسي») -> meta -> title -> summary -> action.
// The card itself is not a link; only the action button is.
export default function IncidentCard({ tag, meta, title, children, action }) {
  return (
    <article className="incident-card">
      {tag && <p className="incident-card__tag">{tag}</p>}
      {meta && <p className="incident-card__meta">{meta}</p>}
      <h2 className="incident-card__title">{title}</h2>
      {children && <div className="incident-card__summary">{children}</div>}
      {action && <div className="incident-card__action">{action}</div>}
    </article>
  );
}
