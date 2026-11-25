import './DemoBanner.css';

// The thin bar on top of every screen in the public demo (VITE_DEMO=1 builds only, see App.jsx).
// «إعادة العرض» goes back to Home and reloads the page: the demo keeps the visitor's decision
// in memory only, so a reload starts it again from the beginning.
export default function DemoBanner() {
  function restart(event) {
    event.preventDefault();
    window.location.hash = '#/';
    window.location.reload();
  }

  return (
    <p className="demo-banner" role="note">
      عرض تجريبي ببيانات وهمية. النسخة الحقيقية تعمل على جهاز الشركة.{' '}
      <a className="demo-banner__reset" href="#/" onClick={restart}>
        إعادة العرض
      </a>
    </p>
  );
}
