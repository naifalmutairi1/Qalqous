# Qalqous — DESIGN.md

Single source of truth for every Qalqous screen. Visual reference: `Qalqous Style Sheet.dc.html`. Approved screen: `Qalqous Report.dc.html`. Anything not listed here is not part of the system; adding a color, size or component requires explicit approval.

---

## 1. Direction

- **Name:** Sand & Pine (رمل وصنوبر), direction 2c.
- **Concept:** a white sheet resting on warm sand, read late at night by a tense admin; it states what happened in short sentences and waits for one calm decision.
- **Adjectives:** soft, roomy, plain-spoken.
- **Never does:**
  1. Uses red, orange, warning icons, or any color to signal danger. Severity is carried by words, never by color.
  2. Uses Pine `#2F6B4F` anywhere except the confirmation box shown after a decision.
  3. Gives one decision button more visual weight than the other (color, size, fill, order emphasis, or wording length cues).

Additional hard bans: no gradients, no glass/blur, no drop shadows, no emoji as icons, no Inter, no letter-spacing.

---

## 2. Colors

| Token | Hex | Role | Allowed in | Not allowed |
|---|---|---|---|---|
| `sand` | `#F3EEE6` | Dominant: page background | Page background; number tile fill; evidence log bar; "are you sure?" box; status banner fill; disabled button fill and border; hover fill of decision button and list item | Text |
| `sheet` | `#FFFFFF` | Content surface | Main sheet; cards; decision button fill; evidence log line block; text and check glyph on `pine`; text on `bark` | — |
| `bark` | `#2B2620` | Primary text | Headlines, body text, values; fill + border of primary button and of the confirm ("نعم، …") button | Large background areas |
| `bark-soft` | `#4A4239` | Secondary text | Subline under headline; "are you sure?" body; incident card summary; evidence log toggle text; primary button hover fill | Borders |
| `clay-deep` | `#6E6253` | Labels and meta text | Fact labels; dates/times meta; helper text under buttons; tile captions; back link; list arrow | Fills, borders |
| `clay` | `#9A8B78` | Outlines and markers | 1.5px border of neutral buttons; status dot; disabled button text | Reading text (fails 4.5:1) |
| `line` | `#EFE8DD` | Dividers | 1px rules between fact rows, list items, and above the decision section; header separator | Fills, text |
| `pine` | `#2F6B4F` | Sharp accent: decision recorded | Confirmation box fill and the check glyph inside its white circle. Nothing else. | Buttons, links, icons, status, tiles, hover, focus |

Contrast (WCAG): `bark` on `sheet` 15.2:1 · `bark-soft` on `sheet` 9.6:1 · `clay-deep` on `sheet` 5.9:1, on `sand` 5.1:1 · `sheet` on `pine` 6.4:1 · `clay` on `sand` 2.9:1 (disabled text only, exempt).

Focus ring: 2px solid `bark`, offset 2px, on every interactive element (keyboard focus only, `:focus-visible`).

---

## 3. Typography

**Fonts**
- Display/titles: `'Almarai', sans-serif` — weights 700, 800.
- Body/UI: `'Tajawal', sans-serif` — weights 400, 500, 700.
- Technical values: `ui-monospace, 'SF Mono', Menlo, monospace` — weight 400 in logs, 600 in tiles and emphasized values.

**Scale (5 sizes)**

| Token | Font | Weight | Size | Line-height | Used for |
|---|---|---|---|---|---|
| `display` | Almarai | 800 | 44px desktop → 28px phone (`clamp(28px, 4.4vw, 46px)` on the Report headline) | 1.45 | The one headline per screen. Only bold moment on the page. |
| `tile-number` | Almarai | 700 | 34px | 1.2 | The number inside a number tile. Only there. |
| `title` | Almarai | 700 | 24px | 1.4 | Section titles («ماذا حدث», «قرارك»); incident card title; confirmation box title |
| `body` | Tajawal | 400 (500 buttons/toggles, 700 emphasis and button labels) | 17px | 1.8 | Fact values, paragraphs, button labels |
| `small` | Tajawal | 400 | 15px | 1.7 | Labels, meta, helper text, tile captions |

Rules: `text-wrap: balance` on `display`; `text-wrap: pretty` on paragraphs. `letter-spacing` is never set (default `normal`). Technical values take the size of their context (tile: 22–24px/600; body: 17px; log: 13–15px/1.9–2) and do not create a new scale step.

---

## 4. Spacing, radius, borders, shadows

**Spacing scale (px):** `4 · 8 · 12 · 16 · 24 · 32 · 48`. No other values.

