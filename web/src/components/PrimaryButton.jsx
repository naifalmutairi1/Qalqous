import './buttons.css';

// Primary button (DESIGN.md 5.3): navigation only («افتح التقرير»), never the decision.
// With href it is a link (it goes somewhere); without, a button (it does something here).
// small: the neutral 48px variant («أعد المحاولة»).
export default function PrimaryButton({ href, onClick, small = false, children }) {
  const className = small ? 'btn btn--neutral btn--small' : 'btn btn--primary';
  if (href) {
    return (
      <a className={className} href={href}>
        {children}
      </a>
    );
  }
  return (
    <button type="button" className={className} onClick={onClick}>
      {children}
    </button>
  );
}
