import './StatusBanner.css';

// Status banner (DESIGN.md 5.7). The dot says the state; the words say what it means. No red, no icons.
//   status="ok":      solid clay dot, still (calm: open incident or nothing to report)
//   status="loading": solid clay dot that pulses slowly
//   status="error":   hollow clay dot; pass the «أعد المحاولة» button as `action`
// role="status" lets screen readers announce a change of state.
export default function StatusBanner({ status = 'ok', action, children }) {
  return (
    <div className={`banner banner--${status}`} role="status">
      <span className="banner__dot" aria-hidden="true" />
      <p className="banner__text">{children}</p>
      {action}
    </div>
  );
}
