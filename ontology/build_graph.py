#!/usr/bin/env python3
"""
Build the one graph (slice 1c; the full Ibn Hishām layer joined in slice 11a).

    .venv/bin/python ontology/build_graph.py
    .venv/bin/python ontology/build_graph.py --full    # also check every node of the large files in the joined graph (slow)
    .venv/bin/python ontology/build_graph.py --query ontology/queries/abu_bakr.rq   # also run a SPARQL file on the joined graph

Loads marsad.ttl, relations.ttl and every .ttl in ontology/corpus/ and
ontology/examples/ into a single graph, applies the merge decisions listed in
MERGE_DECISIONS below (printed every run), prints the number of instances per
class, and validates against shapes.ttl (a graph conforms when it has no
Violation; Warnings are advisories). It writes two files (gitignored):

- build/graph-all.ttl: the joined graph, every data file.
- build/graph.ttl: the graph the reader pages, Ask, learning paths and the views
  read. It leaves out the files in ON_HOLD_FROM_PAGES until the pages can carry
  them (slice 11b); everything else reads exactly as before.

Checking at this size (slice 11a). The full-book file is about 500,000 triples and
SHACL over all of it takes about half an hour, so:
1. every data file is checked on its own (with the vocabulary), and the verdict is
   cached by checksum (ontology/shacl_check.py): an unchanged file is not re-checked;
   a large file with no cached verdict is checked only with --full (or by
   `ontology/validate.py FILE`, which fills the same cache);
2. the joined graph is checked on every node of the smaller files and on every node
   that more than one file describes: that is where files can contradict each other
   (two values for a single-valued property, a type from one file, a link from another).
   Nodes that only a large file describes were covered by step 1.

Exit codes:  0 = conforms   1 = violations   2 = could not run

Duplicate labels. The corpus files still each declare some of the same
entities, so a merged entity can carry several rdfs:label values (one per
source). They are all kept: nothing is dropped or promoted to a "preferred"
label in the graph (the ontology uses skos:prefLabel only for controlled
vocabulary, and PersonShape forbids auto-selecting a canonical display name).
The display name for an entity is preferred_name_en in
ontology/corpus/identity.csv. The count of multi-label entities is printed.
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # shacl_check.py sits beside this file

try:
    from rdflib import RDF, RDFS, BNode, Graph, Namespace, URIRef
    import shacl_check
except ImportError:
    sys.exit("Requires rdflib and pyshacl:  pip install rdflib pyshacl")

ONT = Path(__file__).resolve().parent
ROOT = ONT.parent
VOCAB = [ONT / "marsad.ttl", ONT / "relations.ttl"]
SHAPES = ONT / "shapes.ttl"
DATA = sorted((ONT / "corpus").glob("*.ttl")) + sorted((ONT / "examples").glob("*.ttl"))
OUT = ROOT / "build" / "graph.ttl"
OUT_ALL = ROOT / "build" / "graph-all.ttl"
MRS = Namespace("https://w3id.org/marsad/core#")
PLC = Namespace("https://w3id.org/marsad/id/place/")
BASE = "https://w3id.org/marsad/id/"
# Data files left out of build/graph.ttl (the pages' graph) for now, and the size above which a
# file counts as large: both in ontology/shacl_check.py, which the review importer shares.
ON_HOLD_FROM_PAGES = shacl_check.ON_HOLD_FROM_PAGES

# Merge decisions: triples that are in the sources and are left OUT of the unified
# graph because the merge makes a single-valued property multi-valued. Source files
# are never edited (each must still validate on its own). Each entry is
# (subject, predicate, left-out object, kept object, reason). A stale entry (the
# triple is no longer there) is an error so this list cannot rot silently.
#
# Ghar Thawr (O4): the maintainer was unsure, so the default stands. The maintainer
# accepted the default (keep `cave`) on 15 October 2026. Leave this entry as it is.
# (The IRI is the slice 1d re-minted one; the retired ID is a variant in identity.csv.)
MERGE_DECISIONS = [
    (PLC["Tvj82GYrHHvbBIehvFBQcA"], MRS.placeType, MRS.pt_route_node, MRS.pt_cave,
     "Ghar Thawr: examples/thawr.ttl says cave, corpus/seed-incidents.ttl says route node; PlaceShape allows exactly one "
     "placeType. Provisional: the physical type (cave) is kept and route node is left out of the unified graph. "
     "A maintainer/scholar decision; both stay in their source files."),
]


def short(g, term):
    try:
        return g.namespace_manager.normalizeUri(term)
    except Exception:  # noqa: BLE001
        return str(term)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--query", type=Path, help="SPARQL SELECT file to run on the joined graph after building")
    ap.add_argument("--full", action="store_true", help="check large files on their own when no verdict is cached (slow)")
    args = ap.parse_args()
    vocab = Graph()
    for f in VOCAB:
        vocab.parse(f, format="turtle")
    pages = Graph() + vocab
    held = Graph()
    declared_in = {}   # entity IRI -> files that type it
    parsed = {}
    for f in DATA:
        sub = Graph().parse(f, format="turtle")
        parsed[f.name] = sub
        for s, _, o in sub.triples((None, RDF.type, None)):
            if isinstance(s, URIRef) and str(s).startswith(BASE):
                declared_in.setdefault(s, set()).add(f.name)
        (held if f.name in ON_HOLD_FROM_PAGES else pages).__iadd__(sub)
    g = pages + held
    for prefix, ns in vocab.namespaces():
        g.bind(prefix, ns)
        pages.bind(prefix, ns)

    print(f"loaded: {len(VOCAB)} vocabulary files + {len(DATA)} data files "
          f"({', '.join(f.name for f in DATA)}) -> {len(g)} triples")

    # merge decisions, in both graphs
    for s, p, drop, keep, why in MERGE_DECISIONS:
        if (s, p, drop) not in g or (s, p, keep) not in g:
            print(f"error: stale merge decision for {short(g, s)} {short(g, p)}: the triple to leave out or the one to keep "
                  "is no longer in the sources", file=sys.stderr)
            return 2
        g.remove((s, p, drop))
        pages.remove((s, p, drop))
        print(f"merge decision: left out {short(g, s)} {short(g, p)} {short(g, drop)} (kept {short(g, keep)}). {why}")

    OUT.parent.mkdir(exist_ok=True)
    g.serialize(OUT_ALL, format="turtle")
    pages.serialize(OUT, format="turtle")

    # counts per class (instances only: subjects that are not defined in the vocabulary files)
    vocab_subjects = set(vocab.subjects())
    counts = Counter()
    for s, _, c in g.triples((None, RDF.type, None)):
        if s not in vocab_subjects:
            counts[c] += 1
    print(f"\ninstances per class in the joined graph ({sum(counts.values())} typed nodes):")
    for c, n in sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        print(f"  {n:6d}  {short(g, c)}")

    entities = [s for s in declared_in if (s, RDF.type, None) in g]
    multi_file = [s for s, fs in declared_in.items() if len(fs) > 1]
    labels = Counter()
    for s in set(g.subjects(RDFS.label, None)):
        if isinstance(s, URIRef) and str(s).startswith(BASE):
            labels[len(set(g.objects(s, RDFS.label)))] += 1
    print(f"\nentity IRIs typed in the data files: {len(entities)}; typed in more than one file: {len(multi_file)}")
    print(f"entities with more than one rdfs:label (all kept): {sum(n for k, n in labels.items() if k > 1)}")

    # each large file on its own (cached), and the joined graph where files meet: ontology/shacl_check.py
    ok, full_text, advisories, notes = shacl_check.check_joined(
        parsed, vocab, MERGE_DECISIONS, run_large=args.full, paths={f.name: f for f in DATA})
    for n in notes:
        print("\n" + n)
    print(f"\nwrote {OUT_ALL.relative_to(ROOT)} ({len(g)} triples) and {OUT.relative_to(ROOT)} "
          f"({len(pages)} triples; on hold from the pages: {', '.join(sorted(ON_HOLD_FROM_PAGES)) or 'none'})")
    if ok:
        print("CONFORMS - no violations.")
    else:
        print("DOES NOT CONFORM - violations below.\n")
        print(full_text)
    if advisories:
        print(f"{len(advisories)} advisory result(s), {len(set(advisories))} distinct (warnings do not block conformance).")
    if args.query:
        print(f"\nquery {args.query}:")
        res = g.query(args.query.read_text(encoding="utf-8"))
        print("\t".join(str(v) for v in res.vars))
        for row in res:
            print("\t".join("" if x is None else str(x) for x in row))
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        sys.exit(f"error: {e}")
