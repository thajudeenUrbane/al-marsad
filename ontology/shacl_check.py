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
from rdflib import Graph, Namespace
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
