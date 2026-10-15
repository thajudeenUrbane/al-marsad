#!/usr/bin/env python3
"""
Import reviewers' decision files (slice 3a). The only way a claim's status moves.

    .venv/bin/python review/import_decisions.py                  # every *.json in review/inbox/
    .venv/bin/python review/import_decisions.py FILE.json ...    # these files
    .venv/bin/python review/import_decisions.py --dry-run ...    # check and report, write nothing
    .venv/bin/python review/import_decisions.py --check          # do corpus statuses agree with reviews.ttl? (exit 1 if not)
    .venv/bin/python review/import_decisions.py --reapply        # restore reviewed statuses after a corpus file was regenerated

Options: --roster PATH (default review/roster.csv, gitignored; never commit a roster),
--ontology DIR (default the repository's ontology/; the tests use a temporary copy),
--no-validate (skip the SHACL run; then run ontology/build_graph.py yourself).

What it does with each decision file (format: docs/handover/slice-3a.md):
  1. Refuses the whole file if it is not valid JSON in the documented format, if its
     reviewer_id is not on the roster, or if it decides one target twice.
  2. Refuses one decision, with a clear message, and goes on with the others, when: a
     field is missing or malformed; the target is not a claim (or identity row) in the
     corpus; the reviewer has no grant active on the decision's date whose role may decide
     (reviewer or scholar; editor too for identity) and whose scope covers the claim
     (see common.py, "Scope"); it accepts a claim with no real source in the graph (every
     50 Stories link) without citing one; it is needs discussion without a note; its note
     or citation holds a reviewer's name, an email address or a phone number; the same
     reviewer already decided that target differently; or it contradicts the claim's
     current status (accepted, rejected or under review) - a disagreement goes to the
     review board, not to this script.
  3. Applies what is left: each decision becomes one mrs:ReviewDecision in
     ontology/corpus/reviews.ttl (reviewer by opaque ID; status before and after), and the
     claim's mrs:assertionStatus is changed in the corpus file that states it - one triple,
     located in the text and checked by re-parsing (nothing else may change). A decision
     that agrees with the claim's current status is recorded and changes nothing.
  4. Validates reviews.ttl alone and, if a status changed, the whole graph as
     build_graph.py builds it; writes nothing unless both conform.
Re-importing a file changes nothing. The roster names are printed so the maintainer can
check who sent the file; no name is ever written to a file.
Exit codes: 0 = all done, 1 = something refused or out of step, 2 = could not run.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from pyshacl import validate
from rdflib import Graph
from rdflib.compare import isomorphic

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

DEFAULT_ROSTER = c.ROOT / "review" / "roster.csv"
DEFAULT_INBOX = c.ROOT / "review" / "inbox"
FORMAT = "marsad-review-decisions"
FILE_KEYS = {"format", "version", "reviewer_id", "decisions", "created", "queue"}
DECISION_KEYS = {"kind", "target", "decision", "checks", "note", "citation", "date"}


class Refused(Exception):
    pass


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# reading decision files
# ---------------------------------------------------------------------------

def read_file(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise Refused(f"not a readable JSON file ({e})") from None
    if not isinstance(doc, dict):
        raise Refused("the top level must be a JSON object")
    if doc.get("format") != FORMAT or doc.get("version") != 1:
        raise Refused(f'not a decision file: expected "format": "{FORMAT}", "version": 1')
    extra = sorted(set(doc) - FILE_KEYS)
    if extra:
        raise Refused(f"unknown field(s) {', '.join(extra)}")
    if not isinstance(doc.get("decisions"), list):
        raise Refused('"decisions" must be a list')
    targets = [d.get("target") for d in doc["decisions"] if isinstance(d, dict)]
    twice = sorted({t for t in targets if isinstance(t, str) and targets.count(t) > 1})
    if twice:
        raise Refused(f"decides the same target more than once: {', '.join(twice)}")
    return doc


def text_field(d: dict, key: str) -> str | None:
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise Refused(f'"{key}" must be text')
    v = v.strip()
    if len(v) > c.FREE_TEXT_LIMITS[key]:
        raise Refused(f'"{key}" is longer than {c.FREE_TEXT_LIMITS[key]} characters')
    return v or None


def parse_decision(d) -> dict:
    if not isinstance(d, dict):
        raise Refused("a decision must be a JSON object")
    extra = sorted(set(d) - DECISION_KEYS)
    if extra:
        raise Refused(f"unknown field(s) {', '.join(extra)}")
    for key in ("kind", "target", "decision", "date"):
        if not isinstance(d.get(key), str) or not d[key].strip():
            raise Refused(f'"{key}" is missing')
    if d["kind"] not in ("claim", "identity"):
        raise Refused('"kind" must be "claim" or "identity"')
    if d["decision"] not in c.OUTCOMES:
        raise Refused(f'"decision" must be one of {", ".join(c.OUTCOMES)}')
    checks = d.get("checks", [])
    if not isinstance(checks, list) or any(x not in c.CHECKS for x in checks) or len(set(checks)) != len(checks):
        raise Refused(f'"checks" must list each of {", ".join(c.CHECKS)} at most once')
    try:
        day = c.parse_day(d["date"], '"date"')
    except ValueError as e:
        raise Refused(str(e)) from None
    if day > date.today() + timedelta(days=1):
        raise Refused(f'"date" {day} is in the future')
    return {"kind": d["kind"], "target": d["target"].strip(), "outcome": d["decision"], "checks": tuple(sorted(checks)),
            "note": text_field(d, "note"), "citation": text_field(d, "citation"), "day": day}


# ---------------------------------------------------------------------------
# the import
# ---------------------------------------------------------------------------

class Importer:
    def __init__(self, tree: c.Tree, roster: dict):
        self.tree = tree
        self.roster = roster
        self.names = sorted({g.name for grants in roster.values() for g in grants})
        self.status = {a: tree.status(a) for a in tree.assertions()}
        self.by_key = {(d.reviewer, d.target): d for d in tree.decisions()}
        self.existing = tree.decisions()
        self.new: list[c.Decision] = []
        self.tradition = tree.default_tradition()

    def resolve(self, kind: str, target: str):
        iri = c.expand(target)
        if iri is None:
            raise Refused(f"target {target!r} is not an al-Marsad ID")
        for _ in range(20):  # an ID re-minted since the queue was built (ontology/corpus/id-renames.csv)
            new = self.tree.renames.get(c.curie(iri))
            if not new:
                break
            iri = c.expand(new)
        if kind == "claim":
            if (iri, c.RDF.type, c.MRS.Assertion) not in self.tree.graph:
                raise Refused(f"no claim {c.curie(iri)} in the corpus")
            facets = {"sources": {self.tree.source_of(iri)}, "topic": self.tree.topic_of(iri), "period": self.tree.period_of(iri)}
        else:
            row = self.tree.identity_row(iri)
            if row is None:
                raise Refused(f"no identity row {c.curie(iri)} in identity.csv")
            facets = {"sources": {s for s in row.get("source_files", "").split(";") if s}, "topic": "identity", "period": None}
        return iri, facets

    def authorize(self, reviewer, kind: str, day: date, facets: dict, target):
        grants = self.roster[reviewer]
        active = [g for g in grants if g.active_on(day)]
        if not active:
            raise Refused(f"the reviewer has no grant active on {day}")
        deciding = [g for g in active if g.role in c.DECIDING_ROLES[kind]]
        if not deciding:
            raise Refused(f"role {', '.join(sorted({g.role for g in active}))} may not decide a {kind} "
                          f"(docs/06 §3.1: {', '.join(sorted(c.DECIDING_ROLES[kind]))})")
        if not any(c.scope_matches(g.scope, facets) for g in deciding):
            raise Refused(f"out of scope: {c.curie(target)} is {c.describe_facets(facets)}; the reviewer's scope is "
                          + " | ".join(repr(g.scope_text) for g in deciding))

    def decide(self, reviewer, raw) -> str:
        d = parse_decision(raw)
        target, facets = self.resolve(d["kind"], d["target"])
        self.authorize(reviewer, d["kind"], d["day"], facets, target)
        for key in ("note", "citation"):
            why = d[key] and c.private_data_in(d[key], self.names)
            if why:
                raise Refused(f"the {key} contains {why}; names and contact details must not enter the public record")
        if d["outcome"] == "needs_discussion" and not d["note"]:
            raise Refused("needs discussion must carry a note: the review board needs the reason")
        new = c.Decision(iri=None, target=target, reviewer=reviewer, outcome=d["outcome"], checks=d["checks"],
                         note=d["note"], citation=d["citation"], day=d["day"].isoformat(), tradition=self.tradition)
        if d["kind"] == "claim":
            if d["outcome"] == "accept" and not d["citation"] and not self.tree.has_real_source(target):
                basis = "an AI-generated document" if self.tree.ai_basis(target) else "no source passage"
                raise Refused(f"accept refused: {c.curie(target)} rests on {basis}, with no real source in the graph. "
                              "Accepting it needs the real source the reviewer checked (work and location, "
                              "e.g. volume and page). Never invent one.")
            new.status_before = self.status[target]
            new.status_after = c.OUTCOME_STATUS[d["outcome"]]
        else:
            new.question = "same_as"
        prior = self.by_key.get((reviewer, target))
        if prior is not None:
            if prior.content() == new.content():
                return "already imported"
            raise Refused(f"this reviewer already decided {c.curie(target)} on {prior.day} ({prior.outcome}); "
                          "a change goes through the maintainer")
        if d["kind"] == "claim":
            before, after = new.status_before, new.status_after
            if before not in ("proposed", after):
                last = [x for x in self.existing + self.new if x.target == target]
                who = f" (decided {last[-1].day} by {c.curie(last[-1].reviewer)})" if last else ""
                raise Refused(f"conflict: {c.curie(target)} is already {before}{who}; a different decision goes to "
                              "the review board. Not applied.")
            self.status[target] = after
        self.by_key[(reviewer, target)] = new
        self.new.append(new)
        return "new" if new.status_before != new.status_after or d["kind"] == "identity" else "new (agrees; no change)"


# ---------------------------------------------------------------------------
# writing: reviews.ttl and the status triples
# ---------------------------------------------------------------------------

def edit_statuses(tree: c.Tree, path: Path, text: str, edits: list) -> str:
    """Change each (assertion, old, new) status in one file's text; verify nothing else changed."""
    masked = c.mask_turtle(text)
    spans = []
    for a, old, new in edits:
        found = c.locate_object(text, masked, str(a), str(c.MRS.assertionStatus), str(c.status_iri(old)))
        if len(found) != 1:
            raise Refused(f"{path.name}: found the status of {c.curie(a)} in {len(found)} places, expected 1; nothing written")
        spans.append((found[0], new))
    out = text
    for span, new in sorted(spans, reverse=True):
        out = c.replace_term(out, span, str(c.status_iri(new)))
    before, after = tree.graphs[path], Graph().parse(data=out, format="turtle")
    (pb, nb), (pa, na) = c.strip_bnodes(before), c.strip_bnodes(after)
    want_gone = {(a, c.MRS.assertionStatus, c.status_iri(old)) for a, old, _ in edits}
    want_new = {(a, c.MRS.assertionStatus, c.status_iri(new)) for a, _, new in edits}
    bn_before = Graph()
    bn_after = Graph()
    for t in before:
        if t not in pb:
            bn_before.add(t)
    for t in after:
        if t not in pa:
            bn_after.add(t)
    if pb - pa != want_gone or pa - pb != want_new or nb != na or not isomorphic(bn_before, bn_after):
        raise Refused(f"{path.name}: the status edit would change more than the status triples; nothing written")
    return out


