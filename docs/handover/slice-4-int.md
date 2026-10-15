# Slice 4 integration: Ibn Hishām ingestion on top of the slice 3b stack

Branch `slice-4-int`: `slice-4-ingest` rebased onto `slice-3b`, then onto main after the Arabic interface (#18) merged (one conflict, in `site/render.py` `claim_li`: kept both sides, so a text object is shown in its own language inside Arabic pages too). `bash scripts/check_all.sh` passes every step. Statuses, confidences and canonical IDs are untouched; the cached text is not committed.

**What changed, and why**
1. `ontology/tools/identity_audit.py`: `FILES` knows `ontology/corpus/ibn-hisham.ttl`. The 79 existing `identity.csv` rows the file references got `;ibn-hisham` appended to `source_files` (nothing else on those rows changed).
2. `site/observatory/tests`: the observatory merges a narrator pair that recurs across chains into one link (one claim per chain). The test now counts distinct pairs, checks the links are exactly those pairs, and checks no claim is lost (links carry as many claims as chain links). The behaviour was right.
3. `ask/`:
   - `ask/golden/questions.jsonl`: rows for g01, g02, g04, g07, g10, g11, g13, g15, g28, g41, the `absent` list of g01, the candidates of g19 (4 people named Fāṭima/Fatimah now) and `about_n` of g33 (20) were recomputed straight from `build/graph.ttl` with rdflib, without the ask engine (the same rules as ask/DSL.md). The same method reproduced the unchanged cases (g03, g05, g08, g09, g14, g16-g18, g29, g37) before I trusted it. Spot-checked by hand against the claims and glosses (e.g. Abū Kabsha at Badr, Suraqa at the Hijra). Every line is still "pending scholar check".
   - Matcher: two words with the same consonant skeleton of 3 or more letters (Siffin, ʿUsfān, Ṣafwān all s-f-n) now count as one name only if they are at most `sound_max_edits` (2, in `rules.json`) letters apart. Shorter keys (Mecca/Makkah, Ayesha/ʿĀʾisha) are unchanged. "Who was at Siffin?" is `not_found` again. Same edit in `ask/static/ask.js`; parity test passes.
   - New tie-break: among entries that match equally only by spelling, the nearest spelling wins ("Ayesha" is ʿĀʾisha, not ʿAyyāsh); equals are still put back to the visitor. Without it s10 became ambiguous.
   - Tests: `test_a_sound_alike_is_not_a_spelling_of_another_name`; the Zayd test no longer hard-codes 2 options (there are three people named Zayd now); more parity questions.
4. `site/model.py`, `site/render.py`: an assertion whose object is a text (`rel_dated`) keeps it in `Claim.literal`, is filed under no entity, and is shown as written, in its language (`<span class="lit" lang="ar" dir="rtl">`). The 11 rdflib "not a valid URI" warnings are gone. Test: `test_a_text_as_object_is_shown_as_written_and_raises_no_warning`.
5. `LICENSING.md`: a paragraph on `ibn-hisham.ttl` (pointers, names, ascriptions, short age/date expressions; OpenITI CC BY-NC-SA 4.0 text not redistributed; credit OpenITI and the edition).

**A failure the ingestion's handover did not see: the page budget.** On this stack the Prophet's page was 345,749 bytes (limit 300,000), and after the Arabic interface (slice 9) its Arabic twin was 327,731. Two causes, two fixes:
- Every person page loads `thread.json` (176 KB), and 70 KB of it was the machine-written glosses of the new claims. `site/thread.py` now leaves out a claim's comment longer than 120 characters (`MAX_ROLE_CHARS`); the claim's page still shows it in full. Test: `test_long_comments_stay_on_the_pages_not_in_the_thread`.
- The passage citation shown beside each claim was about 330 characters, and the Prophet's page carries hundreds. `ingest/ibn_hisham.py` now writes the short form: `Ibn Hishām, al-Sīra al-Nabawiyya (al-Saqqā et al. ed., Cairo 1375/1955; provisional), vol. 1, pp. 494–496; OpenITI ms310–ms311, lines 8600–8638`. The full edition, OpenITI version, checksum and character offsets stay on the Edition, Witness and selector of each passage. `ibn-hisham.ttl` was rebuilt: only the 100-odd citation lines changed.

**For the maintainer**
- Confirm the LICENSING.md wording and that quoting names and short age/date expressions from the OpenITI text is acceptable (open point of slice 4).
- The budget margin is small: the Prophet's Arabic page is 294,267 of 300,000 bytes (English 257,699).  The next large ingestion will need a structural fix (split a very large page); the two cuts above are the stopgap.
- The thread no longer shows the AI gloss for Ibn Hishām claims; it shows relation, status and source, and links to the page.
- The ask golden set is still what the graph records, not what is true; it needs the scholar check.
- Everything in slice 4's own "left for a scholar" list still stands.
