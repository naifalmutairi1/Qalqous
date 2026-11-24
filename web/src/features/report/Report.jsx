import NumberTile, { TileRow } from '../../components/NumberTile.jsx';
import FactRow, { FactList } from '../../components/FactRow.jsx';
import EvidenceLog from '../../components/EvidenceLog.jsx';
import { company, firstName, getAccount, getEvidenceLogs, getIncident } from '../../lib/data.js';
import { fmtDuration, fmtNumber, fmtTime, fmtTimeSec, fmtWeekdayDate, pluralForm } from '../../lib/format.js';
import Decision from './Decision.jsx';
import { evidenceForFacts } from './findings.js';
import './report.css';

// Screen 2: the incident report (HANDOFF.md 1g, design/mockups/report-*.png).
// decisions: decisions made in this session (from App), so they survive going back to Home.
export default function Report({ id, params, decisions, onDecide }) {
  const incident = getIncident(id);

  return (
    <div className="report">
      <header className="report-header">
        <a className="report-header__back" href="#/">
          <span aria-hidden="true">→</span> الرئيسية
        </a>
        <div className="report-header__brand">
          <span className="report-header__logo">قلقوص</span>
          <bdi className="report-header__company">{company.name}</bdi>
        </div>
      </header>

      {incident ? (
        <ReportSheet
          incident={incident}
          decision={decisions[incident.id] ?? incident.decision}
          onDecide={onDecide}
          dropLogIds={devDropLogIds(params)}
        />
      ) : (
        <article className="sheet">
          <p>لم نجد هذا التقرير.</p>
        </article>
      )}
    </div>
  );
}

// Dev-only switch to see «(غير مؤكد)»: #/report/inc-0014?drop=evt-40131,evt-40130 hides those log lines.
// import.meta.env.DEV is true only under `npm run dev`, so a real build ignores it.
function devDropLogIds(params) {
  if (!import.meta.env.DEV) return [];
  return (params.get('drop') ?? '').split(',').filter(Boolean);
}

function ReportSheet({ incident, decision, onDecide, dropLogIds }) {
  const account = getAccount(incident.username);
  const logs = getEvidenceLogs(incident).filter((l) => !dropLogIds.includes(l.id));
  // The facts below are the findings: each needs a log line, or it is marked «(غير مؤكد)».
  const evidence = evidenceForFacts(incident, logs);
  const unconfirmed = (fact) => evidence[fact].length === 0;
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
          onDecide={(choice) => onDecide(incident.id, choice)}
        />
      </section>

      <EvidenceLog lines={logs} />
    </article>
  );
}
