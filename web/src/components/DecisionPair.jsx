import './buttons.css';
import './DecisionPair.css';

// Decision buttons (DESIGN.md 5.1): ALWAYS an equal pair. Same component, same class, same size:
// neither choice may look heavier than the other.
// options: [{ choice, label, helper }], in reading order.
// disabled: after a decision both buttons stay visible but disabled, and the helper lines go away.
export default function DecisionPair({ options, disabled = false, onPick }) {
  return (
    <div className="decision-pair">
      {options.map((o) => (
        <div className="decision-pair__item" key={o.choice}>
          <button
            type="button"
            className="btn btn--neutral decision-pair__button"
            disabled={disabled}
            onClick={() => onPick(o.choice)}
          >
            {o.label}
          </button>
          {!disabled && <p className="decision-pair__helper">{o.helper}</p>}
        </div>
      ))}
    </div>
  );
}
