import { useEffect, useRef } from 'react';
import './buttons.css';
import './ConfirmBox.css';

// "Are you sure?" step (DESIGN.md 5.2). It replaces the decision pair after a press.
// Here the two buttons are intentionally unequal: confirm is filled, «رجوع» is neutral.
export default function ConfirmBox({ children, confirmLabel, onConfirm, onBack }) {
  // Move keyboard/screen-reader focus to the box when it appears, so the user
  // lands on the question instead of being left on a button that no longer exists.
  const ref = useRef(null);
  useEffect(() => ref.current?.focus(), []);

  return (
    <div className="confirm-box" ref={ref} tabIndex={-1} role="group" aria-labelledby="confirm-box-title">
      <h3 id="confirm-box-title" className="confirm-box__title">هل أنت متأكد؟</h3>
      <p className="confirm-box__body">{children}</p>
      <div className="confirm-box__actions">
        <button type="button" className="btn btn--confirm confirm-box__confirm" onClick={onConfirm}>
          {confirmLabel}
        </button>
        <button type="button" className="btn btn--neutral btn--medium" onClick={onBack}>
          رجوع
        </button>
      </div>
    </div>
  );
}
