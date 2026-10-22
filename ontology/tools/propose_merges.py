#!/usr/bin/env python3
"""
Propose merges of duplicate entries (slice 11a, maintainer F3): proposals only, for an editor.

    .venv/bin/python ontology/tools/propose_merges.py           # write ontology/corpus/merge-proposals.csv
    .venv/bin/python ontology/tools/propose_merges.py --check   # exit 1 if the committed file is not current

The full-book pass read the Sīra in 96 chunks and matched people across chunks only by
name and father line, so one person, place or event can have several entries, and the
earlier corpora name some of the same events again. This tool lists candidate pairs
with the evidence for each. It never merges: an editor fills in the `decision` column
(accept / reject / scholar), the maintainer approves, and an accepted row is applied
the way identity.csv already works (the merged ID becomes a variant, its address
redirects; maintainer P8). Scholars see only the rows marked `scholar`. The review pages
(review/build_pages.py) show the undecided rows as "same entry?" questions, and
review/import_decisions.py writes the decision, the reviewer's opaque ID, the date and any
note into the four decision columns; a re-run here keeps them.

What is proposed, in this order:
1. events with the same name once articles, diacritics, a trailing "(2)" and
   parentheses are set aside ("The Battle of the Yarmūk" / "The Battle of al-Yarmūk").
   A story event of the 50 Stories is never proposed as one with a historical event:
   that pairing is listed with confidence `scholar` (a story is a telling, docs/02);
2. every person with a recorded claim (slice 11a began with the 100 most connected),
   against every other person entry with the same name or a name it gives in brackets ("ʿAbd al-ʿUzzā ... (Abū
   Lahab)"): `probable` when the recorded fathers agree (and the grandfathers, where
   both are recorded), `possible` when one side records no father or is an ancestor
   in a lineage, `scholar` when fathers or grandfathers differ, when the entries'
   notes tell namesakes apart ("of Banū ʿAbd al-Dār"), or when the name is only a kunya.
   A single name is never matched on: one word (ʿAmr, Kaʿb), a compound ism (ʿAbd Allāh,
   ʿAbd al-Dār, ʿUbayd Allāh) or Imruʾ al-Qays;
3. royal titles recorded as persons (Qayṣar, Kisrā, al-Najāshī ...): grouped under the
   title for the office model (maintainer F12), confidence `scholar`.

Confidence is about the evidence listed, never about the history.
"""

import argparse
import csv
import io
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IDENTITY = ROOT / "ontology" / "corpus" / "identity.csv"
CLAIMS = [ROOT / "ingest" / "claims" / "ibn-hisham-full.jsonl", ROOT / "ingest" / "claims" / "ibn-hisham.jsonl"]
OUT = ROOT / "ontology" / "corpus" / "merge-proposals.csv"
TOP_PEOPLE = None  # every person with a recorded claim (slice 11a began with the 100 most connected)
STOP = {"the", "of", "a", "an", "at", "in", "to", "and", "s"}
KUNYA = {"abu", "abi", "aba", "umm"}
TITLES = ["qaysar", "kisra", "najashi", "tubba", "muqawqis", "hiraql"]
FIELDS = ["proposal", "kind", "keep_id", "keep_name", "merge_id", "merge_name", "evidence", "confidence",
          "decision", "decided_by", "decided_on", "decision_note"]
DECIDED = ("decision", "decided_by", "decided_on", "decision_note")  # written by review/import_decisions.py


