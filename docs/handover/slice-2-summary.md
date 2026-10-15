# Slice 2 summary, for the maintainer (15 October 2026)

## What a visitor can do now
- Open the home page and choose one of **three doors**: **Discover** (the 50 stories, story first), **Study** (events in time order, people and groups) or **Research** (sources, open questions, every record, the whole graph to download). Study and Research open each record's page at its evidence: the claims, each with its status and source. No account, no tracking.
- Read a plain page for every person (184), group (12), place (22), event (46) and story (50). Each says at the top how far it has been checked; every claim shows "Status: proposed" (or "not recorded"); Details holds the names as recorded, who recorded what, and the raw data.
- **Search** names in any spelling ("Abu Bakr", "abubakr", "أبو بكر"); without JavaScript the box lists every name A–Z.
- **Follow the thread** on a person's page: everything recorded for them in order, and anyone who shares a moment is one tap away; the thread moves on to them and the path stays on screen.
- Switch **Plain words** on to hide Arabic terms that already have English beside them, and to show a plain English wording where the glossary records one (4 terms so far). The choice stays on the device.
- From the home page's list of views: the Observatory, Timeline, Map and Learning paths (Life lines and Ask the graph appear when built); and the **earlier prototypes**, labelled as such.
- Everything works with JavaScript off, on a phone, without loading anything from another site.

## Weights (budget 300 KB per reader page)
325 reader pages. Heaviest: the Prophet's page with the thread, 157 KB; the search page 125 KB; Research 111 KB (each counting its CSS, scripts and data). Interactive views have their own 2 MB budget (the Observatory is 457 KB).

## Still unverified
- **Nothing is reviewed.** All 549 claims are proposed; all records are stubs or outlines. The 50 Stories were generated with AI and every story page says so.
- Arabic names exist for 6 places only; the Companion honorific never shows (no gender field); glossary: 7 definitions, 36 "definition needed".
- External IDs (Wikidata etc.) will show as "possible match, proposed, not reviewed" once slice 5's file lands.
- The deploy is ready but off until you add the Cloudflare secrets (docs/handover/slice-2c-ci.md).