| Value | Use |
|---|---|
| 4 | Label ↔ value inside a tile or list item |
| 8 | Inside small groups (dot + text, check + title rows) |
| 12 | Between tiles; between paired buttons; incident card internal gap |
| 16 | Section title ↔ content; fact row vertical padding; grid gaps between label and value |
| 24 | Card / tile / banner inner padding; status banner horizontal padding |
| 32 | Space above the decision section (paired with a `line` rule); primary button horizontal padding |
| 48 | Between sections; main sheet padding on desktop (24 on phone) |

**Radius:** `12` inner blocks (evidence log line block) · `20` tiles, cards, banners, evidence log bar, "are you sure?" box, confirmation box · `28` main sheet · `999` (pill) every button.

**Borders:** `1.5px solid clay` neutral buttons · `1.5px solid sand` disabled buttons · `1.5px solid bark` confirm button · `1px solid line` dividers. No other borders.

**Shadows:** none. Depth comes only from `sheet` on `sand`.

**Sizes:** button height 56px (secondary/small 48px). Minimum hit target 44×44px everywhere, phone included. Main sheet max inline-size 880px. Page inline padding `clamp(12px, 3vw, 40px)`.

---

## 5. Components

Only these ten exist. States not listed do not exist for that component.

### 5.1 Decision button (neutral pair)
Always rendered as an equal pair: «إبقاءه موقوف» and «إرجاع الحساب», same size, same style, side by side (`flex: 1 1 240px`, gap 12–16px), each with a `small` helper line in `clay-deep` below.
- **Default:** fill `sheet`, border 1.5px `clay`, text `bark` Tajawal 700 17px, height 56px, radius 999.
- **Hover:** fill `sand`. Transition `background 150ms`.
- **Pressed:** fill `sand`, border `bark-soft`.
- **Disabled (after a decision):** fill `sand`, border 1.5px `sand`, text `clay`, `cursor: not-allowed`, `disabled` attribute. Both buttons disable together and stay visible above the confirmation box.
- **Flow:** press → "are you sure?" box replaces the pair → «نعم، …» → disabled pair + confirmation box.

### 5.2 "Are you sure?" step (part of 5.1)
Box: fill `sand`, radius 20, padding 24. Title `title` «هل أنت متأكد؟». Body `body` in `bark-soft` describing the consequence in one or two sentences. Actions: confirm button (fill + border `bark`, text `sheet`, 700) and «رجوع» (neutral button style, 500). These two are intentionally unequal; the pair in 5.1 is not.

### 5.3 Primary button
For navigation only (e.g. «افتح التقرير»). Never used for the decision.
- **Default:** fill `bark`, text `sheet` Tajawal 700 17px, height 56px, padding-inline 32px, radius 999.
- **Hover:** fill `bark-soft`.
- **Pressed:** fill `bark-soft`, text `sheet`.
- **Disabled:** fill `sand`, text `clay`.
- **Small variant** («أعد المحاولة»): neutral button style, height 48px, padding-inline 24px, Tajawal 500 15px.

### 5.4 Number tile
Fill `sand`, radius 20, padding 20px 24px, gap 4. Number in `tile-number`; caption in `small` `clay-deep` below. Up to 3 per row (`repeat(auto-fit, minmax(200px, 1fr))`, gap 12); stacks on phone. Technical value tiles (IP) use the technical font 600 at 22–24px, `dir="ltr"`, aligned to the inline start of the RTL tile. Not interactive; no states.

### 5.5 Fact row
Grid `minmax(120px,180px) minmax(0,1fr)`, gap 16, padding-block 16 / padding-inline 4, `body`. Label in `clay-deep`, value in `bark`. 1px `line` between rows; none after the last. Not interactive.

### 5.6 Incident card (Home)
Sits on `sand`. Fill `sheet`, radius 20, padding 24, gap 12. Content order: meta (`small`, `clay-deep`: time · «ينتظر قرارك») → title (`title`) → one-line summary (`body`, `bark-soft`) → primary button «افتح التقرير». The whole card is not a link; only the button is.

### 5.7 Status banner
One component, two states. Fill `sand`, radius 20, padding 16px 24px, gap 12, `body`.
- **Loading:** 10px `clay` dot, opacity pulse 0.4 → 1 → 0.4 over 1.6s ease-in-out, infinite. Text states what is being checked and that the account is already suspended as a precaution.
- **Error:** 10px hollow dot (2px `clay` border, no fill). Text says the detailed investigation failed and the basic rule-based report is shown and is sufficient to decide. Trailing small primary-variant button «أعد المحاولة».
- No red, no icons, no exclamation marks.

