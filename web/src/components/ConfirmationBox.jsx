import { useEffect, useRef } from 'react';
import './ConfirmationBox.css';

// Confirmation box (DESIGN.md 5.9): the ONLY place Pine green appears.
// Shown after a confirmed decision; it stays (no close button, no timer).
// role="status" makes screen readers announce it when it appears.
// focusOnShow: true right after the user confirms, so focus lands on the result.
export default function ConfirmationBox({ title, recordedAt, nextStep, focusOnShow = false }) {
  const ref = useRef(null);
  useEffect(() => {
    if (focusOnShow) ref.current?.focus();
  }, [focusOnShow]);

  return (
    <div className="confirmation" role="status" ref={ref} tabIndex={-1}>
      <div className="confirmation__head">
        <span className="confirmation__check" aria-hidden="true">✓</span>
        <h3 className="confirmation__title">{title}</h3>
      </div>
      <p>{recordedAt}</p>
      <p>{nextStep}</p>
    </div>
  );
}
