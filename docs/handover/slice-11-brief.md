# Slice 11 brief — one graph: the full Sīra joins, cleaned

Context: README "Standing rules"; docs/handover/sira-full.md (the full-book pass, branch `sira-full-pass`) and ingest/full-pass-instructions.md; docs/handover/maintainer-answers-3.md (chapter F, P8, P9, G5, G6, S6, H3, W7). Do not read chat history; this file is the brief. Work in two parts on two branches: 11a (data) first, then 11b (site). Statuses stay `proposed`; nothing is invented.

## 11a — data (branch `slice-11a-graph`, from `sira-full-pass` rebased on main)
1. **Join (F15).** Move `ontology/corpus-full/ibn-hisham-full.ttl` into the unified build. `build_graph.py` must still finish in reasonable time: validate each corpus file on its own when it changes (cache by checksum), and validate the union with the shapes that cross files. Record the timings.
2. **Duplicates (F3).** Write `ontology/tools/propose_merges.py`. It proposes merges with their evidence (same Arabic form, father line, shared section, cross-layer label match), first for events (Yarmūk ×2, the boycott annulment ×2, Abyssinia split, Badr across layers), then for the 100 most-connected people, then for titles. Output: a reviewable CSV (`ontology/corpus/merge-proposals.csv`, with confidence and evidence). An editor approves rows. An approved row is applied through identity.csv's existing rules: old IDs become variants, and old addresses redirect (P8, G5). Kunya-only and same-name cases are marked for scholars.
3. **Sides (F1).** For each person in a battle list, add one claim that they fought with the Prophet ﷺ or against him at that event. Each claim rests on the list heading the text gives, with the span quoted. Use `rel_fought_alongside` / `rel_fought_against` with an event link if the shapes allow it. Otherwise add the smallest new relation, following relations.ttl's pattern, and say why in the handover.
4. **Formula (F5) and voice (F7).** On every `rel_narrated_from` record the formula as written: ḥaddathanī, akhbaranī, ʿan, balaghanī, zaʿamū or qāla. The quote is already in the span, so re-read it from the cached text. Give every claim a voice: Ibn Isḥāq, or Ibn Hishām ("qāla Ibn Hishām"). Attach Ibn Hishām's poetry doubts («وأكثر أهل العلم بالشعر ينكر…», 14 places) as a qualifier on the claims of that poem.
5. **Offices (F12).** Qayṣar, Kisrā, al-Najāshī and similar titles become offices, held by named persons where the text names them.
6. **Count checks (F2).** `ingest/count_checks.py`: each total the text states (Badr 314 with those given a share; Second ʿAqaba 73 men and 2 women; First ʿAqaba 12; Uḥud 65 Muslim and 22 Quraysh dead; Abyssinia 83 men "if ʿAmmār is among them"; Badr captives counted 43, Quraysh slain counted 50) is compared with the graph. A mismatch becomes a review-queue item. Quote each total's span. Never use a modern figure.
7. **Audit sample (F4).** `ingest/audit_sample.py` writes a seeded random sample of about 400 claims, stratified by predicate, as review-tool batches for the editor. The handover reports how to compute the published rate.
8. **Small fixes.** Khadīja "father of" Fāṭima becomes `rel_mother_of`, listed in a new `docs/CHANGELOG-data.md` (G6). Clear the 32 bookkeeping needs-review flags and turn the 12 groups into "real tribe or group?" questions (P9; `build_queue.py --list-excluded`). Move the al-Thurayya rows from external-ids.csv into a credited CC BY-SA file, and update LICENSING.md (S6).

## 11b — site (branch `slice-11b-site`, after 11a)
- Reader pages, search, thread, Observatory and Ask over about 7,900 people. The Prophet's ﷺ page is one long page loaded in parts (H3): the first part within budget, the rest fetched as the reader scrolls, and complete without JavaScript through linked part pages.
- Redirects for every retired ID (G5). Search ranks within the budget (split search.json by first letter if needed). Thread.json is split past about 200 KB (X1).
- Connect skips ancestors beyond three generations by default and says "same clan" (F13).
- The background layer (F11) is labelled and is kept out of learning paths.

## Done when
- 11a: one graph that conforms, with timings; merge proposals, side claims, formulas, voices, offices, count checks and the audit sample all committed and reproducible; handover `docs/handover/slice-11a.md` (≤60 lines).
- 11b: every page passes the budget and HTML checks with the joined graph; `scripts/check_all.sh` passes; handover `docs/handover/slice-11b.md`.

## Rules
AI never asserts. Never upgrade a status. Never invent names, dates, totals or IDs. Every quote is an exact substring of the cached text. No model names or IDs in any repo file. The cached text stays gitignored (licence: S1). Commit messages end with the attribution lines given in the session.
