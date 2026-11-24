import { useState } from 'react';
import DecisionPair from '../../components/DecisionPair.jsx';
import ConfirmBox from '../../components/ConfirmBox.jsx';
import ConfirmationBox from '../../components/ConfirmationBox.jsx';
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
      helper: <>إذا تأكدت أن {n} هو من دخل.</>,
      sure: <>سيعود حساب {u} للعمل فوراً. افعل هذا فقط إذا تأكدت أن {n} هو من دخل.</>,
      confirm: 'نعم، أرجِع الحساب',
      done: <>قرارك: إرجاع حساب {u}</>,
      next: 'سيواصل قلقوص مراقبة الحساب وينبّهك إن تكرر النشاط.',
    },
  };
}

// decision: the saved decision { choice, decidedAt } or null. onDecide(choice) saves one.
export default function Decision({ username, name, decision, onDecide }) {
  const [pending, setPending] = useState(null); // the choice waiting for "are you sure?"
  const [justDecided, setJustDecided] = useState(false);
  const copy = copyFor(username, name);
  const options = ['keep_suspended', 'restore'].map((choice) => ({ choice, ...copy[choice] }));

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
      <ConfirmBox
        confirmLabel={c.confirm}
        onBack={() => setPending(null)}
        onConfirm={() => {
          setJustDecided(true);
          onDecide(pending);
        }}
      >
        {c.sure}
      </ConfirmBox>
    );
  }

  return <DecisionPair options={options} onPick={setPending} />;
}
