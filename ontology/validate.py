#!/usr/bin/env python3
"""
Validate al-Marsad data against the SHACL shapes.

    pip install rdflib pyshacl
    python ontology/validate.py                      # validates the worked example
    python ontology/validate.py path/to/data.ttl ... # validates your own data

Conformance criterion (docs/02 §4): a dataset conforms if it validates
WITHOUT VIOLATION. Warning-level results are advisories that require a
human decision; they do not block conformance.

Exit codes:  0 = conforms   1 = violations   2 = could not run
"""

import sys
import re
from pathlib import Path

try:
    from rdflib import Graph
    from pyshacl import validate
except ImportError:
    sys.exit("Requires rdflib and pyshacl:  pip install rdflib pyshacl")

ONT = Path(__file__).parent
VOCAB = [ONT / "marsad.ttl", ONT / "relations.ttl"]
SHAPES = ONT / "shapes.ttl"
DEFAULT_DATA = [ONT / "examples" / "thawr.ttl"]


def main(argv):
    data_files = [Path(a) for a in argv[1:]] or DEFAULT_DATA

    data = Graph()
    for f in VOCAB + data_files:
        if not f.exists():
            sys.exit(f"missing: {f}")
        data.parse(f, format="turtle")

    shapes = Graph().parse(SHAPES, format="turtle")

    print(f"data:   {len(data)} triples from {len(VOCAB) + len(data_files)} files")
    print(f"shapes: {len(shapes)} triples\n")

    # The spec's conformance criterion: no violations.
    conforms, _, _ = validate(data, shacl_graph=shapes, advanced=True,
                              allow_warnings=True)

    # Second pass to surface advisories the first pass tolerated.
    _, _, full_text = validate(data, shacl_graph=shapes, advanced=True)
    advisories = re.findall(r"Message: (.+)", full_text)

    if conforms:
        print("CONFORMS — no violations.")
    else:
        print("DOES NOT CONFORM — violations below.\n")
        print(full_text)

    if advisories:
        seen = []
        for a in advisories:
            if a not in seen:
                seen.append(a)
        print(f"\n{len(advisories)} advisory result(s), {len(seen)} distinct:")
        for a in seen:
            print(f"  · {a.strip()}")
        print("\nAdvisories flag data a specialist should look at. They do not"
              "\nblock conformance — but a corpus that accumulates them silently"
              "\nis degrading, so track the count over time.")

    return 0 if conforms else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception as e:  # noqa: BLE001
        sys.exit(f"error: {e}")