def minting(tree: c.Tree, roster: dict):
    """mint_id.py, and every payload already taken: the repository's, this tree's and the roster's."""
    mint = load_module("mint_id", c.ROOT / "ontology" / "tools" / "mint_id.py")
    taken = set(mint.taken_payloads())
    for text in tree.texts.values():
        taken.update(re.findall(re.escape(c.BASE) + r"[a-z]+/([0-9A-Za-z]+)", text))
        taken.update(p for _, p in re.findall(r"\b([a-z]{2,5}):([0-9A-Za-z]{22})\b", text))
    taken.update(str(r).rsplit("/", 1)[-1] for r in roster)
    return mint, taken


def shacl(tree: c.Tree, texts: dict, whole: bool):
    shapes = Graph().parse(tree.ontology / "shapes.ttl", format="turtle")
    g = Graph()
    g += tree.vocab
    files = texts if whole else {tree.reviews_path: texts[tree.reviews_path]}
    for text in files.values():
        g.parse(data=text, format="turtle")
    if whole:  # the same merge decisions build_graph.py applies
        bg = tree.ontology / "build_graph.py"
        bg = bg if bg.exists() else c.ONTOLOGY / "build_graph.py"
        for s, p, drop, keep, _ in getattr(load_module("build_graph", bg), "MERGE_DECISIONS", []):
            if (s, p, drop) in g and (s, p, keep) in g:
                g.remove((s, p, drop))
    conforms, _, report = validate(g, shacl_graph=shapes, advanced=True, allow_warnings=True)
    return conforms, report


