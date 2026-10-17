# Hiring — Phase A

Two roles from lab/beyond-the-graph "Team and cost" (round 3, M2). Ads go out in W0; people start in W3 (PLAN.md, critical path). Remote; non-profit rates; donation-funded, so every figure is published by category (M3).

## 3D and web engineer (full-time; full plan $70k–110k a year, lean $50k–70k)
**The work.** Turn the Hijrah Night prototype (about 1,000 lines, three.js over real terrain) into a world that runs at 30 fps on a $150 Android phone, falls back to a 2.5D map and to plain text without losing anything a learner must read, and is built only from sourced claims. You own the renderer, the device tiers, terrain tiles, the performance harness, projector mode and the personal sky.

**You have.** Shipped three.js or similar WebGL work in production, measured on real low-end devices; terrain or map tiles (MapLibre, PMTiles, terrain-RGB); static-site thinking (no runtime server, budgets in CI); accessibility and progressive enhancement; comfort with a build that refuses content it cannot trace to a source. Arabic or RTL experience is a plus; WebGPU is a plus.

**You will not.** Draw people, buildings or scenes the sources do not give. Add tracking or accounts for learners.

**Portfolio test (paid, about 6 hours, take-home).**
1. Given a terrain-RGB tile set for a 200 × 200 km area and a JSON of 12 points (7 located with grades, 5 unlocated, in order), render a night scene: one warm central light that is never drawn as a marker, located points as small lights, unlocated stops as dashed placeholders with no line between any stops.
2. Add a tier switch: text list (works with JS off), 2.5D map, 3D. Choose the tier automatically from device memory and a measured frame rate.
3. Report median fps and peak memory on the cheapest Android phone you can get (or Chrome's low-end CPU and network throttling, stated), and first-load size.
**Scored on:** frame time and memory on the low-end target (30%); honesty of the encoding: no road drawn, absence visible, central light not a node (25%); fallback quality, JS off and at 390 px (20%); code clarity and a short README with the measurements (25%).

## Product designer (0.5; full plan $30k–45k a year, lean $12k–20k contract)
**The work.** Give al-Marṣad a visual and sonic identity for a sacred history presented **without depiction**: a night world of light, lights, dark stones, dashed absence and chains of narration rising toward the book. You design the world's UI, the three depths (Discover, Study, Research), question and recall cards, the sky, projector mode, Arabic and Latin typography together, and the sound policy note the scholars decide on.

**You have.** A portfolio of restrained, typographic, information-rich work; Arabic typography or bilingual layouts; design for dim screens and small phones; experience working with subject experts who sign off your work. Islamic art, calligraphy, cartography or museum interpretation is a plus.

**You will not.** Draw figures or faces, silhouettes, generated reconstructions, or anything that could be read as a portrait of the Prophet ﷺ or the Companions. Use points, badges, streaks or leaderboards.

**Portfolio test (paid, about 8 hours).**
1. One phone screen at 390 × 844 at night: the cave at Thawr, three people present as lights, the Prophet ﷺ as the light, one opponent as a dark stone, one unlocated place, and one claim with its source line (work, volume and page) readable on a dim, cheap screen.
2. The same screen in Arabic (RTL), with names as written in Ibn Hishām and Gregorian dates first (L1, L2).
3. A guess-first question card and its reveal, where the wrong answer is explained by a sourced claim, with no points.
4. Half a page on how your choices avoid depiction and avoid ranking people.
**Scored on:** aniconic clarity, nothing figurative and nothing a scholar would need to remove (30%); legibility and contrast at night on a low-end screen, both scripts (25%); provenance visible without clutter (20%); restraint and craft (25%). Two scholars see the shortlisted entries before the offer.

## Process
W0 post (both); W1–W2 tests and interviews, scored on the rubric by the maintainer and one reviewer; W3 offers and start. If no engineer by W3, builder sessions carry the port and the cut list starts at item 1 (PLAN.md).
