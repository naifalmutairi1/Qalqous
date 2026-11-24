import { useId, useState } from 'react';
import { fmtCount, fmtLogStamp } from '../lib/format.js';
import './EvidenceLog.css';

// Collapsible evidence log (DESIGN.md 5.8). Collapsed by default; the whole bar is the button.
// lines: log lines { id, at, event, username, ip }. They are shown exactly as in the log file,
// left-to-right, as plain text (never as HTML).
export default function EvidenceLog({ lines }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  const count = fmtCount(lines.length, {
    one: 'سطر واحد', two: 'سطران', few: '{n} أسطر', many: '{n} سطراً', other: '{n} سطر',
  });
  // Pad the event name so the user and IP columns line up (LOGIN_FAIL is shorter than LOGIN_SUCCESS).
  const text = lines
    .map((l) => [l.id, fmtLogStamp(l.at), l.event.padEnd(13), l.username, l.ip].join('  '))
    .join('\n');

  return (
    <div className="evidence">
      <button
        type="button"
        className="evidence__bar"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen(!open)}
      >
        <span>سجلّ الأدلة ({count})</span>
        <span aria-hidden="true">{open ? '▴' : '▾'}</span>
      </button>
      {open && (
        <pre id={panelId} className="evidence__lines" dir="ltr">
          {text}
        </pre>
      )}
    </div>
  );
}
