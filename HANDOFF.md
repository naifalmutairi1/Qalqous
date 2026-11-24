# Qalqous (قلقوص) — HANDOFF.md

Build spec. Sources: `Qalqous Report.dc.html` (hi-fi Report), `Qalqous Wireframes.dc.html` (Home 1c + states 1d/1e/1f, Report 1g), `Qalqous Style Sheet.dc.html`, `DESIGN.md` (visual rules — follow it exactly), `mock.json` (sample data).
`[?]` = assumed, not visible in the screens. Everything else is decided.

---

## 1. Who and why

- **Primary persona:** Abu Fahad (أبو فهد), 34, the only IT person at a 25-person contracting company (Najd Build Contracting). Knows what a log and an IP are; cannot tell an attack from a normal mistake. Opens Qalqous on his laptop late at night after an alert email, tense.
- **Core task:** within minutes, learn whether an account was taken over and what that account can reach, then decide: restore the account or keep it suspended.
- **Not for:**
  - Contacting the employee (outside Qalqous).
  - Storing, checking or comparing passwords (Qalqous never sees them).
  - Analysing anything other than login events (`LOGIN_FAIL`, `LOGIN_SUCCESS`).
  - Suspending real accounts — suspension happens in the simulated data only.
  - Multi-admin teams, roles or permissions management [?].

---

## 2. Screens

1. **Home (1c)** — status strip, the open incident card (or calm empty state), last decision, previous-reports list that expands in place via «عرض الكل».
2. **Report (1g)** — headline, what happened (3 number tiles + 2 fact rows), what the account can access (one line), decision (neutral pair → "are you sure?" → Pine confirmation), collapsible evidence log.

There is no third page. Only Arabic RTL; laptop-first at 1280px, readable down to phone width.

---

## 3. Flows

### 3.1 Happy path — decide on an incident
1. Logs arrive. Detection rule fires on `majed.f`: ≥5 `LOGIN_FAIL` within 10 min, followed by a `LOGIN_SUCCESS`.
2. Qalqous opens an incident and suspends `majed.f` (simulated).
3. (Should) One alert email is sent for this new incident.
4. AI investigation runs. Home shows the **loading** banner/card (1e).
5. Investigation completes. Home shows the **incident card** (1c): «أوقفنا حساب majed.f مؤقتاً», chips/summary, «افتح التقرير».
6. Abu Fahad presses «افتح التقرير» → Report.
7. He reads headline, tiles (١٠ / ١١:٠٢ م / 203.0.113.102), rows (duration, seen before), access line.
8. Optional: expands «سجلّ الأدلة (١١ سطراً)» to read raw lines.
9. He presses «إبقاءه موقوف» **or** «إرجاع الحساب».
10. The pair is replaced by «هل أنت متأكد؟» with the consequence text.
11. He presses «نعم، أبقِه موقوفاً» / «نعم، أرجِع الحساب».
12. Decision is saved with timestamp. Both decision buttons render **disabled**; the **Pine confirmation box** appears below them, persistent: decision, «سُجّل القرار الساعة …», next step.
13. Back on Home: incident is no longer open; it becomes «آخر قرار» and the top item in previous reports.

### 3.2 Unhappy paths
- **U1 — Changes mind at "are you sure?":** presses «رجوع» → returns to the neutral pair; nothing saved.
- **U2 — AI investigation fails:** Home shows the **error** banner (1f) and the incident card tagged «تقرير أساسي» with «افتح التقرير الأساسي». The Report is built from rules only; every finding without an evidence log line is labelled «غير مؤكد». «أعد المحاولة» re-runs the AI investigation. The decision is still allowed on the basic report.
- **U3 — Investigation still running when he opens Qalqous:** Home shows loading (1e). The account is already suspended. He waits; no Report link until a report (AI or basic) exists [?].
- **U4 — No incidents:** Home shows the empty state (1d) «قلقوص يراقب. لا توجد حوادث مفتوحة.» with last decision and previous reports.
- **U5 — Saving the decision fails:** [?] not designed. Proposal: stay on "are you sure?", keep buttons enabled, show the error status banner with «أعد المحاولة».
- **U6 — Report opened for an already-decided incident** (from previous reports): buttons disabled + Pine box with the stored decision and time [?].
- **U7 — Two incidents open at once:** [?] not designed (Home shows «حادث مفتوح واحد»). See open questions.
- **U8 — Logs not received / monitor down:** [?] not designed.

