# Circle mode: the Majlis Sheet Builder

A prototype for teachers, halaqa leaders and parents. The research we read says AI tutors mostly fail on
engagement, tools that support a teacher work, and Sefaria's user-made source sheets are its most-used
teaching artefact. So this mode makes no tutor: it helps an adult build a sheet for a circle.

    python3 lab/circle-mode/build.py      # writes index.html (about 0.8 MB, no external requests)

`build.py` reads the full-book Ibn Hishām claims, their passages and the citations in
`ontology/corpus/ibn-hisham-full.ttl`, drops the bare lineage claims (father, mother, ancestor, sibling,
uncle, cousin), and inlines the remaining claims as compact JSON into `template.html`.

## What the page does
- **Search** ignores accents, ʿayn/hamza marks and Arabic harakat and alef/tāʾ marbūṭa forms (the claims are
  in transliteration today, so Arabic matching only matters once Arabic labels arrive). Filter by section or person.
- **Sheet**: add claims, reorder them, remove them, and add **questions** or **teacher's notes**. There is no
  free field for facts: every statement about the past is a claim's gloss with its citation. Notes print as
  "Teacher's note (not from the source)".
- **Disagreements**: in one section, finds claims with the same subject and predicate but different objects
  (for "who lodged him" style predicates, also same predicate and object with different subjects). With no
  section chosen, it lists the sections that have candidates.
- **Project** (arrow keys step through items, Esc closes) and **Print** use the same clean sheet view.
- **Save/open** sheets in this browser (localStorage, wrapped in try/catch) and **share** a sheet as a compact
  JSON string; claims missing from a newer build are skipped with a message.
- Preloaded example: "The two reports of the lodging at Qubāʾ" (S0698, S0699).
- The footer says the claims are AI-extracted, proposed and unreviewed.

Tested headless with Playwright: no page errors, no external requests (`screenshot.png`, `screenshot-projector.png`).

## Next step: live guess on the projector
The teacher projects a sheet; before a claim is revealed, the room guesses (who lodged him? which place?).
- One **Cloudflare Durable Object per session**, keyed by a short room code shown on the projector with a QR.
- Students open the code on a phone and join over a **WebSocket**. No accounts, no names required: a random
  per-tab id, optional nickname, nothing stored after the session ends (DO storage cleared on close).
- The projector (teacher) sends `open {item, choices}`; choices come only from claims, with distractors drawn
  from the same predicate elsewhere in the book, as in Hijrah Night. Phones send `guess {choice}`.
- The DO keeps tallies and broadcasts counts only; on `reveal` the projector shows the claim, its citation
  and the bar of guesses. For a disagreement item, reveal shows both reports, so "both" is the right answer.
- Teacher controls: lock, reveal, next, end. Rate-limit one guess per id per item; drop sockets on end.
- No free-text answers from students in v1, so there is nothing to moderate on a shared screen.
