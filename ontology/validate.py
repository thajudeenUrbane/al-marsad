#!/usr/bin/env python3
"""
Validate al-Marsad data against the SHACL shapes.

    pip install rdflib pyshacl
    python ontology/validate.py                      # validates the worked example
    python ontology/validate.py path/to/data.ttl ... # validates your own data

Conformance criterion (docs/02 §4): a dataset conforms if it validates
WITHOUT VIOLATION. Warning-level results are advisories that require a
human decision; they do not block conformance.

One data file is checked through the cache in ontology/shacl_check.py: an
unchanged file (with unchanged vocabulary and shapes) is not checked twice.

Exit codes:  0 = conforms   1 = violations   2 = could not run
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # shacl_check.py sits beside this file

try:
    from rdflib import Graph
    import shacl_check
except ImportError:
    sys.exit("Requires rdflib and pyshacl:  pip install rdflib pyshacl")

ONT = Path(__file__).parent
VOCAB = [ONT / "marsad.ttl", ONT / "relations.ttl"]
SHAPES = ONT / "shapes.ttl"
DEFAULT_DATA = [ONT / "examples" / "thawr.ttl"]


def main(argv):
    data_files = [Path(a) for a in argv[1:]] or DEFAULT_DATA

    for f in VOCAB + data_files:
        if not f.exists():
            sys.exit(f"missing: {f}")

    if len(data_files) == 1:
        conforms, full_text, advisories, cached = shacl_check.cached_file_check(data_files[0])
        print(f"data:   {data_files[0]} with the vocabulary{' (cached verdict)' if cached else ''}\n")
    else:
        data = Graph()
        for f in VOCAB + data_files:
            data.parse(f, format="turtle")
        print(f"data:   {len(data)} triples from {len(VOCAB) + len(data_files)} files\n")
        # The spec's conformance criterion: no violations (warnings are advisories).
        conforms, full_text, advisories = shacl_check.check(data)

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
