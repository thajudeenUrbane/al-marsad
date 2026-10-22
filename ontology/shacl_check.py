"""SHACL checking shared by validate.py and build_graph.py.

One pass per check (the result graph gives both the conformance verdict, which
ignores Warnings as docs/02 §4 says, and the advisories), optionally limited to
chosen focus nodes, and a cache for a file checked on its own: the verdict is kept
under build/cache/shacl/ keyed by the checksum of the file, the vocabulary, the
shapes and the pyshacl version, so an unchanged file is not checked twice.
"""

import hashlib
import json
from pathlib import Path

import pyshacl
from pyshacl import validate
from rdflib import BNode, Graph, Namespace
from rdflib.namespace import RDF

ONT = Path(__file__).resolve().parent
ROOT = ONT.parent
VOCAB = [ONT / "marsad.ttl", ONT / "relations.ttl"]
SHAPES = ONT / "shapes.ttl"
CACHE = ROOT / "build" / "cache" / "shacl"
SH = Namespace("http://www.w3.org/ns/shacl#")


def shapes_graph():
    return Graph().parse(SHAPES, format="turtle")


def check(data, shapes=None, focus_nodes=None):
    """Validate once. Returns (conforms, report_text, advisories); conforms means no Violation."""
    shapes = shapes if shapes is not None else shapes_graph()
    kw = {"focus_nodes": list(focus_nodes)} if focus_nodes is not None else {}
    _, results, text = validate(data, shacl_graph=shapes, advanced=True, **kw)
    severities = [results.value(r, SH.resultSeverity) for r in results.subjects(RDF.type, SH.ValidationResult)]
    violations = sum(1 for s in severities if s == SH.Violation)
    advisories = [str(results.value(r, SH.resultMessage)) for r in results.subjects(RDF.type, SH.ValidationResult)
                  if results.value(r, SH.resultSeverity) != SH.Violation]
    return violations == 0, text, advisories


def _key(path):
    h = hashlib.sha256()
    for f in VOCAB + [SHAPES, Path(path)]:
        h.update(Path(f).read_bytes())
    h.update(pyshacl.__version__.encode())
    return h.hexdigest()


def cached_file_check(path, run=True):
    """Check one data file on its own (with the vocabulary), using the cache.

    Returns (conforms, report_text, advisories, from_cache), or None when the
    verdict is not cached and run is False.
    """
    key = _key(path)
    hit = CACHE / f"{Path(path).name}.{key[:24]}.json"
    if hit.exists():
        d = json.loads(hit.read_text(encoding="utf-8"))
        return d["conforms"], d["text"], d["advisories"], True
    if not run:
        return None
    data = Graph()
    for f in VOCAB + [Path(path)]:
        data.parse(f, format="turtle")
    conforms, text, advisories = check(data)
    CACHE.mkdir(parents=True, exist_ok=True)
    for old in CACHE.glob(f"{Path(path).name}.*.json"):
        old.unlink()
    hit.write_text(json.dumps({"conforms": conforms, "text": text, "advisories": advisories}), encoding="utf-8")
    return conforms, text, advisories, False


# Data files left out of what the pages and the scholars' queue read, until they can carry them (slice 11b).
ON_HOLD_FROM_PAGES = {"ibn-hisham-full.ttl"}
# A file with more triples than this is "large": its own nodes are checked through the per-file
# cache rather than in every joined check.
LARGE = 100_000


def check_joined(parsed, vocab, merge_decisions=(), run_large=False, paths=None):
    """Check a joined graph the way build_graph.py does (slice 11a). `parsed`: file name -> Graph.

    1. each large file on its own, through the cache (computed only when run_large, else
       reported as not checked whole);
    2. every triple of the smaller files, plus what the large files say about nodes another
       file also describes (with their blank-node parts), with the merge decisions applied.
    Returns (conforms, report_text, advisories, notes)."""
    notes, ok_all, texts = [], True, []
    large = sorted(n for n, g in parsed.items() if len(g) > LARGE)
    for name in large:
        path = (paths or {}).get(name)
        res = cached_file_check(path, run=run_large) if path is not None else None
        if res is None:
            notes.append(f"{name}: {len(parsed[name])} triples, no cached verdict for this version of the file: "
                         "checked only where it meets other files")
            continue
        ok, text, _, cached = res
        notes.append(f"{name} on its own: {'conforms' if ok else 'DOES NOT CONFORM'}{' (cached verdict)' if cached else ''}")
        if not ok:
            ok_all = False
            texts.append(text)
    subjects_in = {}
    for name, g in parsed.items():
        for s in set(g.subjects()):
            subjects_in.setdefault(s, set()).add(name)
    shared = {s for s, fs in subjects_in.items() if len(fs) > 1}
    meet = Graph() + vocab
    big = Graph()
    for name, g in parsed.items():
        if name in large:
            big += g
        else:
            meet += g
    todo = [s for s in shared if (s, None, None) in big]
    seen = set()
    while todo:
        s = todo.pop()
        if s in seen:
            continue
        seen.add(s)
        for t in big.triples((s, None, None)):
            meet.add(t)
            if isinstance(t[2], BNode):
                todo.append(t[2])
    for s, p, drop, keep, *_ in merge_decisions:
        if (s, p, drop) in meet and (s, p, keep) in meet:
            meet.remove((s, p, drop))
    ok, text, advisories = check(meet)
    notes.append(f"joined graph checked where files meet: {len(meet)} triples ({len(seen)} nodes from the large files)")
    if not ok:
        texts.append(text)
    return ok and ok_all, "\n".join(texts), advisories, notes