def write(tree: c.Tree, roster: dict, importer_new: list, status_edits: dict, do_validate: bool) -> list[str]:
    """Write reviews.ttl and the changed corpus files, or raise Refused and write nothing."""
    texts = dict(tree.texts)
    texts.setdefault(tree.reviews_path, "")
    existing = tree.decisions()
    log = tree.log_node()
    reviewers = set()
    if tree.reviews_path in tree.graphs:  # never drop what the file holds
        reviewers = set(tree.graphs[tree.reviews_path].subjects(c.RDF.type, c.PROV.Person))
        current = tree.graphs[tree.reviews_path]
        again = Graph().parse(data=c.render_reviews(log, reviewers, existing), format="turtle")
        if set(current) != set(again):
            raise Refused(f"{tree.reviews_path.name} holds content this importer does not write (edited by hand?); "
                          "fix it first. Nothing written.")
    mint, taken = minting(tree, roster)
    if log is None:
        log = c.expand("rvw:" + mint.new_payload(taken))
    for d in importer_new:
        if d.iri is None:
            d.iri = c.expand("rvw:" + mint.new_payload(taken))
    texts[tree.reviews_path] = c.render_reviews(log, reviewers | {d.reviewer for d in importer_new}, existing + importer_new)
    changed = [tree.reviews_path]
    for path, edits in status_edits.items():
        texts[path] = edit_statuses(tree, path, texts[path], edits)
        changed.append(path)
    if do_validate:
        ok, report = shacl(tree, texts, whole=False)
        if ok and status_edits:
            ok, report = shacl(tree, texts, whole=True)
        if not ok:
            raise Refused("the result does not conform to shapes.ttl; nothing written:\n" + report)
    changed = [p for p in changed if texts[p] != tree.texts.get(p)]
    for path in changed:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(texts[path], encoding="utf-8")
        os.replace(tmp, path)
    return [p.name for p in changed]


