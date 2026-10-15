# Slice 1 summary (for the maintainer)

## What "one graph" now means
One command, `.venv/bin/python ontology/build_graph.py`, reads the ontology and all four corpus files (the Ghar Thawr example, generation-1, the 100 seed incidents and the 50 Stories) into a single graph, checks it against the shapes and fails if anything is invalid. The graph has 184 people, 12 groups, 22 places, 96 named events and about 550 claims.

Every person, place and event has exactly one ID, listed in `ontology/corpus/identity.csv`; the 50 Stories use only those IDs. Abu Bakr is one node: a single query returns his story links, incident links, kinship ties and event participations from all four sources (see docs/handover/slice-1c.md).

The 50 Stories are now data: 50 story events, the prose kept word for word, and 380 links from people and groups to stories, each with the doc's own role text. "(accepted Islam later)" is kept on the 24 links where the doc says it.

## What is still unverified
All of it. Every claim is `proposed` and every record `stub`; the 50 Stories doc says itself that it was written from general knowledge without access to the sources. The seed incidents have no passages attached and their dates are approximate. Nothing has been reviewed by a scholar, so nothing is "knowledge" yet.

## What needs a scholar or a decision
- Whether each story link is right, and what the people's real roles were; the role text is only what the doc says.
- Whether story events are the same events as the incident and Badr/Uhud events already in the graph. They are deliberately not merged.
- The 32 identity rows still marked needs-review (look-alike names, two people called ʿUrwa, ID collisions) and the 18 probable merges.
- Ghar Thawr is a "cave" in one file and a "route node" in another; the build keeps "cave" for now.
- Whether `participated in` is the right relation for people only "connected" to a story (narrators, relatives).
- No Arabic names yet for most people and places; none were invented.
