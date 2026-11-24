// format.js: ONE place for numbers, dates and times. Never build them by hand in a screen.
//
// Numerals (DESIGN.md §6): Arabic-Indic digits ١٢٣ with «ص»/«م» for everything the user reads,
// Gregorian calendar. Raw log timestamps are the exception: they stay as in the logs (0-9),
// so fmtLogStamp uses a Latin locale on purpose.
// Never zero-pad (٥ not ٠٥) and never put a middle dot (U+00B7) next to a number: use «،».
export const LOCALE = 'ar-SA-u-ca-gregory';

// All times are shown in the company's timezone (server/config.py COMPANY timezone), not the browser's.
// Without this, a laptop set to another timezone would show the wrong hour.
const TIME_ZONE = 'Asia/Riyadh';

const number = new Intl.NumberFormat(LOCALE);
const time = new Intl.DateTimeFormat(LOCALE, { hour: 'numeric', minute: '2-digit', timeZone: TIME_ZONE });
const timeSec = new Intl.DateTimeFormat(LOCALE, {
  hour: 'numeric', minute: '2-digit', second: '2-digit', timeZone: TIME_ZONE,
});
const date = new Intl.DateTimeFormat(LOCALE, { day: 'numeric', month: 'long', timeZone: TIME_ZONE });
const weekday = new Intl.DateTimeFormat(LOCALE, { weekday: 'long', timeZone: TIME_ZONE });
const logStamp = new Intl.DateTimeFormat('en-CA', {
  year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23', timeZone: TIME_ZONE,
});

// ١٠
export const fmtNumber = (n) => number.format(n);
// ١١:٠٢ م
export const fmtTime = (iso) => time.format(new Date(iso));
// ١١:٠٢:٠٧ م
export const fmtTimeSec = (iso) => timeSec.format(new Date(iso));
// ٢٣ نوفمبر
export const fmtDate = (iso) => date.format(new Date(iso));
// الاثنين ٢٣ نوفمبر (no comma between weekday and date, as in the design)
export const fmtWeekdayDate = (iso) => `${weekday.format(new Date(iso))} ${fmtDate(iso)}`;

// Time between two moments: «٢ د ٤٤ ث». Minutes are left out when zero: «٤٤ ث».
export function fmtDuration(fromIso, toIso) {
  const seconds = Math.round((new Date(toIso) - new Date(fromIso)) / 1000);
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return min > 0 ? `${fmtNumber(min)} د ${fmtNumber(sec)} ث` : `${fmtNumber(sec)} ث`;
}

// A day label for "when", relative to now, in the company timezone:
// same day -> «الليلة» (from 6 pm) or «اليوم»; the day before -> «أمس»; older -> «٢٣ نوفمبر».
const dayKey = new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone: TIME_ZONE });
const hour24 = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', hourCycle: 'h23', timeZone: TIME_ZONE });
export function fmtDayLabel(iso, now = new Date()) {
  const d = new Date(iso);
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  if (dayKey.format(d) === dayKey.format(now)) return Number(hour24.format(d)) >= 18 ? 'الليلة' : 'اليوم';
  if (dayKey.format(d) === dayKey.format(yesterday)) return 'أمس';
  return fmtDate(iso);
}

// How long ago: «قبل ٣ دقائق», «قبل ساعتين», «أمس». Intl.RelativeTimeFormat writes the Arabic for us.
const relative = new Intl.RelativeTimeFormat(LOCALE, { numeric: 'auto' });
export function fmtAgo(iso, now = new Date()) {
  const minutes = Math.round((new Date(iso) - now) / 60000); // negative = in the past
  if (Math.abs(minutes) < 60) return relative.format(minutes, 'minute');
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return relative.format(hours, 'hour');
  return relative.format(Math.round(hours / 24), 'day');
}

// Arabic nouns change form with the count: ١٠ أسطر، ١١ سطراً، سطران.
// Intl.PluralRules tells us which form a number needs: one, two, few (3-10), many (11-99), other.
const plural = new Intl.PluralRules('ar');
export const pluralForm = (n) => plural.select(n);

// fmtCount(11, { one: 'سطر واحد', two: 'سطران', few: '{n} أسطر', many: '{n} سطراً', other: '{n} سطر' })
//   -> «١١ سطراً». {n} is replaced by the number in Arabic-Indic digits.
export function fmtCount(n, forms) {
  const form = forms[pluralForm(n)] ?? forms.other;
  return form.replace('{n}', fmtNumber(n));
}

// Raw log timestamp, exactly like the log file: 2026-11-23 23:02:07 (Western digits).
export function fmtLogStamp(iso) {
  const p = Object.fromEntries(logStamp.formatToParts(new Date(iso)).map((x) => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}:${p.second}`;
}
