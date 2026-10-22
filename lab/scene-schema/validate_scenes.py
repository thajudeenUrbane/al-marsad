"""Validate scene-layer examples against scene-shapes.ttl (lab).

Usage: python lab/scene-schema/validate_scenes.py [data.ttl ...]
Groups results by Part: focus nodes under .../scene/INVALID- are Part B.
"""
import sys
from pathlib import Path
from collections import Counter
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef, BNode
from rdflib.namespace import RDF

HERE = Path(__file__).resolve().parent
SH = Namespace("http://www.w3.org/ns/shacl#")
BAD = "https://w3id.org/marsad/id/scene/INVALID-"

def owner(g, node):
    """Walk up from a blank node to the first IRI that points at it."""
    seen = set()
    while isinstance(node, BNode) and node not in seen:
        seen.add(node)
        subj = next(g.subjects(None, node), None)
        if subj is None:
            break
        node = subj
    return node

def main(paths):
    data = Graph()
    for p in paths or [HERE / "examples" / "hijrah-cave.ttl"]:
        data.parse(p, format="turtle")
    shapes = Graph().parse(HERE / "scene-shapes.ttl", format="turtle")
    ont = Graph().parse(HERE / "scenes.ttl", format="turtle")
    ont.parse(HERE.parent.parent / "ontology" / "marsad.ttl", format="turtle")
    data += ont   # vocabulary individuals (statuses, roles) must be typed for sh:class
    conforms, report, _ = validate(data, shacl_graph=shapes,
                                   inference="none", advanced=True, allow_warnings=True)
    parts = {"A (valid)": Counter(), "B (invalid)": Counter()}
    lines = []
    for r in report.subjects(RDF.type, SH.ValidationResult):
        focus = report.value(r, SH.focusNode)
        own = owner(data, focus)
        part = "B (invalid)" if str(own).startswith(BAD) else "A (valid)"
        sev = str(report.value(r, SH.resultSeverity)).split("#")[-1]
        msg = str(report.value(r, SH.resultMessage) or "")
        parts[part][sev] += 1
        lines.append(f"[{part}] {sev}: {str(own).rsplit('/',1)[-1]}: {msg[:140]}")
    for l in sorted(lines):
        print(l)
    for k, c in parts.items():
        print(f"Part {k}: {dict(c) or 'no results'}")
    ok = not parts["A (valid)"] and parts["B (invalid)"]
    print("EXPECTED OUTCOME" if ok else "UNEXPECTED OUTCOME")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