def fold(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[ʿʾ'’`ʿʾ]", "", s).lower()
    return s


def base_tokens(name):
    """Name tokens with brackets, '(2)', articles and stop words set aside."""
    s = fold(re.sub(r"\([^)]*\)", " ", name))
    s = re.sub(r"\b(al|as|ash|ad|adh|at|ath|an|ar|az|az)-", "", s)
    toks = re.findall(r"[a-z]+", s)
    out = []
    for t in toks:
        if t in STOP:
            continue
        t = {"ibn": "b", "bin": "b", "bint": "bt", "abdullah": "abd allah", "accepts": "accept",
             "acceptance": "accept"}.get(t, t)
        t = re.sub(r"(ah|a)$", "a", t)  # Ḥamzah / Ḥamza
        out.extend(t.split())
    return tuple(out)


def aliases(name):
    """A person's name and the names it gives in brackets (not '(2)', not '(father of ...)')."""
    names = [base_tokens(name)]
    for inner in re.findall(r"\(([^)]*)\)", name):
        f = fold(inner).strip()
        if not f or re.match(r"^\d+$|^note\b|^father of|^mother of|^son of|^of\b|^from\b|^ancestor|^transmitter|^narrator|^poet", f):
            continue
        names.append(base_tokens(inner))
    # a bare single name (ʿAmr, Kaʿb, and a compound ism such as ʿAbd Allāh or ʿAbd al-Dār) says nothing
    # about who is meant: never matched on (as in the full pass)
    return [n for n in names if units(n) > 1]


def units(tokens):
    """Name units: 'abd' with the word after it is one name (ʿAbd Allāh, ʿAbd al-Dār once articles go), as are
    'X Allāh' (ʿUbayd Allāh) and Imruʾ al-Qays."""
    n, skip = 0, False
    for t in tokens:
        if skip:
            skip = False
            continue
        if t in ("alla", "allah") and n:  # ʿUbayd Allāh, Taym Allāh: one name
            continue
        n += 1
        if t in ("abd", "imru", "imr", "imra"):  # ʿAbd X, Imruʾ al-Qays: one name
            skip = True
    return n


def first_name(tokens):
    """Up to the first 'b'/'bt' (the person's own name, without the father line)."""
    out = []
    for t in tokens:
        if t in ("b", "bt"):
            break
        out.append(t)
    return tuple(out)


def read_identity():
    with IDENTITY.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_claims():
    rows = []
    for f in CLAIMS:
        if f.exists():
            rows += [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows


def is_story(row):
    """An event minted for a story of the 50 Stories (slice 1c), whatever files now refer to it."""
    return row["kind"] == "event" and "story-unit event" in row.get("note", "")


def rank(row):
    """Which entry to keep: the one the older, hand-curated files describe, then the most files."""
    files = row["source_files"].split(";")
    curated = any(f in files for f in ("thawr", "generation-1", "seed-incidents"))
    return (0 if curated else 1, 0 if "ibn-hisham" in files else 1, -len(files), row["canonical_id"])


def proposals():
    ident = read_identity()
    by_name = defaultdict(list)
    for r in ident:
        by_name[(r["kind"], r["preferred_name_en"])].append(r)
    claims = load_claims()

    def rid(x):
        if not isinstance(x, dict) or "name" not in x:
            return None
        rows = by_name.get((x.get("kind"), x["name"]))
        return rows[0]["canonical_id"] if rows else None

    degree = Counter()
    fathers = defaultdict(set)     # person id -> father's own name (tokens)
    father_ids = defaultdict(set)  # person id -> father's id
    for c in claims:
        s, o = rid(c["subject"]), rid(c["object"])
        for x in (s, o):
            if x:
                degree[x] += 1
        if c["predicate"] == "rel_father_of" and s and o:
            fathers[o].add(first_name(base_tokens(c["subject"]["name"])))
            father_ids[o].add(s)

    def grandfathers(pid):
        return {g for f in father_ids[pid] for g in fathers[f]}

    def notes(name):
        """Bracketed notes that tell namesakes apart ("of Banū ʿAbd al-Dār", "ancestor in ...")."""
        return {fold(n).strip() for n in re.findall(r"\(([^)]*)\)", name)
                if re.match(r"^(of |ancestor|from )", fold(n).strip())}
    out = []

    # 1. events
    events = [r for r in ident if r["kind"] == "event"]
    groups = defaultdict(list)
    for r in events:
        groups[base_tokens(r["preferred_name_en"])].append(r)
    for key, rows in sorted(groups.items()):
        if len(rows) < 2 or not key:
            continue
        rows = sorted(rows, key=rank)
        keep = next((r for r in rows if not is_story(r)), rows[0])
        for r in rows:
            if r is keep:
                continue
            story = is_story(r) or is_story(keep)
            out.append(("event", keep, r,
                        "same event name once articles, diacritics, brackets and '(2)' are set aside"
                        + ("; one is a story of the 50 Stories, which is never merged with a historical event by rule"
                           if story else ""),
                        "scholar" if story else "probable"))

    # 2. people: the most-connected, against every other person entry with a shared name
    people = [r for r in ident if r["kind"] == "person"]
    index = defaultdict(list)
    for r in people:
        for a in aliases(r["preferred_name_en"]):
            index[a].append(r)
    top = [r for r in sorted(people, key=lambda r: (-degree[r["canonical_id"]], r["canonical_id"]))[:TOP_PEOPLE]
           if degree[r["canonical_id"]]]
    seen = set()
    for r in top:
        for a in aliases(r["preferred_name_en"]):
            for o in index[a]:
                if o["canonical_id"] == r["canonical_id"]:
                    continue
                pair = tuple(sorted((r["canonical_id"], o["canonical_id"])))
                if pair in seen:
                    continue
                seen.add(pair)
                keep, other = sorted((r, o), key=rank)
                fk, fo = fathers[keep["canonical_id"]], fathers[other["canonical_id"]]
                gk, go = grandfathers(keep["canonical_id"]), grandfathers(other["canonical_id"])
                nk, no = notes(keep["preferred_name_en"]), notes(other["preferred_name_en"])
                only_kunya = len(a) <= 3 and a[0] in KUNYA and "b" not in a
                if only_kunya:
                    conf, why = "scholar", "same name, but only a kunya (which different people share)"
                elif nk and no and not nk & no:
                    conf, why = "scholar", "same name, but the entries' notes tell namesakes apart"
                elif fk and fo and fk & fo and gk and go and not gk & go:
                    conf, why = "scholar", "same name and father's name, but different recorded grandfathers"
                elif fk and fo and fk & fo:
                    grand = " and grandfather" if gk & go else ""
                    conf, why = "probable", f"same name and the same recorded father{grand} ({' '.join(sorted(fk & fo)[0])})"
                elif fk and fo:
                    conf, why = "scholar", "same name but different recorded fathers"
                else:
                    conf, why = "possible", "same name; one side records no father"
                if conf == "probable" and any(n.startswith("ancestor") for n in nk | no):
                    conf, why = "possible", why + "; an ancestor in a lineage, where one name recurs across generations"
                elif conf == "probable" and bool(nk) != bool(no):
                    conf, why = "possible", why + "; only one entry carries a note telling namesakes apart: check it"
                out.append(("person", keep, other, f"{why}; the name compared: {' '.join(a)}", conf))

    # 3. titles held by persons
    titled = defaultdict(list)
    for r in people:
        toks = base_tokens(r["preferred_name_en"])
        for t in TITLES:
            if toks and toks[0] == t:
                titled[t].append(r)
    for t, rows in sorted(titled.items()):
        if len(rows) < 2:
            continue
        rows = sorted(rows, key=rank)
        for r in rows[1:]:
            out.append(("title", rows[0], r,
                        f"both are recorded under the title {t}: possibly one office held by different persons "
                        "(maintainer F12), possibly one person", "scholar"))

    order = {"event": 0, "person": 1, "title": 2}
    conf_order = {"probable": 0, "possible": 1, "scholar": 2}
    out.sort(key=lambda x: (order[x[0]], conf_order[x[4]], x[1]["preferred_name_en"], x[2]["canonical_id"]))
    rows = []
    for n, (kind, keep, other, why, conf) in enumerate(out, 1):
        rows.append({"proposal": f"M{n:04d}", "kind": kind, "keep_id": keep["canonical_id"],
                     "keep_name": keep["preferred_name_en"], "merge_id": other["canonical_id"],
                     "merge_name": other["preferred_name_en"], "evidence": why, "confidence": conf,
                     "decision": "", "decided_by": "", "decided_on": "", "decision_note": ""})
    return rows


def render(rows, previous):
    """Keep decisions already written into the committed file (matched by keep_id + merge_id)."""
    done = {(r["keep_id"], r["merge_id"]): r for r in previous}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        d = done.get((r["keep_id"], r["merge_id"]))
        if d:
            for k in DECIDED:
                r[k] = d.get(k, "")
        w.writerow(r)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    previous = list(csv.DictReader(OUT.open(encoding="utf-8"))) if OUT.exists() else []
    rows = proposals()
    text = render(rows, previous)
    if a.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"{OUT.relative_to(ROOT)} is not current: run ontology/tools/propose_merges.py")
            return 1
        print(f"{OUT.relative_to(ROOT)} is up to date")
        return 0
    OUT.write_text(text, encoding="utf-8")
    c = Counter((r["kind"], r["confidence"]) for r in rows)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} proposals")
    for k, v in sorted(c.items()):
        print(f"  {v:5d}  {k[0]:7} {k[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
