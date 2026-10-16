# Full-book pass over Ibn Hishām's Sīra: handover

**What.** Slice 4 extracted 404 claims from 106 passages, about 3% of the text. This pass covers **every section** of the same OpenITI text: `0213IbnHisham.SiraNabawiyya.Shamela0023833-ara1`, at the same pinned commit and checksum, with the same provisional edition (al-Saqqā et al., Cairo 1375/1955, E33). It also adds a page, `sira-network/index.html`, that draws the whole network.

**Numbers.**
- **1,788** sections carry claims, out of the text's 2,165 sections. Each such section is one Passage and one Report.
- **15,065** proposed claims.
- **7,879** new entities: 7,547 people, 189 places and 143 events, each with an identity.csv row marked `needs-review`.
- **349** existing entities are referenced.
- 439 entities are named but have no claim, for example a person a poem only addresses. They are listed anyway, because the aim was every named person.
- Claims by predicate:
  - kinship and lineage: father_of 9,231, sibling_of 304, mother_of 277
  - transmission and participation: narrated_from 1,250, participated_in 1,236, died_during 411, migrated_to 241
  - **killed 228**
  - the rest (visited, spouse_of, led, present_at, appointed, mawla_of ...) are fewer than 200 each.
- Qualifiers: text_alternative 354, hedged 122, editorial_brackets 119, share_not_present 8.

**How it was made.**
- `ingest/sira_full.py chunks` cuts the cached text into sections (the text between two of the edition's `###` headings) and 96 chunks of about 15,000 characters each.
- An AI pass worked through each chunk following **`ingest/full-pass-instructions.md`**. That file is committed: it is the prompt, the predicate list and the red lines.
- Each chunk's output quotes the Arabic span for every claim. `verify N` refuses any quote that is not an exact substring of its section. All 96 chunks verify.
- `assemble` turns every quote into offsets and a checksum, mints IDs (mint_id.py's rule) and writes `ingest/claims/ibn-hisham-full*.jsonl` and identity.csv rows.
- `ingest/ibn_hisham.py build full` writes the Turtle. A re-run is byte for byte the same.
- The chunk files and the extraction output quote the text, so they stay in the gitignored `ingest/cache/full/`. Nothing committed contains running text. Glosses that quoted Arabic were replaced with an English sentence generated from the claim itself.

**Where.**
- `ontology/corpus-full/ibn-hisham-full.ttl` (23 MB, ~500,000 triples). It is **deliberately outside `ontology/corpus/`**, so `build_graph.py`, the site and the review queue are unchanged by it.
- `identity_audit.py` knows the file (`ibn-hisham-full`).
- `relations.ttl` gains one type, **`rel_killed`**. The maghāzī lists of who killed whom had no fitting predicate.

**People across chunks: read this before trusting a node.** Each chunk was read on its own, so one person appears in many chunks. They are matched (`build_groups`) **only on name and father line**:
- Two records are one person when their name, carried up the father line the chunk's own claims state (to three generations), is the same.
- A bare single name (Kaʿb, ʿAmr) is **never** merged across chunks.
- A kunya alone (Abū Sufyān, Abū ʿUbayda) **is** merged. That can join two different people (Abū Sufyān b. Ḥarb and Abū Sufyān b. al-Ḥārith), so check kunya-only nodes.
- 327 identity names carry a "(2)" or "(note)" suffix because two groups ended up with the same English name.

Expect duplicates (one person under several IDs) far more often than wrong merges. A resolution pass, by a person or a reviewed AI pass, is the next step. `sira_full.py groups` prints the largest groups.

**Known errors.**
- A seeded sample of 24 claims had 1 wrong: al-Aswad b. al-Muṭṭalib was given as the father of al-Ḥārith b. Zamʿa, when the father is Zamʿa. It was an extraction error, not a merge error.
- `sira_full.py suspects` checks every father_of claim whose span reads "A b. B" against the two names recorded. It lists **166** for review in `ingest/claims/ibn-hisham-full-suspects.tsv`. Most are names the text itself alternates, like Shayba for ʿAbd al-Muṭṭalib or ʿAmr for Hāshim, but the error above is among them. **Check these first.**
- Judgement calls reported by the pass that a scholar should see:
  - participation inferred from the section's list context (the slain at Uḥud, the emigrants to Abyssinia, the Badr captives) when the sentence naming the event is in a neighbouring section;
  - several claims that share one quote (the Prophet's children with Khadīja, the lodgings at Qubāʾ);
  - royal titles (Qayṣar, Kisrā, al-Najāshī) recorded as persons;
  - a few `existing` links made on a bare kunya or a verse.

**The page.** `sira-network/index.html` (1.7 MB, self-contained, no external request, works at phone width) is built by `sira-network/build.py` from committed files only.
- Search any name, in English or Arabic. The entry's relations are drawn around it, coloured by kind, with a table of every statement and its citation (volume, page, OpenITI milestone, lines).
- It says on every view that the data is AI-extracted, proposed and unreviewed.
- Lists are alphabetical: no metric, no ranking.
- It is a prototype island like `generation-1/`: `check_all.sh` builds it and checks the committed copy is current.

**Checks.**
- `ingest/ibn_hisham.py check all` passes. The slice 4 file is unchanged.
- `identity_audit.py --check` covers the new file.
- `validate.py ontology/corpus-full/ibn-hisham-full.ttl` **conforms**, with no violations, run on 16 October 2026; it took 30 minutes. Because of that, `check_all.sh` skips it unless `CHECK_FULL_SIRA=1`. The same builder writes `ibn-hisham.ttl`, which is validated on every run.
- `scripts/check_all.sh` passes: 44 steps passed, and the one skipped step is the slow validation above.

**For the maintainer.**
1. The same licence question as slice 4 applies: names and short date expressions only are committed.
2. Decide when (if ever) this layer joins `ontology/corpus/`. That would put about 7,500 people into the site, the observatory, search and the review queue, all of which have page budgets.
3. Run a resolution pass on duplicate people before review.
4. The older slice 4 sample (404 claims) is kept as it is. It overlaps this pass in about 100 sections, and its chains of transmission are modelled in more detail.
