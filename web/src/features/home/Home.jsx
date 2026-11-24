import { useState } from 'react';
import StatusBanner from '../../components/StatusBanner.jsx';
import IncidentCard from '../../components/IncidentCard.jsx';
import PrimaryButton from '../../components/PrimaryButton.jsx';
import ReportListItem from '../../components/ReportListItem.jsx';
import { company, incidents, monitor } from '../../lib/data.js';
import { fmtAgo, fmtCount, fmtDate, fmtDayLabel, fmtTime } from '../../lib/format.js';
import './home.css';

// Screen 1: Home (HANDOFF.md 1c/1d/1e/1f, design/mockups/home.png for the layout).
// decisions: decisions made in this session (from App). params: dev-only state switch.

const FIRST_LIST_SIZE = 2; // previous reports shown before «عرض الكل» (HANDOFF.md rule 12)

// Arabic count forms (see fmtCount in lib/format.js).
const OPEN_FORMS = {
  one: 'حادث مفتوح واحد', two: 'حادثان مفتوحان', few: '{n} حوادث مفتوحة', many: '{n} حادثاً مفتوحاً', other: '{n} حادث مفتوح',
};
const OTHER_ACCOUNT_FORMS = {
  zero: 'لا حسابات أخرى', one: 'حساب واحد آخر', two: 'حسابان آخران', few: '{n} حسابات أخرى', many: '{n} حساباً آخر', other: '{n} حساب آخر',
};
const ACCOUNT_FORMS = {
  zero: 'لا حسابات', one: 'حساب واحد', two: 'حسابان', few: '{n} حسابات', many: '{n} حساباً', other: '{n} حساب',
};
const FAILED_FORMS = {
  one: 'محاولة فاشلة واحدة', two: 'محاولتان فاشلتان', few: '{n} محاولات فاشلة', many: '{n} محاولة فاشلة', other: '{n} محاولة فاشلة',
};

// Dev-only: #/?state=empty|loading|error shows the other designed states (ignored in a real build).
function devState(params) {
  if (!import.meta.env.DEV) return null;
  const s = params.get('state');
  return ['empty', 'loading', 'error'].includes(s) ? s : null;
}

export default function Home({ params, decisions }) {
  const [retrying, setRetrying] = useState(false); // «أعد المحاولة» pressed: show the loading state
  const [showAll, setShowAll] = useState(false);

  // Merge the decisions made in this session into the mock incidents.
  const all = incidents.map((i) => ({ ...i, decision: decisions[i.id] ?? i.decision }));
  const decided = all
    .filter((i) => i.decision)
    .sort((a, b) => new Date(b.decision.decidedAt) - new Date(a.decision.decidedAt));
  let open = all.filter((i) => !i.decision);

  const forced = devState(params);
  if (forced === 'empty') open = [];
  const incident = open[0] ?? (forced ? incidents[0] : null); // only one card is designed (rule 11)
  const state = retrying ? 'loading' : forced ?? (incident ? 'open' : 'empty');

  return (
    <div className="home">
      <div className="home-top">
        <header className="home-header">
          <span className="home-header__logo">قلقوص</span>
          <span className="home-header__admin">{company.admin.displayName}</span>
        </header>
        <Strip state={state} openCount={open.length} onRetry={() => setRetrying(true)} />
      </div>

      <div className={decided.length > 0 ? 'home-columns' : 'home-columns home-columns--single'}>
        <div className="home-main">
          <MainCard state={state} incident={incident} />
        </div>

        {decided.length > 0 && (
          <aside className="home-side" aria-label="القرارات السابقة">
            <section className="home-side__section">
              <h2 className="home-side__label">آخر قرار</h2>
              <p>
                <LastDecision incident={decided[0]} />
              </p>
            </section>

            <section className="home-side__section">
              <h2 className="home-side__label">التقارير السابقة</h2>
              <ul className="report-list">
                {(showAll ? decided : decided.slice(0, FIRST_LIST_SIZE)).map((i) => (
                  <ReportListItem
                    key={i.id}
                    href={`#/report/${i.id}`}
                    username={i.username}
                    outcome={i.decision.choice === 'restore' ? 'أُرجع الحساب' : 'بقي موقوفاً'}
                    when={`${fmtDate(i.decision.decidedAt)}، ${fmtTime(i.decision.decidedAt)}`}
                  />
                ))}
              </ul>
              {!showAll && decided.length > FIRST_LIST_SIZE && (
                <button type="button" className="home-more" onClick={() => setShowAll(true)}>
                  عرض الكل ({fmtCount(decided.length, { other: '{n}' })}) <span aria-hidden="true">←</span>
                </button>
              )}
            </section>
          </aside>
        )}
      </div>
    </div>
  );
}

