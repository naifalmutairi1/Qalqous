import { useState } from 'react';
import DecisionPair from '../../components/DecisionPair.jsx';
import ConfirmBox from '../../components/ConfirmBox.jsx';
import ConfirmationBox from '../../components/ConfirmationBox.jsx';
import StatusBanner from '../../components/StatusBanner.jsx';
import PrimaryButton from '../../components/PrimaryButton.jsx';
import { fmtDate, fmtTime } from '../../lib/format.js';

// The decision flow (HANDOFF.md 3.1 steps 9-12):
//   equal pair -> "are you sure?" -> disabled pair + Pine confirmation.
// «رجوع» goes back to the pair and saves nothing. A decision is final.
//
// Copy is word for word from HANDOFF.md §7. `user` is the username (majed.f), `name` the first name (ماجد).
// Usernames sit in <bdi> so the Latin text does not push the Arabic punctuation around.
function copyFor(user, name) {
  const u = <bdi>{user}</bdi>;
  const n = <bdi>{name}</bdi>;
  return {
    keep_suspended: {
      label: 'إبقاءه موقوف',
      helper: 'لن يستطيع أحد الدخول إليه حتى تغيّر كلمة المرور.',
      sure: <>سيبقى حساب {u} موقوفاً. لن يستطيع أحد الدخول إليه، ولا صاحب الحساب نفسه، حتى تغيّر كلمة المرور وتعيد تفعيله.</>,
      confirm: 'نعم، أبقِه موقوفاً',
      done: <>قرارك: إبقاء حساب {u} موقوفاً</>,
      next: <>الخطوة التالية: غيّر كلمة مرور {n}.</>,
    },
    restore: {
      label: 'إرجاع الحساب',
      helper: 'إذا تأكدت أن صاحب الحساب هو من دخل.',
      sure: <>سيعود حساب {u} للعمل فوراً. افعل هذا فقط إذا تأكدت أن صاحب الحساب هو من دخل.</>,
      confirm: 'نعم، أرجِع الحساب',
      done: <>قرارك: إرجاع حساب {u}</>,
      next: 'سيواصل قلقوص مراقبة الحساب وينبّهك إن تكرر النشاط.',
    },
  };
}

// decision: the saved decision { choice, decidedAt } or null.
// onDecide(choice) saves one on the server; it returns a promise that fails if saving failed.
export default function Decision({ username, name, decision, onDecide }) {
  const [pending, setPending] = useState(null); // the choice waiting for "are you sure?"
  const [justDecided, setJustDecided] = useState(false);
  const [saving, setSaving] = useState(false); // true while the server is saving: ignore more clicks
  const [saveFailed, setSaveFailed] = useState(false);
  const copy = copyFor(username, name);
  const options = ['keep_suspended', 'restore'].map((choice) => ({ choice, ...copy[choice] }));

  async function save() {
    if (saving) return;
    setSaving(true);
    setSaveFailed(false);
    setJustDecided(true); // move focus to the confirmation when it appears
    try {
      await onDecide(pending);
    } catch {
      setJustDecided(false);
      setSaveFailed(true); // HANDOFF.md U5: stay on "are you sure?" and offer «أعد المحاولة»
    } finally {
      setSaving(false);
    }
  }

  if (decision) {
    const c = copy[decision.choice];
    return (
      <>
        <DecisionPair options={options} disabled />
        <ConfirmationBox
          title={c.done}
          recordedAt={`سُجّل القرار الساعة ${fmtTime(decision.decidedAt)}، ${fmtDate(decision.decidedAt)}`}
          nextStep={c.next}
          focusOnShow={justDecided}
        />
      </>
    );
  }

  if (pending) {
    const c = copy[pending];
    return (
      <>
        {saveFailed && (
          <StatusBanner
            status="error"
            action={
              <PrimaryButton small onClick={save}>
                أعد المحاولة
              </PrimaryButton>
            }
          >
            لم نتمكن من حفظ قرارك. تأكد أن قلقوص يعمل على هذا الجهاز، ثم أعد المحاولة.
          </StatusBanner>
        )}
        <ConfirmBox
          confirmLabel={c.confirm}
          onBack={() => {
            setPending(null);
            setSaveFailed(false);
          }}
          onConfirm={save}
        >
          {c.sure}
        </ConfirmBox>
      </>
    );
  }

  return <DecisionPair options={options} onPick={setPending} />;
}
