# Moments layer brief — what happened, in order, as reviewable claims, and scenes built from them

Context: README "Standing rules"; lab/beyond-the-graph ("What it exposed", N2, architecture "Truth"); ontology/marsad.ttl, shapes.ttl, relations.ttl; docs/handover/slice-11a.md (merge proposals); docs/handover/maintainer-answers-3.md (F3, F5, F7, P5); lab/phase-a-plan/PLAN.md (experiment 6, critical path). Do not read chat history; this file is the brief. Statuses stay `proposed`.

## Build
1. **Moment.** Add `mrs:Moment`: agents, act, place, sequence within its section, time window (four-corner, as the model requires), and the passage span it rests on (exact substring of the cached text). Shape it in shapes.ttl; add one example that conforms.
2. **Trial (experiment 6).** Extract moments for the 28 Hijrah sections the prototype uses. Section 680 (the night of leaving) must come from the text, not from the AI-written heading. Write `ontology/corpus/moments-hijrah-trial.ttl` and a run log. Export a review batch so one scholar can review it, timed.
3. **Decision.** ≥ 80% accepted: run the full pass. 60–80%: full pass plus an editor pass. < 60%: an editor writes moments from each section, then review. Record the rate and minutes per moment in the handover.
4. **Scene.** Add `mrs:Scene`: place, time window, actors, moments, claims, camera, sound, questions, approvals. A scene is published only if every field resolves to claims. Hand-written text is limited to titles, camera and questions, and questions assert nothing.
5. **Packs.** `ontology/tools/build_scene_packs.py` compiles JSON scene packs and question banks. Every answer and every distractor resolves to a claim; a validator rejects any name, number or date not inside a shown claim.
6. **Cast.** Apply the editor's decisions on Hijrah-cast merge proposals (e.g. ʿAbd Allāh b. Urayqiṭ / b. Arqaṭ) through identity.csv; old addresses redirect.

## Done when
`build_graph.py` conforms with moments and scenes; about 25–30 Hijrah scenes across 10 chapters; scene packs and question banks built in CI by a new step in `scripts/check_all.sh`; tests for the validator. Handover `docs/handover/moments-layer.md` (≤60 lines) with the acceptance rate and timings.

## Rules
AI never asserts. Never upgrade a status. Never invent names, dates or IDs. Every quote is an exact substring of the cached text, which stays gitignored. No model names or IDs in any repo file.
