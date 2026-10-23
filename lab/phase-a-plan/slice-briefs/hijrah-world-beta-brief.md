# Hijrah World beta brief — from the prototype to a world people can use

Context: README "Standing rules"; lab/beyond-the-graph (N1, architecture, design grammar); lab/hijrah-night (the prototype and its build); docs/handover/maintainer-answers-3.md (H4, X1, G1, T4, E1); lab/phase-a-plan/PLAN.md (Gate A2). Do not read chat history; this file is the brief. Build on the scene packs of `moments-layer` once they land; until then, on the prototype's CHAPTERS.

## Build
1. **Port.** `site/world/hijrah/` built by `site/world/build_world.py` from scene packs. Every string is an i18n key; no external requests; nothing a learner reads about the past is typed by hand. The build refuses a scene whose text does not resolve to claims, as the prototype's build does.
2. **Tiers.** Tier 0: text, works with JavaScript off. Tier 1: 2.5D map. Tier 2: 3D terrain (WebGL2; WebGPU only if ahead). Chosen from device memory, a GPU probe and measured frame rate; the learner can override.
3. **Terrain.** Terrain-RGB tiles for the Ḥijāz (Copernicus GLO-30 or the AWS terrain tiles), loaded by view, credited in LICENSING.md. First load under 3 MB.
4. **Design grammar.** The Prophet ﷺ is the light at the centre, never a node or figure (H4). People are lights, brightness by generation (T4). Opponents recorded by claims are dark stones; a stone turns to a star only at a recorded acceptance of Islam (X1). No recorded side means neutral, never guessed. Unlocated stops are dashed; no road between stops. Chains rise toward the book in Study depth.
5. **Depths (G1).** Discover shows no review language and keeps each claim's source line (work and page). Study and Research show status.
6. **Performance harness.** Per-chapter frame times, memory and first-load size logged from the three test phones to `site/world/perf-log.csv`; a size budget check in CI.

## Done when
On all three test phones (≤ $150): median 30 fps per chapter, worst chapter under 150 MB, first load under 3 MB. A Playwright check passes at 390×844 and on desktop, JS on and off, with no external requests; the step is in `scripts/check_all.sh`. Pilot build tagged `world-beta-2` after scholar review. Handover `docs/handover/hijrah-world-beta.md` (≤60 lines) with screenshots of each tier and the perf table.

## Rules
No pixel without provenance; no depiction (no figures, no generated scenes, no reconstructions); AI never asserts; never hard-code entity IDs; no model names or IDs in the repo.