// The status strip at the top: one sentence about the whole company right now.
function Strip({ state, openCount, onRetry }) {
  if (state === 'loading') {
    return <StatusBanner status="loading">قلقوص يراجع نشاطاً غير معتاد الآن</StatusBanner>;
  }
  if (state === 'error') {
    return (
      <StatusBanner
        status="error"
        action={
          <PrimaryButton small onClick={onRetry}>
            أعد المحاولة
          </PrimaryButton>
        }
      >
        تعذّر إكمال التحقيق التفصيلي. نعرض لك التقرير الأساسي المبني على القواعد، وهو كافٍ لاتخاذ القرار.
      </StatusBanner>
    );
  }
  if (state === 'open') {
    const others = monitor.accountsMonitored - openCount;
    return (
      <StatusBanner>
        {fmtCount(openCount, OPEN_FORMS)}، {fmtCount(others, OTHER_ACCOUNT_FORMS)} بلا ملاحظات
      </StatusBanner>
    );
  }
  return (
    <StatusBanner>
      {fmtCount(monitor.accountsMonitored, ACCOUNT_FORMS)}، آخر فحص {fmtAgo(monitor.lastCheckAt)}
    </StatusBanner>
  );
}

// The main column: the open incident, the investigation in progress, or the calm empty state.
function MainCard({ state, incident }) {
  if (state === 'empty' || !incident) {
    return <IncidentCard title="قلقوص يراقب. لا توجد حوادث مفتوحة." />;
  }

  const user = <bdi>{incident.username}</bdi>;
  const failed = fmtCount(incident.failedAttempts, FAILED_FORMS);
  const address = incident.ipSeenBefore ? 'عنوان معروف' : 'عنوان جديد';

  if (state === 'loading') {
    return (
      <IncidentCard title={<>نراجع ما حدث على حساب {user}</>}>
        <p>يستغرق هذا عادةً أقل من دقيقتين. أوقفنا الحساب مؤقتاً احتياطاً.</p>
        <ul className="home-steps">
          <li><span className="home-steps__mark" aria-hidden="true">✓</span>جمعنا سجلات الدخول</li>
          <li><span className="home-steps__mark" aria-hidden="true">✓</span>قارنّا العنوان بالعناوين المعروفة</li>
          <li>
            <span className="home-steps__mark" aria-hidden="true"><span className="home-steps__dot pulse-dot" /></span>
            نحدّد ما يستطيع الحساب الوصول إليه…
          </li>
        </ul>
      </IncidentCard>
    );
  }

  const title = <>أوقفنا حساب {user} مؤقتاً</>;
  const href = `#/report/${incident.id}`;

  if (state === 'error') {
    return (
      <IncidentCard
        tag="تقرير أساسي"
        title={title}
        action={<PrimaryButton href={href}>افتح التقرير الأساسي</PrimaryButton>}
      >
        {failed} ثم دخول ناجح الساعة {fmtTime(incident.successAt)} من {address}، ينتظر قرارك
      </IncidentCard>
    );
  }

  // The account's role: the part of its access line before the colon («موظف عادي»).
  const role = incident.access.split(':')[0];
  return (
    <IncidentCard
      meta={`${fmtDayLabel(incident.openedAt)}، ${fmtTime(incident.openedAt)}، ينتظر قرارك`}
      title={title}
      action={<PrimaryButton href={href}>افتح التقرير</PrimaryButton>}
    >
      {failed}، {address}، {role}
    </IncidentCard>
  );
}

function LastDecision({ incident }) {
  const user = <bdi>{incident.username}</bdi>;
  const when = fmtDate(incident.decision.decidedAt);
  return incident.decision.choice === 'restore' ? (
    <>أرجعتَ حساب {user}، {when}</>
  ) : (
    <>أبقيتَ حساب {user} موقوفاً، {when}</>
  );
}
