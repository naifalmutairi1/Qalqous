# DESIGN.md

<!--
  ذاكرة التصميم حقة مشروعك. الـagent يقراه قبل أي شغل واجهات (السطر في CLAUDE.md يقول له كذا).
  تعبّيه في تطبيق ٣ من الـmockup اللي اخترته: إما بالـprompt "اكتب DESIGN.md" من صفحة اليوم الثاني،
  أو بيدك. كل [ ] لازم تنمسح وتنكتب مكانها قيمة. قيم دقيقة، مو "modern" ولا "clean".
  مثال معبّى كامل: example/DESIGN.md (كورة الخميس).
  أقل من ٢٠٠ سطر.
-->

## 1. Direction

- Name: [اسم الاتجاه اللي اخترته، مثال: لوحة الملعب]
- Concept: [one line: what the product feels like and why it fits its users]
- Adjectives: [three words]
- Primary reference: `design/refs/01-primary-[name].png`
- Mockup: `design/mockups/home-375.png`

### This design never does

- [three things, e.g. gradients, emoji as icons, centered body text]
- No Inter, Roboto, Arial, Space Grotesk. No purple gradients. No three identical cards in a row.

## 2. Colors

One dominant colour, one sharp accent. Hex values read from a screenshot are estimates: check them by eye.

| Token | Hex | Role | Allowed on |
|---|---|---|---|
| `--color-bg` | [#] | page background | |
| `--color-surface` | [#] | cards, sheets | |
| `--color-ink` | [#] | main text | |
| `--color-muted` | [#] | secondary text | never for long paragraphs |
| `--color-primary` | [#] | main actions only | buttons, active nav |
| `--color-accent` | [#] | one highlight per screen | never for text blocks |
| `--color-line` | [#] | borders, dividers | |
| `--color-danger` | [#] | errors | error text and banners only |

Contrast: text on bg and on surface passes WCAG AA (4.5:1).

## 3. Typography

- Display font: [name] [weights], from Google Fonts
- Body font (must support Arabic): [Noto Sans Arabic / Tajawal / Cairo / Readex Pro / Almarai] [weights]
  - Check it: type «حتى» and «على» in the font. If the final ى looks wrong (some fonts draw «حتى» like «حق»), pick another one.
- Scale (size / line-height / weight):
  - h1: [ ] / [ ] / [ ]
  - h2: [ ] / [ ] / [ ]
  - body: [16px or more] / [1.7-1.8] / [ ]
  - caption: [ ] / [ ] / [ ]
- No letter-spacing and no uppercase on Arabic. Opaque text colours only.

## 4. Spacing and layout

- Spacing scale: [4, 8, 12, 16, 24, 32, 48]: use only these steps
- Radius: [ ]   Border: [ ]   Shadow: [none / exact value]
- Max content width: [ ]
- Breakpoints: 375 (design here first) / 768 / 1280
- Touch targets: 44px minimum

## 5. Components

For each one: default, hover, focus, disabled, loading, error.

- Button (primary, secondary): [shape, colours, states]
- Input: [ ]
- Card: [ ]
- Navigation: [top / bottom, active state]
- List item: [ ]
- Empty state: [one short line + one action]
- Loading: [skeletons that match the real layout]
- Error: [plain Arabic + retry]

## 6. Arabic and RTL

- `<html lang="ar" dir="rtl">`. Logical properties only. Flex rows follow `dir`.
- Mirror: back/forward arrows, chevrons, progress that fills along the reading direction.
- Never mirror: logos, play/pause, checkmarks, clocks, numbers.
- English names in `<bdi>`; codes and long numbers in `<span dir="ltr">`; user inputs `dir="auto"`.
- Numerals: Arabic-Indic ١٢٣ for every number the user reads in the Arabic UI (counts, prices, times,
  percents); 0-9 only inside code. Never zero-pad (٥ not ٠٥); no middle dot (U+00B7) next to a number
  (the Arabic zero is a dot), use «،». A count that is still 0 says it in words («ما فيه شي للحين»),
  not a lone «٠». Calendar: [Gregorian / Hijri].
  Locale in `web/src/lib/format.js`: [ar-SA-u-ca-gregory (default) / ar-SA (Hijri)]
  Choice: [keep Arabic-Indic / switch to Western 0-9 everywhere because ...]
  (0-9 = `ar-SA-u-ca-gregory-nu-latn`; pick it only if your users expect it, and write why.)

## 7. Motion

- Durations: [ ]   Easing: [ ]
- The one page-load animation: [what enters, in what order] (or "none yet")
- Respects `prefers-reduced-motion`.

## 8. The one bold place

- [The single strong moment on the main screen. Everything else stays calm.]
