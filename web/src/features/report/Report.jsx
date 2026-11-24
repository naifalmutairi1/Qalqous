import { useEffect, useState } from 'react';
import NumberTile, { TileRow } from '../../components/NumberTile.jsx';
import FactRow, { FactList } from '../../components/FactRow.jsx';
import EvidenceLog from '../../components/EvidenceLog.jsx';
import StatusBanner from '../../components/StatusBanner.jsx';
import PrimaryButton from '../../components/PrimaryButton.jsx';
import { ApiError, getReport, postDecision } from '../../lib/api.js';
import { fmtDuration, fmtNumber, fmtTime, fmtTimeSec, fmtWeekdayDate, pluralForm } from '../../lib/format.js';
import Decision from './Decision.jsx';
import { evidenceForFacts, serverConfirmed } from './findings.js';
import './report.css';

// Screen 2: the incident report (HANDOFF.md 1g, design/mockups/report-*.png).
// Data comes from the API (lib/api.js). Five states:
//   loading   -> waiting for the API
//   notFound  -> no incident with this id (404), or an id that is not a number (422)
//   notReady  -> the incident exists but its report is still being written (409)
//   error     -> the API is not running or failed; «أعد المحاولة» asks again
//   ready     -> the report
export default function Report({ id, params }) {
  const [state, setState] = useState('loading');
  const [data, setData] = useState(null); // { company, incident, account, logs }
  const [attempt, setAttempt] = useState(0); // +1 = load again («أعد المحاولة», or after a 409 on deciding)

  useEffect(() => {
    // `ignore` stops an old answer from replacing a newer one (if the id changes while loading).
    let ignore = false;
    setState('loading');
    getReport(id)
      .then((report) => {
        if (ignore) return;
        setData(report);
        setState('ready');
      })
      .catch((error) => {
        if (ignore) return;
        setState(stateForError(error));
      });
    return () => {
      ignore = true;
    };
  }, [id, attempt]);

  // Save the decision on the server. If it fails, Decision shows its own error and stays on «هل أنت متأكد؟».
  async function decide(choice) {
    try {
      const saved = await postDecision(data.incident.id, choice);
      setData((d) => ({ ...d, incident: { ...d.incident, status: 'decided', decision: saved } }));
    } catch (error) {
      // 409: someone already decided (another tab). Load the report again to show that decision.
      if (error instanceof ApiError && error.status === 409) {
        setAttempt((n) => n + 1);
        return;
      }
      throw error;
    }
  }

  return (
    <div className="report">
      <header className="report-header">
        <a className="report-header__back" href="#/">
          <span aria-hidden="true">→</span> الرئيسية
        </a>
        <div className="report-header__brand">
          <span className="report-header__logo">قلقوص</span>
          {data && <bdi className="report-header__company">{data.company.name}</bdi>}
        </div>
      </header>

      {state === 'loading' && <StatusBanner status="loading">نحضّر التقرير…</StatusBanner>}

      {state === 'error' && (
        <StatusBanner
          status="error"
          action={
            <PrimaryButton small onClick={() => setAttempt((n) => n + 1)}>
              أعد المحاولة
            </PrimaryButton>
          }
        >
          تعذّر فتح التقرير الآن. تأكد أن قلقوص يعمل على هذا الجهاز، ثم أعد المحاولة.
        </StatusBanner>
      )}

      {state === 'notFound' && (
        <article className="sheet">
          <p>لم نجد هذا التقرير.</p>
        </article>
      )}

      {state === 'notReady' && (
        <article className="sheet">
          <p>التقرير لم يجهز بعد. نراجع ما حدث على الحساب، ويستغرق هذا عادةً أقل من دقيقتين.</p>
        </article>
      )}

      {state === 'ready' && (
        <ReportSheet
          incident={data.incident}
          account={data.account}
          logs={data.logs}
          onDecide={decide}
          dropLogIds={devDropLogIds(params)}
        />
      )}
    </div>
  );
}

// Which screen state an API error leads to. Anything unexpected is the friendly error banner:
// we never show the raw error to the admin.
function stateForError(error) {
  if (!(error instanceof ApiError)) return 'error';
  if (error.status === 404 || error.status === 422) return 'notFound';
  if (error.status === 409) return 'notReady';
  return 'error'; // 0 = no connection; 500/502 = the API is down behind the Vite proxy, or crashed
}

