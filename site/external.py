"""Possible matches in other databases (Wikidata, al-Thurayya, OpenITI), read from
ontology/corpus/external-ids.csv when that file exists (slice 5 writes it).

Every row there is a proposal from a matching tool, never an identity decision. The
pages show each one as a possible match with the status the row records ("proposed"
today), and never as a fact about the person or place. Without the file nothing is
shown and nothing fails.

Columns (slice 5): canonical_id, kind, system, external_id, external_label, evidence,
confidence, status. canonical_id is an identity.csv ID such as per:<payload>; its prefix
names the IRI path segment, as in ontology/tools/identity_audit.py (IRI_SEGMENT; a test
checks the two tables agree). Rows for records without a page (works, for example) are
skipped.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "ontology" / "corpus" / "external-ids.csv"
# al-Thurayya's candidates, kept in their own file under al-Thurayya's licence (CC BY 4.0)
CSV_PATH_ALTHURAYYA = ROOT / "ontology" / "corpus" / "external-ids-althurayya.csv"
ID_BASE = "https://w3id.org/marsad/id/"
COLUMNS = ("canonical_id", "kind", "system", "external_id", "external_label", "evidence", "confidence", "status")
PREFIX_SEGMENT = {"per": "person", "plc": "place", "ev": "event", "grp": "group"}
# Only systems whose address pattern is certain get a link; others show the ID as text.
URL_PATTERNS = {"wikidata": ("https://www.wikidata.org/wiki/{id}", re.compile(r"^Q[1-9][0-9]*$"))}
SYSTEM_ORDER = ("wikidata", "althurayya", "openiti")
CONFIDENCE_ORDER = ("exact", "probable", "needs-review")


def iri_for(canonical_id: str) -> str | None:
    prefix, sep, payload = canonical_id.strip().partition(":")
    if not sep or prefix not in PREFIX_SEGMENT or not re.fullmatch(r"[0-9A-Za-z]+", payload):
        return None
    return f"{ID_BASE}{PREFIX_SEGMENT[prefix]}/{payload}"


def url_for(system: str, external_id: str) -> str | None:
    pattern = URL_PATTERNS.get(system)
    if pattern and pattern[1].match(external_id):
        return pattern[0].format(id=external_id)
    return None


def _rank(seq: tuple[str, ...], value: str) -> int:
    return seq.index(value) if value in seq else len(seq)


def load(path: Path | None = None, known: set[str] | None = None) -> dict[str, list[dict]]:
    """{entity IRI: [row, ...]}, rows sorted by system, the tool's confidence, then ID.
    `known`: IRIs that have a page; rows for anything else are left out. A file that
    lacks one of COLUMNS is a build error, so a format change cannot pass silently."""
    if path is None:
        out: dict[str, list[dict]] = {}
        for p in (CSV_PATH, CSV_PATH_ALTHURAYYA):
            for iri, rows in load(p, known).items():
                for r in rows:
                    if r not in out.setdefault(iri, []):
                        out[iri].append(r)
        for rows in out.values():
            rows.sort(key=lambda r: (_rank(SYSTEM_ORDER, r["system"]), r["system"],
                                     _rank(CONFIDENCE_ORDER, r["confidence"]), r["external_id"]))
        return out
    path = Path(path)
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing column(s) {', '.join(missing)}")
        out: dict[str, list[dict]] = {}
        for row in reader:
            iri = iri_for(row["canonical_id"] or "")
            if iri is None or (known is not None and iri not in known):
                continue
            ext = (row["external_id"] or "").strip()
            if not ext:
                continue
            item = {k: (row[k] or "").strip() for k in COLUMNS}
            item["url"] = url_for(item["system"], ext)
            if item not in out.setdefault(iri, []):
                out[iri].append(item)
    for rows in out.values():
        rows.sort(key=lambda r: (_rank(SYSTEM_ORDER, r["system"]), r["system"],
                                 _rank(CONFIDENCE_ORDER, r["confidence"]), r["external_id"]))
    return out
