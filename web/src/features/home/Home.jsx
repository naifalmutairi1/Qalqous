import { useEffect, useState } from 'react';
import StatusBanner from '../../components/StatusBanner.jsx';
import IncidentCard from '../../components/IncidentCard.jsx';
import PrimaryButton from '../../components/PrimaryButton.jsx';
import ReportListItem from '../../components/ReportListItem.jsx';
import { getHome, retryInvestigation } from '../../lib/api.js';
import { fmtAgo, fmtCount, fmtDate, fmtDayLabel, fmtTime } from '../../lib/format.js';
import './home.css';

// Screen 1: Home (HANDOFF.md 1c/1d/1e/1f, design/mockups/home.png for the layout).
// Data comes from GET /api/home (lib/api.js): { company, monitor, openIncident | null, decided }.
// monitor.status: investigating (the AI is working) | error (an AI attempt failed) | ok.

const FIRST_LIST_SIZE = 2; // previous reports shown before «عرض الكل» (HANDOFF.md rule 12)
const POLL_MS = 3000; // while the AI investigates, Home asks the API again this often

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

export default function Home() {
  const [load, setLoad] = useState('loading'); // the call to the API: loading | error | ready
  const [data, setData] = useState(null);
  const [attempt, setAttempt] = useState(0); // +1 = load the page again (the API was not reachable)
  const [retrying, setRetrying] = useState(false); // true while «أعد المحاولة» re-runs the AI investigation
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    let ignore = false; // drop an old answer if a newer request has started
    setLoad('loading');
    getHome()
      .then((home) => {
        if (ignore) return;
        setData(home);
        setLoad('ready');
      })
      .catch(() => {
        if (!ignore) setLoad('error'); // never show the raw error
      });
    return () => {
      ignore = true;
    };
  }, [attempt]);
  const retry = () => setAttempt((n) => n + 1);

  // While the AI investigates, ask again every few seconds. This is "quiet": the screen stays as it
  // is (no «نحضّر الصفحة…») and only changes when the answer differs. Each new answer sets `data`,
  // which runs this effect again, until the status is no longer `investigating`.
  useEffect(() => {
    if (load !== 'ready' || retrying || data.monitor.status !== 'investigating') return undefined;
    let ignore = false;
    const timer = setTimeout(() => {
      getHome()
        .then((home) => {
          if (!ignore) setData(home);
        })
        .catch(() => {
          if (!ignore) setLoad('error');
        });
    }, POLL_MS);
    return () => {
      ignore = true;
      clearTimeout(timer);
    };
  }, [load, retrying, data]);

  // «أعد المحاولة» on the failure strip: run the AI investigation again, then show the fresh Home.
  // The request waits until the run ends; meanwhile the strip and card show "investigating".
  async function rerunInvestigation() {
    setRetrying(true);
    try {
      await retryInvestigation(data.openIncident.id);
    } catch {
      // 409 (already decided, already an AI report, or a run is going on now) or no connection:
      // nothing to show here, the fresh Home below shows the real state.
    }
    try {
      setData(await getHome());
    } catch {
      setLoad('error');
    }
    setRetrying(false);
  }

  const header = (
    <header className="home-header">
      <span className="home-header__logo">قلقوص</span>
      {data && <span className="home-header__admin">{data.company.admin.displayName}</span>}
    </header>
  );

  if (load !== 'ready') {
    return (
      <div className="home">
        <div className="home-top">
          {header}
          {load === 'loading' ? (
            <StatusBanner status="loading">نحضّر الصفحة…</StatusBanner>
          ) : (
            <StatusBanner
              status="error"
              action={
                <PrimaryButton small onClick={retry}>
                  أعد المحاولة
                </PrimaryButton>
              }
            >
              تعذّر فتح الصفحة الآن. تأكد أن قلقوص يعمل على هذا الجهاز، ثم أعد المحاولة.
            </StatusBanner>
          )}
        </div>
      </div>
    );
  }

  const { monitor, decided } = data; // decided: newest decision first
  const incident = data.openIncident; // only one card is designed (rule 11)
  // Which designed state to show:
  //   loading = the investigation is running (or being re-run); error = the latest AI attempt failed.
  const state =
    retrying || monitor.status === 'investigating'
      ? 'loading'
      : monitor.status === 'error'
        ? 'error'
        : incident
          ? 'open'
          : 'empty';

  return (
    <div className="home">
      <div className="home-top">
        {header}
        <Strip state={state} monitor={monitor} openCount={incident ? 1 : 0} onRetry={rerunInvestigation} />
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
function Strip({ state, monitor, openCount, onRetry }) {
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

  // A rule-based report gets the «تقرير أساسي» card, whatever the strip says (project rule).
  if (state === 'error' || incident.reportSource === 'rules') {
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