def plan_edits(tree: c.Tree, changes: list) -> dict:
    """(assertion, old, new) -> {file: [(assertion, old, new)]} for every file that states the old status."""
    edits = {}
    for a, old, new in changes:
        files = [f for f in tree.files_declaring_status(a) if (a, c.MRS.assertionStatus, c.status_iri(old)) in tree.graphs[f]]
        if not files:
            raise Refused(f"no corpus file states {c.curie(a)} as {old}")
        for f in files:
            edits.setdefault(f, []).append((a, old, new))
    return edits


# ---------------------------------------------------------------------------
# --check and --reapply
# ---------------------------------------------------------------------------

def drift(tree: c.Tree) -> tuple[list, list]:
    """(restorable [(assertion, current, expected)], problems [str])"""
    restorable, problems = [], []
    by_target = tree.decisions_by_target()
    for target, ds in sorted(by_target.items(), key=lambda kv: str(kv[0])):
        claim = [d for d in ds if d.status_after]
        if not claim:
            if tree.identity_row(target) is None:
                problems.append(f"identity decision on {c.curie(target)}, which has no identity row")
            continue
        if (target, c.RDF.type, c.MRS.Assertion) not in tree.graph:
            problems.append(f"decision on {c.curie(target)}, which is no longer a claim in the corpus")
            continue
        expected, current = claim[-1].status_after, tree.status(target)
        if current == expected:
            continue
        if current == claim[0].status_before:
            restorable.append((target, current, expected))
        else:
            problems.append(f"{c.curie(target)} is {current}, but its last decision ({claim[-1].day}) set {expected}")
    for a in tree.assertions():
        st = tree.status(a)
        if st in ("accepted", "rejected", "under_review") and not any(d.status_after == st for d in by_target.get(a, [])):
            problems.append(f"{c.curie(a)} is {st} with no review decision that set it (RD4)")
    return restorable, problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="*", type=Path, help="decision files (default: every *.json in review/inbox/)")
    ap.add_argument("--roster", type=Path, default=DEFAULT_ROSTER)
    ap.add_argument("--ontology", type=Path, default=c.ONTOLOGY)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-validate", action="store_true")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--reapply", action="store_true")
    args = ap.parse_args(argv)

    tree = c.Tree(args.ontology)
    restorable, problems = drift(tree)
    for a, cur, exp in restorable:
        print(f"out of step: {c.curie(a)} is {cur}; reviews.ttl says {exp}")
    for p in problems:
        print(f"problem: {p}")
    if args.check:
        print("statuses agree with reviews.ttl" if not (restorable or problems) else
              "statuses do not agree with reviews.ttl" + (" (--reapply restores the out-of-step ones)" if restorable else ""))
        return 1 if (restorable or problems) else 0
    if args.reapply:
        if not restorable or args.dry_run:
            print(f"{len(restorable)} status(es) to restore" + (" (dry run; nothing written)" if restorable else ""))
            return 1 if problems else 0
        try:
            names = write(tree, {}, [], plan_edits(tree, restorable), not args.no_validate)
        except Refused as e:
            print(f"error: {e}")
            return 1
        print(f"restored {len(restorable)} status(es) from reviews.ttl; wrote {', '.join(names)}")
        return 1 if problems else 0
    if restorable or problems:
        print("error: corpus statuses disagree with reviews.ttl (was a corpus file regenerated?). "
              "Run --check, then --reapply. Nothing imported.")
        return 1

    try:
        roster = c.load_roster(args.roster, tree)
    except ValueError as e:
        print(f"error: {e}")
        return 2
    files = args.files or sorted(DEFAULT_INBOX.glob("*.json"))
    if not files:
        print(f"no decision files (looked in {DEFAULT_INBOX})")
        return 0
    imp = Importer(tree, roster)
    refused = 0
    for path in files:
        try:
            doc = read_file(path)
            reviewer = c.expand(doc.get("reviewer_id") or "")
            if reviewer is None or reviewer not in roster:
                raise Refused(f"reviewer_id {doc.get('reviewer_id')!r} is not on the roster")
        except Refused as e:
            print(f"{path.name}: REFUSED, nothing imported: {e}")
            refused += 1
            continue
        tally = {}
        lines = []
        for n, raw in enumerate(doc["decisions"], start=1):
            try:
                outcome = imp.decide(reviewer, raw)
            except Refused as e:
                outcome = "refused"
                target = raw.get("target") if isinstance(raw, dict) else None
                lines.append(f"  refused #{n} {target or ''}: {e}")
                refused += 1
            tally[outcome] = tally.get(outcome, 0) + 1
        name = roster[reviewer][0].name
        print(f"{path.name}: {len(doc['decisions'])} decision(s) from {name} ({c.curie(reviewer)}): "
              + ", ".join(f"{v} {k}" for k, v in sorted(tally.items())))
        for line in lines:
            print(line)
    if imp.new and not args.dry_run:
        changes = [(d.target, d.status_before, d.status_after) for d in imp.new
                   if d.status_after and d.status_before != d.status_after]
        try:
            names = write(tree, roster, imp.new, plan_edits(tree, changes), not args.no_validate)
        except Refused as e:
            print(f"error: {e}")
            return 1
        moved = {}
        for _, _, new in changes:
            moved[new] = moved.get(new, 0) + 1
        print(f"wrote {', '.join(names)}: {len(imp.new)} decision(s) recorded; statuses moved: "
              + (", ".join(f"{v} {k}" for k, v in sorted(moved.items())) or "none"))
        print("next: .venv/bin/python ontology/build_graph.py" + ("" if not args.no_validate else " (validation was skipped)"))
    elif imp.new:
        print(f"dry run: {len(imp.new)} decision(s) would be recorded; nothing written")
    else:
        print("nothing new to write")
    return 1 if refused else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)