### 5.8 Collapsible evidence log
- **Collapsed (default):** bar fill `sand`, radius 20, height ≥ 56px, padding-inline 20px, Tajawal 500 17px `bark-soft`. Label «سجلّ الأدلة (N سطراً)» with N in Arabic-Indic; chevron `▾` at inline end. Whole bar is the button.
- **Hover:** none beyond cursor pointer.
- **Expanded:** chevron `▴`; below the bar, a `sheet` block with radius 12, margin 0 12px 12px, padding 12px 16px, technical font 13–15px / line-height 1.9–2, `dir="ltr"`, `text-align: left`, `white-space: pre`, horizontal scroll on overflow.
- **Content:** only `LOGIN_FAIL` and `LOGIN_SUCCESS` lines, format `evt-NNNNN  YYYY-MM-DD HH:MM:SS  EVENT  user  ip`.

### 5.9 Confirmation box (Pine)
Appears only after a confirmed decision; persistent (no dismiss, no auto-hide). `role="status"`.
- Fill `pine`, text `sheet`, radius 20, padding `clamp(24px, 4vw, 36px)`, gap 8–12.
- Row 1: 44px `sheet` circle with `✓` in `pine` 800 + decision in `title` (Almarai 700–800), e.g. «قرارك: إبقاء حساب majed.f موقوفاً».
- Row 2: `body` «سُجّل القرار الساعة ١١:١٤ م، ٢٣ نوفمبر».
- Row 3: `small`/`body` next step, e.g. «الخطوة التالية: غيّر كلمة مرور ماجد.»
- No other states.

### 5.10 Previous-report list item
Link, min-height 64px, padding 8px 4px, gap 16, 1px `line` between items. Line 1 `body`: username (technical font, LTR) · outcome («أُرجع الحساب» / «بقي موقوفاً»). Line 2 `small` `clay-deep`: date and time. Trailing `←` in `clay-deep`.
- **Hover:** fill `sand`.
- **Pressed:** fill `sand`, text `bark`.

---

## 6. Arabic and RTL

- Root of every screen: `dir="rtl"` and `lang="ar"`.
- Layout uses logical properties only: `margin-inline-*`, `padding-inline-*`, `padding-block-*`, `inset-inline-*`, `border-inline-*`, `inline-size`, `text-align: start/end`. Never `left`/`right` — the single exception is the LTR evidence log block (`text-align: left`), which is itself `dir="ltr"`.
- Flex/grid order follows reading order; never use `row-reverse` to fake RTL.
- `letter-spacing` is never set on Arabic or Latin text.
- **Icons that mirror:** directional arrows. Back to Home is `→` (points to the inline start in RTL); "go to / open" in lists is `←`. If an SVG arrow is ever used, flip it with `transform: scaleX(-1)` under `[dir="rtl"]`.
- **Icons that do not mirror:** `✓`, `▾`/`▴` chevrons, the status dot.
- **Numerals:**
  - Ordinary numbers, counts, dates and times use Arabic-Indic digits `٠١٢٣٤٥٦٧٨٩`, with Arabic time suffixes «ص» / «م» (e.g. «١١:٠٢ م», «١٠ محاولات», «٢٣ نوفمبر»).
  - Technical values stay exactly as in the logs: Latin characters, Western digits, technical font, wrapped in `<span dir="ltr" style="unicode-bidi:isolate">`. This covers IP addresses (`203.0.113.102`), log line IDs (`evt-40131`), event names (`LOGIN_FAIL`, `LOGIN_SUCCESS`), and raw log timestamps (`2026-11-23 23:02:07`). Inside the evidence log, every value (usernames included) is technical font.
  - Usernames (`majed.f`) in running text, headlines and titles are Latin and LTR (wrapped in `<bdi>`) but use the font of their context (body, title or display), as in the approved mockups. They are not technical font there.
  - Latin proper names (e.g. company name `Najd Build Contracting`) are Latin and LTR but use the body font, not the technical font.
- **Copy tone:** calm Modern Standard Arabic, short sentences, no security jargon. State facts and consequences; do not use alarm words or exclamation marks.
- **Test data:** 10 failed logins in under 3 minutes (22:59:14–23:01:58), 1 success at 23:02:07 (shown «١١:٠٢ م»), IP `203.0.113.102` (documentation range only; never real internet IPs), user `majed.f`, permission «موظف عادي: يقرأ ملفات قسم المشتريات».