---

## 4. Data (nouns)

**Company**
- `name`: string ("Najd Build Contracting")
- `timezone`: string [?] (assumed `Asia/Riyadh`)

**Admin**
- `id`: string
- `displayName`: string («أبو فهد»)

**Monitor status**
- `accountsMonitored`: integer (25)
- `lastCheckAt`: datetime
- `status`: enum `ok | investigating | error`

**Account**
- `username`: string, Latin (e.g. `majed.f`) — unique key
- `displayName`: string (Arabic or Latin)
- `department`: string [?]
- `access`: string — one line of what it can reach («موظف عادي: يقرأ ملفات قسم المشتريات»)
- `status`: enum `active | suspended`
- Known IPs are **derived** from past `LOGIN_SUCCESS` logs, not stored [?] (mock includes `knownIps` for convenience)

**Log line** (read-only input)
- `id`: string (`evt-NNNNN`)
- `at`: datetime (second precision)
- `event`: enum `LOGIN_FAIL | LOGIN_SUCCESS`
- `username`: string
- `ip`: string (IPv4)

**Incident**
- `id`: string
- `username`: string → Account
- `status`: enum `investigating | awaiting_decision | decided`
- `reportSource`: enum `ai | rules`
- `headline`: string
- `openedAt`, `suspendedAt`, `reportReadyAt`: datetime
- `failedAttempts`: integer
- `firstFailAt`, `lastFailAt`, `successAt`: datetime
- `sourceIp`: string
- `ipSeenBefore`: boolean
- `access`: string (snapshot of the account's access line at incident time [?])
- `evidenceLogIds`: string[] → Log line
- `findings`: `{ text: string, evidenceLogIds: string[], confirmed: boolean }[]`
- `decision`: `{ choice: "restore" | "keep_suspended", decidedAt: datetime, decidedBy: string } | null`

**Alert email** (Should)
- `incidentId`: string
- `sentAt`: datetime
- `to`: string [?]

---

## 5. Actions (verbs)

All actions are done by Abu Fahad (the single admin) unless marked System.

- **Detect incident** — System, background. Reads log lines. Creates an incident when the rule matches; sets account `status = suspended`; sets incident `status = investigating`.
- **Investigate (AI)** — System. Reads the incident's log lines and the account's `access`. Writes `findings`, `headline`, `reportSource = ai`, `status = awaiting_decision`. On failure: builds the rule-based report, `reportSource = rules`, monitor `status = error`.
- **Send alert email** — System (Should). One per new incident. Writes Alert email.
- **View Home** — Home. Reads monitor status, the open incident, the latest decided incident, decided incidents list.
- **Expand previous reports («عرض الكل»)** — Home. UI only; reads all decided incidents.
- **Open report («افتح التقرير» / «افتح التقرير الأساسي» / list item)** — Home → Report. Reads one incident + its log lines.
- **Retry investigation («أعد المحاولة»)** — Home (error banner). Re-runs Investigate on the incident.
- **Toggle evidence log** — Report. UI only; reads the incident's log lines.
- **Pick decision («إبقاءه موقوف» / «إرجاع الحساب»)** — Report. UI only; moves to "are you sure?".
- **Cancel («رجوع»)** — Report. UI only; back to the pair.
- **Confirm decision («نعم، …»)** — Report. Writes `incident.decision`, `incident.status = decided`. On `restore`: account `status = active`. On `keep_suspended`: account stays `suspended`. Allowed once per incident.

---

## 6. Rules

1. **Detection:** ≥5 `LOGIN_FAIL` for one username within any 10-minute window, followed by a `LOGIN_SUCCESS` for that username, opens one incident. Whether the success must come from the same IP or within the same window is [?].
2. Opening an incident suspends the account immediately (simulated data only).
3. One alert email per new incident (Should, after all Musts). No email for retries or decisions [?].
4. **Seen before** = this account had a `LOGIN_SUCCESS` from this IP earlier in the logs. Otherwise «لا، أول مرة يظهر هذا العنوان».
5. If AI investigation fails, show the rule-based report. Any finding without at least one evidence log ID is labelled «غير مؤكد».
5a. **Findings = the facts on the Report** (decided 2026-11-24). The five facts shown are the findings: the three tiles (failed attempts, success time, source IP) and the two fact rows (duration, seen before). Each must be backed by at least one evidence log line of the incident:
   - failed attempts → the `LOGIN_FAIL` lines
   - success time → the `LOGIN_SUCCESS` line at `successAt`
   - source IP → the lines from `sourceIp`
   - duration → the `LOGIN_FAIL` lines at `firstFailAt` and `lastFailAt`
   - seen before → the `LOGIN_SUCCESS` line from `sourceIp`
   A fact with no backing line shows «(غير مؤكد)» next to its value. This applies to AI and rule-based reports alike.
6. The rule-based report is sufficient to decide; the decision is never blocked by an AI failure.
7. A decision requires a confirm step. Cancelling saves nothing.
8. A decision is final: after confirm, both buttons are disabled and the Pine box persists. No undo [?].
9. Only logs with `LOGIN_FAIL` / `LOGIN_SUCCESS` are accepted; any other event type is ignored [?].
10. Qalqous never stores, displays or compares passwords.
11. Home shows at most one open incident card (only one designed) [?].
12. «آخر قرار» = the most recent `decision.decidedAt`. Previous reports = decided incidents, newest first; first 2 shown, «عرض الكل (N)» expands the rest in place.
13. Display: ordinary numbers/dates/times in Arabic-Indic digits with «ص»/«م»; usernames, IPs, log IDs, event names and raw log timestamps in Latin/Western digits, monospace, LTR.
14. Only documentation IPs (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) in test and mock data.
15. Pine `#2F6B4F` appears only in the confirmation box. Decision buttons are a neutral equal pair. No red anywhere.

---

## 7. States (exact copy)

### Home
- **Open incident (default):** strip «حادث مفتوح واحد · ٢٤ حساباً آخر بلا ملاحظات». Card meta «الليلة · ١١:٠٢ م», title «أوقفنا حساب majed.f مؤقتاً», chips «١٠ محاولات فاشلة» · «عنوان جديد» · «موظف عادي», button «افتح التقرير». Side: «آخر قرار» «أرجعتَ حساب sara.k · ١٨ نوفمبر»; «التقارير السابقة» items «sara.k · أُرجع ١٨ نوفمبر», «khalid.m · بقي موقوفاً ٢ نوفمبر», «عرض الكل (١٢) ←».
- **Empty:** strip «٢٥ حساباً · آخر فحص قبل ٣ دقائق». Main «قلقوص يراقب. لا توجد حوادث مفتوحة.» Side unchanged.
- **Loading:** strip «قلقوص يراجع نشاطاً غير معتاد الآن». Card title «نراجع ما حدث على حساب majed.f», body «يستغرق هذا عادةً أقل من دقيقتين. أوقفنا الحساب مؤقتاً احتياطاً.» Steps: «جمعنا سجلات الدخول» ✓, «قارنّا العنوان بالعناوين المعروفة» ✓, «نحدّد ما يستطيع الحساب الوصول إليه…» (pulsing).
- **Error:** strip «تعذّر إكمال التحقيق التفصيلي. نعرض لك التقرير الأساسي المبني على القواعد، وهو كافٍ لاتخاذ القرار.» + «أعد المحاولة». Card tag «تقرير أساسي», title «أوقفنا حساب majed.f مؤقتاً», body «١٠ محاولات فاشلة ثم دخول ناجح الساعة ١١:٠٢ م من عنوان جديد · ينتظر قرارك», button «افتح التقرير الأساسي».
- **No previous reports:** [?] not designed. Proposal: hide «آخر قرار» and the list.

### Report
- **Default:** meta «تقرير حادث · الإثنين ٢٣ نوفمبر، ١١:٠٥ م»; headline «أوقفنا حساب majed.f مؤقتاً: احتمال دخول غير مصرّح به»; subline «لم يُستخدم الحساب منذ إيقافه. نحتاج قرارك: هل تبقيه موقوفاً أم تعيده؟»; tiles «١٠ · محاولات بكلمة مرور خاطئة», «١١:٠٢ م · نجح الدخول بعدها، مرة واحدة», «203.0.113.102 · مصدر الدخول»; rows «المدة: من ١٠:٥٩:١٤ م إلى ١١:٠١:٥٨ م (٢ د ٤٤ ث)، ثم دخول ناجح ١١:٠٢:٠٧ م», «هل رأيناه من قبل؟ لا، أول مرة يظهر هذا العنوان في شركتك»; access «موظف عادي: يقرأ ملفات قسم المشتريات.»
- **Decision helpers:** under «إبقاءه موقوف»: «لن يستطيع أحد الدخول إليه حتى تغيّر كلمة المرور.»; under «إرجاع الحساب»: «إذا تأكدت أن ماجد هو من دخل.»
- **Are you sure (keep):** «سيبقى حساب majed.f موقوفاً. لن يستطيع أحد الدخول إليه، ولا صاحب الحساب نفسه، حتى تغيّر كلمة المرور وتعيد تفعيله.» → «نعم، أبقِه موقوفاً» / «رجوع».
- **Are you sure (restore):** «سيعود حساب majed.f للعمل فوراً. افعل هذا فقط إذا تأكدت أن ماجد هو من دخل.» → «نعم، أرجِع الحساب» / «رجوع».
- **Confirmed (keep):** «قرارك: إبقاء حساب majed.f موقوفاً» · «سُجّل القرار الساعة {time}، {date}» · «الخطوة التالية: غيّر كلمة مرور ماجد.»
- **Confirmed (restore):** «قرارك: إرجاع حساب majed.f» · «سُجّل القرار الساعة {time}، {date}» · «سيواصل قلقوص مراقبة الحساب وينبّهك إن تكرر النشاط.»
- **Evidence log:** «سجلّ الأدلة (١١ سطراً)» collapsed by default.
- **Basic report (rules):** [?] not separately designed. Built: same layout + «تقرير أساسي» line under meta; unconfirmed facts suffixed «(غير مؤكد)» (rule 5a).
- **Loading / error loading the report itself:** [?] not designed. Proposal: reuse the Home status banner.

---

## 8. Sample data

See `mock.json`. Contains: company, monitor status, 3 accounts (`majed.f` — long Arabic name «ماجد بن فهد بن عبدالرحمن العتيبي»; `sara.k` — English name «Sarah Kelly»; `khalid.m`), login-only logs, and 3 incidents (open `majed.f`; decided `sara.k` restore 18 Nov 09:10; decided `khalid.m` keep suspended 2 Nov 19:45).
Note: Home shows «عرض الكل (١٢)»; mock has 2 decided incidents. The count must be derived from data, not hard-coded.

---

## 9. Open questions for the backend

1. Log ingestion: push or pull, format, and how often? What does «آخر فحص قبل ٣ دقائق» measure?
2. Detection window: must the `LOGIN_SUCCESS` fall inside the same 10-minute window, and must it come from the same IP as the failures?
3. Can one account have two open incidents? What if a new burst hits an already-suspended account?
4. How are several open incidents at once shown on Home?
5. Where does each account's one-line `access` description come from — entered by Abu Fahad, imported, or generated?
6. AI investigation: timeout value, retry limit, and what exactly marks it "failed"?
7. Is a decision really final, or can Abu Fahad change it later? Is there an audit trail beyond `decidedAt` / `decidedBy`?
8. Restoring in simulation: does «إرجاع الحساب» only flip a flag, or call a (mock) directory API?
9. Alert email: recipient, sender, contents, and deep link to the Report?
10. Timezone source for display (company setting vs browser)?
11. Log retention: how far back does "seen before" look?
12. Authentication for Abu Fahad himself to open Qalqous?
