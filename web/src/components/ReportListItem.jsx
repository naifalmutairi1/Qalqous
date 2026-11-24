import './ReportListItem.css';

// Previous-report list item (DESIGN.md 5.10): a whole-row link to an old report.
// Line 1: username، outcome. Line 2: date and time. Trailing «←» (points "forward" in RTL).
// Use inside <ul className="report-list">.
export default function ReportListItem({ href, username, outcome, when }) {
  return (
    <li>
      <a className="report-item" href={href}>
        <span className="report-item__text">
          <span className="report-item__line">
            <bdi>{username}</bdi>، {outcome}
          </span>
          <span className="report-item__when">{when}</span>
        </span>
        <span className="report-item__arrow" aria-hidden="true">←</span>
      </a>
    </li>
  );
}
