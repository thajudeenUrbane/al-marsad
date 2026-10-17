#!/usr/bin/env python3
"""
Build the scholars' review queue (slice 3a). Reads the graph; changes nothing in it.

    .venv/bin/python review/build_queue.py                      # write review/dist/queue.json
    .venv/bin/python review/build_queue.py --list-excluded      # also print the identity rows left out, and why
    .venv/bin/python review/build_queue.py --identity-confidence needs-review,probable

Claims queue: every Assertion whose status is `proposed`, one review unit per claim,
each claim in exactly one batch, batched in this order:
  1. by story: claims derived from a narrative passage (the 50 Stories), one batch per
     story, in the work's own order;
  2. by person: the rest, under the person the claim is about (its subject if that is a
     person, else its object), persons sorted by name;
  3. by source file: whatever is left (claims about events and places only).
A batch longer than --max-batch units is split into parts. Each unit carries the claim
in plain words, its basis verbatim (the nonReportBasis text, or the Report's matn) with
the source passages (in the top-level "passages" map, Arabic beside English where the
graph has it), its current status, its scope facets (source file, topic, period), whether
accepting it needs a cited source, and any earlier decisions from reviews.ttl.

Identity queue: the rows of ontology/corpus/identity.csv whose confidence is in
--identity-confidence (default: needs-review), as "same person?" questions
(mrs:IdentityAssertion candidates). Rows whose flag is only ID bookkeeping from
slice 1a (the ID collision or hash IDs that slice 1d re-minted) are left out, so no
scholar time goes on them, and so are the rows the full-book pass created (new, not
known duplicates: those go through merge proposals and an editor, maintainer F3);
--list-excluded prints them for the maintainer.

Count checks (slice 11a): where a list in Ibn Hishām's text gives a total and the graph
holds a different number of people in it (ingest/claims/ibn-hisham-full-counts.json),
the mismatch is listed under "count_checks" for an editor: a missed name, a duplicate or
a person in the wrong list. They are questions, not claims, so they carry no decision.

The output is deterministic (no timestamps). Format: docs/handover/slice-3a.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

DEFAULT_OUT = c.ROOT / "review" / "dist" / "queue.json"
COUNTS = c.ROOT / "ingest" / "claims" / "ibn-hisham-full-counts.json"


def count_checks() -> list:
    if not COUNTS.exists():
        return []
    rows = json.loads(COUNTS.read_text(encoding="utf-8"))["checks"]
    return [{k: r[k] for k in ("key", "what", "stated", "found", "found_ibn_ishaq_voice",
                               "found_ibn_hisham_voice", "found_no_voice")} for r in rows if not r["matches"]]


def claim_unit(tree: c.Tree, a, earlier: dict) -> dict:
    g = tree.graph
    subj, obj = g.value(a, c.MRS.assertionSubject), g.value(a, c.MRS.assertionObject)
    pred = g.value(a, c.MRS.predicate)
    pred_label = tree.label(pred, c.SKOS.prefLabel) or c.curie(pred)
    s_name, o_name = tree.name(subj)[0], tree.name(obj)[0]
    if (obj, c.RDF.type, c.MRS.Event) in g:
        o_name = f"“{o_name}”"
    quals = tree.qualifiers(a)
    text = f"{s_name} {pred_label} {o_name}" + (f" ({'; '.join(quals)})" if quals else "")
    period = tree.period_of(a)
    return {
        "id": c.curie(a),
        "kind": "claim",
        "claim": text,
        "subject": tree.entity_json(subj),
        "predicate": {"id": c.curie(pred), "label": pred_label},
        "object": tree.entity_json(obj),
        "qualifiers": quals,
        "source_wording": tree.label(a, c.RDFS.comment),
        "basis": tree.basis_json(a),
        "status": tree.status(a),
        "file": tree.source_of(a) + ".ttl",
        "topic": tree.topic_of(a),
        "period": list(period) if period else None,
        "ai_generated_basis": tree.ai_basis(a),
        "citation_required_to_accept": not tree.has_real_source(a),
        "earlier_decisions": [d.as_json() for d in earlier.get(a, [])],
    }


def split(batch: dict, units: list, size: int) -> list[dict]:
    parts = [units[i:i + size] for i in range(0, len(units), size)] or [[]]
    out = []
    for n, chunk in enumerate(parts, start=1):
        b = dict(batch, part=n, parts=len(parts), units=chunk)
        if len(parts) > 1:
            b["batch"] = f"{batch['batch']}-p{n}"
        out.append(b)
    return out


def claim_batches(tree: c.Tree, size: int) -> tuple[list, dict]:
    g = tree.graph
    earlier = tree.decisions_by_target()
    proposed = [a for a in tree.assertions() if tree.status(a) == "proposed"]
    stories, persons, files, passages = {}, {}, {}, {}
    for a in proposed:
        story = tree.story_of(a)
        if story is not None:
            stories.setdefault(story, []).append(a)
            continue
        who = next((n for n in (g.value(a, c.MRS.assertionSubject), g.value(a, c.MRS.assertionObject))
                    if (n, c.RDF.type, c.MRS.Person) in g), None)
        if who is not None:
            persons.setdefault(who, []).append(a)
        else:
            files.setdefault(tree.source_of(a), []).append(a)

    def units(claims):
        out = [claim_unit(tree, a, earlier) for a in claims]
        for a in claims:
            for p in tree.basis_passages(a):
                passages.setdefault(c.curie(p), tree.passage_json(p))
        return sorted(out, key=lambda u: (c.fold(u["subject"]["name"]), c.fold(u["object"]["name"]), u["id"]))

    batches = []

    def story_key(p):
        parent = g.value(p, c.DCTERMS.isPartOf)
        works = sorted(tree.works_of(p), key=str)
        return (str(works[0]) if works else "", tree.notation(parent) or 0, tree.notation(p) or 0, str(p))

    used = set()
    for p in sorted(stories, key=story_key):
        n = tree.notation(p)
        bid = f"story-{n:02d}" if n is not None and f"story-{n:02d}" not in used else f"story-{c.curie(p).split(':')[-1]}"
        used.add(bid)
        title = tree.label(p) or c.curie(p)
        works = sorted(tree.works_of(p), key=str)
        passages.setdefault(c.curie(p), tree.passage_json(p))
        batches += split({"batch": bid, "kind": "story", "title": title, "story_number": n,
                          "work": tree.label(works[0]) if works else None, "passage": c.curie(p)},
                         units(stories[p]), size)
    for who in sorted(persons, key=lambda w: (c.fold(tree.name(w)[0]), str(w))):
        en, ar = tree.name(who)
        batches += split({"batch": f"person-{c.curie(who).split(':')[-1]}", "kind": "person", "title": en,
                          "title_ar": ar or None, "person": c.curie(who)}, units(persons[who]), size)
    for stem in sorted(files):
        batches += split({"batch": f"file-{stem}", "kind": "file", "title": f"{stem}.ttl"}, units(files[stem]), size)
    return batches, passages


def identity_batches(tree: c.Tree, levels: set, size: int) -> tuple[list, list]:
    earlier = tree.decisions_by_target()
    units, excluded = [], []
    for row in tree.identity:
        if row.get("source_files", "") == "ibn-hisham-full" and row["confidence"] in levels:
            # a person, place or event first named by the full-book pass: needs-review because it is new,
            # not because a "same as?" question is known; duplicates go to an editor through merge proposals
            # (ontology/tools/propose_merges.py, maintainer F3), and only the hard cases reach scholars
            excluded.append({"id": row["canonical_id"], "kind": row["kind"], "name": row["preferred_name_en"],
                             "confidence": row["confidence"], "queued_as": None,
                             "reasons": ["new from the full-book pass: duplicates go through merge proposals"]})
            continue
        queued_as = c.queued_confidence(row)
        flags = c.note_flags(row.get("note", ""))
        if queued_as not in levels:
            if row["confidence"] in levels:
                excluded.append({"id": row["canonical_id"], "kind": row["kind"], "name": row["preferred_name_en"],
                                 "confidence": row["confidence"], "queued_as": queued_as,
                                 "reasons": sorted({why for _, _, why in flags if why})})
            continue
        iri = c.expand(row["canonical_id"])
        units.append({
            "id": row["canonical_id"],
            "kind": "identity",
            "entity": row["kind"],
            "question": "real_group" if c.REAL_GROUP_NOTE in row.get("note", "") else "same_as",
            "name": row["preferred_name_en"],
            "name_ar": row.get("name_ar") or None,
            "variant_ids": [v for v in row.get("variant_ids", "").split(";") if v],
            "stories50_names": [v for v in row.get("stories50_names", "").split(";") if v],
            "files": [v for v in row.get("source_files", "").split(";") if v],
            "confidence": row["confidence"],
            "queued_as": queued_as,
            "note_parts": [part for part, _, _ in flags],
            "earlier_decisions": [d.as_json() for d in earlier.get(iri, [])],
        })
    units.sort(key=lambda u: (u["entity"], c.fold(u["name"]), u["id"]))
    batches = split({"batch": "identity", "kind": "identity", "title": "Identity questions"}, units, size) if units else []
    return batches, excluded


def build(tree: c.Tree, levels: set, size: int) -> dict:
    claims, passages = claim_batches(tree, size)
    identity, excluded = identity_batches(tree, levels, size)
    t = tree.default_tradition()
    counts = count_checks()
    count = {k: sum(1 for b in claims if b["kind"] == k) for k in ("story", "person", "file")}
    return {
        "format": "marsad-review-queue",
        "version": 1,
        "fingerprint": tree.fingerprint(),
        "checks": list(c.CHECKS),
        "decisions": list(c.OUTCOMES),
        "tradition": {"id": c.curie(t), "label": tree.label(t, c.SKOS.prefLabel), "declared_default": True},
        "summary": {
            "claims": sum(len(b["units"]) for b in claims),
            "claim_batches": count,
            "identity_units": sum(len(b["units"]) for b in identity),
            "identity_excluded": len(excluded),
            "identity_confidence": sorted(levels),
            "count_checks": len(counts),
        },
        "claims": claims,
        "identity": identity,
        "identity_excluded": excluded,
        "count_checks": counts,
        "passages": dict(sorted(passages.items())),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ontology", type=Path, default=c.ONTOLOGY, help="ontology directory (default: the repository's)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output JSON (default {DEFAULT_OUT.relative_to(c.ROOT)})")
    ap.add_argument("--max-batch", type=int, default=50, help="split batches longer than this (default 50)")
    ap.add_argument("--identity-confidence", default="needs-review",
                    help="identity.csv confidence values to queue, comma-separated (default needs-review)")
    ap.add_argument("--list-excluded", action="store_true", help="print the identity rows left out and why")
    args = ap.parse_args(argv)
    tree = c.Tree(args.ontology)
    restorable, problems = c.drift(tree)
    if restorable or problems:
        print(f"error: {len(restorable) + len(problems)} claim status(es) disagree with reviews.ttl; a queue built now "
              "could send decided claims back to the scholars. Run review/import_decisions.py --check, then --reapply.")
        return 1
    queue = build(tree, {v.strip() for v in args.identity_confidence.split(",") if v.strip()}, max(1, args.max_batch))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(queue, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    s = queue["summary"]
    b = s["claim_batches"]
    print(f"claims: {s['claims']} proposed, in {sum(b.values())} batches "
          f"({b['story']} story, {b['person']} person, {b['file']} file)")
    print(f"identity: {s['identity_units']} question(s); {s['identity_excluded']} row(s) left out "
          f"(slice-1a ID bookkeeping, or new from the full-book pass)")
    if s["count_checks"]:
        print(f"count checks: {s['count_checks']} list(s) whose count differs from the total the text gives (for an editor)")
    if args.list_excluded:
        for row in queue["identity_excluded"]:
            print(f"  {row['id']}  {row['name']}  -- {'; '.join(row['reasons'])}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
