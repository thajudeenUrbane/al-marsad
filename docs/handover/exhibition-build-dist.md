# Exhibition build: dist regenerated offline

Date 2026-10-24. Branch `claude/exhibition-build-7a92ab`. `expeditions/dist/` now matches the edited `expeditions/compile/compile.py`, `expeditions/app/app.js` and `expeditions/defs/expeditions.json` (the edits, and the prediction this note checks, are in `exhibition-build-expeditions.md`). Nothing is committed, pushed or stashed: the changes are in the working tree.

Offline regeneration of the touched parts only. **Owed after the meeting:** a full rebuild with the five downloads (the terrain tiles, the OpenITI text of Ibn Hishām, the HYG star CSV, the astronomy-engine package and Pillow), following the steps in `exhibition-build-expeditions.md`. The maintainer chose the offline regeneration for today ("do it fast and go ahead", 2026-10-24).

## What I ran

No network, no download, no pip install. The scripts lived in the session scratchpad, outside the repo; they are not kept. Python 3.15.0, Node v24.19.0, `python3 -B` throughout so no `.pyc` is written.

1. `load_compile.py` loads compile.py as a module with a small Pillow stub on the path (so no install is needed). Every function below is compile.py's own.
2. `regen_dist.py`, dry run first, then `--write`:
   - reads dist and checks that all 12 JSON files round-trip byte for byte through main()'s serialisation (`json.dumps(obj, ensure_ascii=False, separators=(",", ":"))`);
   - control: the new code on the data now on disk, against the pages now on disk. Only the people sentence differs, so the rest of compile.py agrees with what dist already held;
   - applies `honour()` to the same glosses main() passes through it (date-case claims and route-stage claims through `Graph.cite`, the shared-count names in `count_lists`, the `review_batch` items) and adds `note` and `note_class` right after `lists` in the three count cases that carry one in the defs (the way `count_case` does);
   - recomputes what is a pure function of the data in dist: `connections`, `questions`, the review counts and `data/index.json` (all equal what is on disk), and checks `publish.html` equals main()'s derivation from `app/index.html` (it does; never written);
   - renders `text/<slug>.html`, `text/index.html` and `channels/<slug>.txt` with `text_page`, `text_index` and `channel_pack`; writes only the files whose content changes; copies `app.js` (the one app file that differed).
3. `verify_dist.py` (read only), `check_corpus_glosses.py` (read only) and `chunk_counts.py` (read only, the counts below).
4. A second `regen_dist.py --write`: "WROTE 0 files and copied 0 app files". Checksums, mtimes and the diff stat were identical before and after.
5. Smoke test of the app: a copy of dist in the scratchpad, served on 127.0.0.1 by a short-lived Python server (it shuts itself down after five minutes; stopped by hand, no listener left). All 5 expeditions and 34 steps were opened in the browser pane. Done twice, same result. At every step the hash and the step label were what was asked for, nothing showed "Something did not load", and the page raised no errors. Badr "The 314" shows the attested note, Abyssinia and ʿAqaba show the schematic note, Uḥud shows none. The Badr people step reads "314 with the Prophet ﷺ, 131 on the other side, and 51 with no side recorded" with the filter labels "With the Prophet ﷺ", "On the other side" and "No side recorded". The home page reads "the Prophet's ﷺ life". No doubled sign, no "against him".

## Diff stat

`git diff --stat -- expeditions/dist`: 19 files changed, 24 insertions(+), 22 deletions(-). The files are single-line or minified, so the line counts are small; the counts that matter are below.

- `app.js` (8 lines: now identical to `app/app.js`).
- `channels/`: abyssinia, aqaba, badr, uhud.
- `data/`: abyssinia, aqaba, badr, hijrah, uhud; review-aqaba, review-badr, review-hijrah, review-uhud.
- `text/`: abyssinia, aqaba, badr, hijrah, uhud.

Byte-identical to HEAD (10 of the 29 tracked files): `app.css`, `index.html`, `memory.js`, `world.js`, `publish.html`, `channels/hijrah.txt`, `data/index.json`, `data/review-abyssinia.json`, `data/stars.json`, `text/index.html`. Nothing outside `expeditions/dist/` was written (scripts and the smoke-test copy are in the scratchpad), and `ingest/`, `ontology/`, compile.py, app.js and the defs were not touched.

## Against the prediction

| | predicted | found |
|---|---|---|
| text-page chunks changed | 22 | 22 (abyssinia 4, aqaba 4, hijrah 4, badr 6, uhud 4) |
| channel-pack chunks changed | 10 | 10 (abyssinia 2, aqaba 2, hijrah 0, badr 4, uhud 2) |
| glosses gaining " ﷺ" | "69 dist glosses plus the review-pack glosses" | 69 in all, see below |
| count cases gaining `note` and `note_class` | 3 (Badr, Abyssinia, ʿAqaba) | 3, key order `type, title, lists, note, note_class, groups, group_sum, twice, after_totals` |
| `dist/app.js` | equal to `app/app.js` | equal (`node --check` passes) |
| `publish.html`, `index.html`, CSS, other JS | unchanged | unchanged |

The one difference is in wording. The note read as "69 plus the review-pack glosses". The real count is 69 in all: 8 in `data/<slug>.json` (3 date-case claims, in hijrah, badr and uhud, and 5 shared-count names, all in badr) and 61 in the review packs (aqaba 4, hijrah 6, badr 24, uhud 27; abyssinia 0). Each of the 69 gained exactly one " ﷺ" (the sign after "the Prophet", "the Prophet's" or "the Prophet Muḥammad"), so 69 signs were added, none doubled, and `honour()` is a fixed point on all of them. The 22 text chunks include the people sentence (2 per page) and, for the three count pages, the case note.

## What was checked (all pass)

- All 12 JSON files parse and round-trip; `node --check expeditions/dist/app.js` exits 0; the five app files in dist equal those in `app/`.
- Field by field against `git show HEAD:`: the only differences in the data files are the 69 inserted signs and the three added `note` and `note_class` pairs. Nothing else moved, including key order.
- No doubled sign anywhere in dist, no sign beside the English or Arabic honorific words, no gloss still bare, no "against him" left.
- Text pages are well formed and equal compile.py's own rendering; the people-sentence numbers match the data (Badr 314, 131 and 51; Uḥud 70, 22 and 75; Abyssinia 0, 0 and 127; ʿAqaba 0, 0 and 77; Hijrah 0, 0 and 3).
- All 1,801 dist glosses equal their gloss in the corpus (`ingest/claims/ibn-hisham-full.jsonl`, read only) by claim id, so a real rebuild would give the same glosses after `honour()`.

## Caveats and flags

- This is not a rebuild. The sky and terrain data, `stars.json`, the review-pack membership and every other unchanged value were carried over from the files already in dist, because the inputs for a rebuild are not on this machine (see "Why dist was not rebuilt" in `exhibition-build-expeditions.md`). The rebuild steps listed there still stand. When it is done, `git diff --stat expeditions/dist` against this regeneration should show nothing; anything it does show is a difference between the carried-over values and the real inputs and is worth a look.
- No bug found in compile.py, app.js or the defs while doing this.
- `exhibition/build.py` reads only the title, people, sky and source of `dist/data/badr.json`; none of those changed.
- `ingest/__pycache__` and `expeditions/compile/__pycache__` exist. They are gitignored and came from the earlier dry runs; my runs wrote no bytecode. Left in place because `ingest/` is read only for this job.