// First word of a person's name, for short sentences: «ماجد» from «ماجد بن فهد ...», «Sarah» from «Sarah Young».
const firstName = (account) => (account?.displayName ?? '').split(' ')[0];

// Dev-only switch to see «(غير مؤكد)»: #/report/1?drop=evt-40131,evt-40130 hides those log lines.
// import.meta.env.DEV is true only under `npm run dev`, so a real build ignores it.
function devDropLogIds(params) {
  if (!import.meta.env.DEV) return [];
  return (params.get('drop') ?? '').split(',').filter(Boolean);
}

function ReportSheet({ incident, account, logs: allLogs, onDecide, dropLogIds }) {
  const logs = allLogs.filter((l) => !dropLogIds.includes(l.id));
  const decision = incident.decision;
  // The facts below are the findings: each needs a log line, or it is marked «(غير مؤكد)».
  // Checked twice: the server's evidence check, and the log lines on this screen.
  const evidence = evidenceForFacts(incident, logs);
  const unconfirmed = (fact) => !serverConfirmed(incident, fact) || evidence[fact].length === 0;
  const readyAt = incident.reportReadyAt ?? incident.openedAt;
  // "محاولات" for 3-10, "محاولة" for 11 and up (Arabic counted-noun rule).
  const attemptsWord = pluralForm(incident.failedAttempts) === 'few' ? 'محاولات' : 'محاولة';

  return (
    <article className="sheet">
      <div className="report__intro">
        <p className="report__meta">
          تقرير حادث، {fmtWeekdayDate(readyAt)}، {fmtTime(readyAt)}
        </p>
        {incident.reportSource === 'rules' && <p className="report__basic">تقرير أساسي</p>}
        <h1 className="report__headline">{incident.headline}</h1>
        {!decision && (
          <p className="report__subline">لم يُستخدم الحساب منذ إيقافه. نحتاج قرارك: هل تبقيه موقوفاً أم تعيده؟</p>
        )}
      </div>

      <section className="report__section" aria-labelledby="what-happened">
        <h2 id="what-happened" className="report__title">ماذا حدث</h2>
        <TileRow>
          <NumberTile
            value={fmtNumber(incident.failedAttempts)}
            caption={`${attemptsWord} بكلمة مرور خاطئة`}
            unconfirmed={unconfirmed('attempts')}
          />
          <NumberTile
            value={fmtTime(incident.successAt)}
            caption="نجح الدخول بعدها، مرة واحدة"
            unconfirmed={unconfirmed('successTime')}
          />
          <NumberTile value={incident.sourceIp} caption="مصدر الدخول" tech unconfirmed={unconfirmed('sourceIp')} />
        </TileRow>
        <FactList>
          <FactRow label="المدة" unconfirmed={unconfirmed('duration')}>
            من {fmtTimeSec(incident.firstFailAt)} إلى {fmtTimeSec(incident.lastFailAt)} (
            {fmtDuration(incident.firstFailAt, incident.lastFailAt)})، ثم دخول ناجح {fmtTimeSec(incident.successAt)}
          </FactRow>
          <FactRow label="هل رأيناه من قبل؟" unconfirmed={unconfirmed('seenBefore')}>
            {incident.ipSeenBefore
              ? 'نعم، دخل هذا الحساب من هذا العنوان من قبل'
              : 'لا، أول مرة يظهر هذا العنوان في شركتك'}
          </FactRow>
        </FactList>
      </section>

      <section className="report__section" aria-labelledby="can-do">
        <h2 id="can-do" className="report__title">ماذا يستطيع هذا الحساب أن يفعل</h2>
        <p>{incident.access}.</p>
      </section>

      <section className="report__section report__decision" aria-labelledby="your-decision">
        <h2 id="your-decision" className="report__title">قرارك</h2>
        <Decision
          username={incident.username}
          name={firstName(account)}
          decision={decision}
          onDecide={onDecide}
        />
      </section>

      <EvidenceLog lines={logs} />
    </article>
  );
}
