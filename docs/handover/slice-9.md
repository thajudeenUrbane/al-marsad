# Slice 9: Arabic interface, reader tier (15 October 2026)

Doc 13 D3 and §4 row 9: the reader tier in Arabic, right to left. **Interface text only, and a draft:** the
translations are AI-drafted and "awaiting review by the scholars" (said in `site/i18n/ar.json`, whose first
key carries the English sentence, and in every Arabic page footer, in both languages).

## What exists
- `site/i18n/ar.json`: every key of `en.json`, plus the extra Arabic plural forms (two, few, many) of the
  counted strings. `Renderer(lang="ar")` builds a copy of the reader tier under `/ar/` at the same paths:
  home, Study, Research, an index per type, a page for every person, group, place, event and story, search
  and glossary (324 pages). `<html lang="ar" dir="rtl">`, hreflang alternates, and a language switch on every
  page (English pages link their Arabic twin; the switch keeps the path).
- **Data is never translated.** Names, claims, sources, story texts, glossary definitions, recorded dates and
  relation words stay as recorded. A Latin-script datum is marked `lang="en" dir="ltr"` (a span; a whole block
  for story prose or an English claim sentence); inside an Arabic sentence it is isolated (LRI/PDI) by
  `I18n.t`, which `Renderer.finish` turns into the span. Arabic names (6 places) are shown as before.
- Plurals: CLDR rules in `render.plural_category`, used by `I18n.tn`, `thread.js` and `search.js`.
- RTL: CSS was already logical. Added: breadcrumb and thread arrows mirrored, no letter-spacing or slanted
  Arabic, an Arabic system font stack (no web fonts), the A-Z letters kept left to right.
- Arabic search: the page, its notes, counts and "no match" text are Arabic; the engine (already
  Arabic-aware) and `search.json` are shared with English. Thread view: Arabic strings in `ar/thread.json`.
- The Arabic hub lists every built view and the earlier prototypes, linked from the site root and labelled
  "English only for now".
- Checks: `ar/` is covered by the budget and HTML checks (HTML check now also needs lang/dir, twins and
  hreflang alternates); `check_hub.py` covers `/ar/`; new `site/check_arabic.cjs` (JS off and on, 390x844: dir,
  no sideways scroll, font stack, footer notice, mirrored arrows, switch both ways, Arabic search and thread);
  `site/tests/test_arabic.py` (keys, placeholders, plurals, dates, built copy). One new line in `check_all.sh`.

## Decisions for the maintainer
1. **Date order per language.** The Gregorian-first rule is kept in Arabic ("622 م (1 هـ)"). Arabic texts
   usually put Hijri first; say if the Arabic pages should.
2. Western digits (0-9) in Arabic pages, as in the data and search; Arabic-Indic digits are a switch away.
3. Gregorian month names: the pan-Arab set (يناير، فبراير ...), not the Levantine one (كانون الثاني ...).
4. The project name on Arabic pages is "المرصد" (English pages keep "al-Marṣad").
5. Whether the Plain words switch makes sense on Arabic pages (it swaps Arabic terms in English data text).

## What the scholars must review
- All of `ar.json`, as a draft. Especially: **إفادة** for "claim"; **التغطية** and its levels (هيكل أولي,
  مخطط, موثَّق بمصادر, مُراجَع, مُتحقَّق منه); the status words (مقترَحة, قيد المراجعة, مقبولة, مرفوضة);
  **الطبقة (الجيل)** for ṭabaqa; the name-form labels (الكنية, اللقب, النسب, النسبة, نظام النقحرة);
  "مسائل مفتوحة" and "ما لا يُعرف"; the dating notes (convert, precision, basis); the honorific strings
  (unchanged, still not shown); the search help; the counted phrases (case and number agreement).
- That no sentence implies a status or ruling the English one does not.

## Left for follow-up
- Interactive views are English only: observatory, lifelines, timeline, map, ask, learn (and the earlier
  prototypes); each needs its own i18n keys and builder changes, and the hub label comes off when it has them.
- hreflang alternates are relative (no canonical site URL is known yet); make them absolute at deploy.
- The Arabic page `<title>` cannot carry markup: English names there are isolated, not tagged `lang`.
- Arabic names exist for 6 places only; Arabic search of Arabic data is thin until more are recorded.
- Glossary definitions, story texts and claim wordings are English until the project records Arabic ones.
