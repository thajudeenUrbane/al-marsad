#!/usr/bin/env python3
"""
Build the Sira network page: every person, place and event of the full-book pass over
Ibn Hisham's al-Sira al-Nabawiyya, and every relation between them, as one
self-contained page (sira-network/index.html, committed, like the other prototypes).

    python sira-network/build.py

Reads only committed files, so it needs neither the cached text nor rdflib:
  ingest/claims/ibn-hisham-full*.jsonl       the claims, passages and new entities
  ontology/corpus/identity.csv               names (English and Arabic as written)
  ontology/corpus/ibn-hisham-full.ttl   each passage's citation (page, milestone, lines)
  ontology/relations.ttl                     each relation's label and class

Nothing on the page is typed in by hand. Every edge is a proposed, AI-extracted claim
that nobody has reviewed, and the page says so. It draws only what the claims state: no
inferred edges, no metric, no ranking (lists are alphabetical). The Arabic text of the
book is not on the page; only names, as identity.csv holds them.
"""

import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAIMS_DIR = ROOT / "ingest" / "claims"
PASSAGES = CLAIMS_DIR / "ibn-hisham-full-passages.jsonl"
CLAIMS = CLAIMS_DIR / "ibn-hisham-full.jsonl"
ENTITIES = CLAIMS_DIR / "ibn-hisham-full-entities.jsonl"
IDENTITY = ROOT / "ontology" / "corpus" / "identity.csv"
TTL = ROOT / "ontology" / "corpus" / "ibn-hisham-full.ttl"
RELATIONS = ROOT / "ontology" / "relations.ttl"
TEMPLATE = Path(__file__).resolve().parent / "index.template.html"
OUT = Path(__file__).resolve().parent / "index.html"
KINDS = {"person": 0, "place": 1, "event": 2}
CLASSES = ["kinship", "social_political", "transmission", "spatial", "participation", "evidentiary"]


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def relations() -> dict:
    """rel_x -> (label, class index)"""
    out = {}
    text = RELATIONS.read_text(encoding="utf-8")
    for m in re.finditer(r"^mrs:(rel_\w+) a mrs:RelationType ;(.*?)\.\s*$", text, re.M | re.S):
        label = re.search(r'skos:prefLabel "([^"]+)"@en', m.group(2))
        cls = re.search(r"mrs:relationClass mrs:relclass_(\w+)", m.group(2))
        out[m.group(1)] = (label.group(1) if label else m.group(1), CLASSES.index(cls.group(1)) if cls else 5)
    return out


def citations() -> dict:
    """passage id -> its short citation, read off the generated Turtle."""
    text = TTL.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^(psg:\w+)\n    a mrs:Passage , oa:SpecificResource ;\n(.*?)\n\n", text, re.M | re.S):
        c = re.search(r'mrs:canonicalCitation "([^"]+)"', m.group(2))
        if c:
            cit = c.group(1)
            cit = cit.split("provisional), ", 1)[-1]  # the edition is named once on the page
            out[m.group(1)] = cit
    return out


def fold(s: str) -> str:
    """Search key: no diacritics, no ʿ ʾ, lower case; Arabic without vowels, hamza forms or tatweel."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[ʿʾ'’‘`]", "", s).lower()
    s = re.sub(r"[ً-ْٰـ]", "", s)
    s = re.sub("[إأآٱ]", "ا", s).replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"\s+", " ", s).strip()


def main():
    for f in (PASSAGES, CLAIMS, TTL):
        if not f.exists():
            sys.exit(f"missing {f.relative_to(ROOT)}: run ingest/sira_full.py assemble and ingest/ibn_hisham.py build full")
    rels = relations()
    cits = citations()
    with IDENTITY.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    by_name = {}
    by_id = {}
    for r in rows:
        if r["kind"] in KINDS:
            by_name.setdefault((r["kind"], r["preferred_name_en"]), []).append(r)
            by_id[r["canonical_id"]] = r

    def row_of(ref: dict) -> dict:
        rs = by_name.get((ref["kind"], ref["name"]), [])
        if len(rs) != 1 and ref.get("id"):
            rs = [by_id[ref["id"]]]
        if len(rs) != 1:
            sys.exit(f"{ref}: not exactly one identity.csv row")
        return rs[0]

    passages = read_jsonl(PASSAGES)
    pidx = {}
    plist = []
    for p in passages:
        pidx[p["id"]] = len(plist)
        label = re.sub(r" \(Ibn Hisham, Sira, section \d+\)$", "", p["label"])
        plist.append([label, cits.get(p["id"], "")])

    nodes, nidx = [], {}

    def node(ref: dict) -> int:
        r = row_of(ref)
        cid = r["canonical_id"]
        if cid not in nidx:
            nidx[cid] = len(nodes)
            new = "full-book pass" in r["note"]
            nodes.append([KINDS[r["kind"]], r["preferred_name_en"], r["name_ar"], 0 if new else 1, cid])
        return nidx[cid]

    preds = sorted({c["predicate"] for c in read_jsonl(CLAIMS)})
    pred_index = {p: k for k, p in enumerate(preds)}
    edges, dated = [], []
    qbits = {"hedged": 1, "text_alternative": 2, "share_not_present": 4, "editorial_brackets": 8}
    for c in read_jsonl(CLAIMS):
        s = node(c["subject"])
        q = sum(qbits.get(x, 0) for x in c.get("qualifiers", []))
        if "literal_spans" in c["object"]:
            dated.append([s, pidx[c["passage"]]])
            continue
        o = node(c["object"])
        edges.append([s, pred_index[c["predicate"]], o, pidx[c["passage"]], q])
    for e in read_jsonl(ENTITIES):  # every named person, place and event, with or without a relation
        node({"kind": e["kind"], "name": e["name"]})
    order = sorted(range(len(nodes)), key=lambda i: fold(nodes[i][1]))
    data = {
        "nodes": nodes,
        "order": order,
        "fold": [fold(n[1]) + "|" + fold(n[2]) for n in nodes],
        "preds": [[p, rels.get(p, (p, 5))[0], rels.get(p, (p, 5))[1]] for p in preds],
        "classes": CLASSES,
        "edges": edges,
        "passages": plist,
        "dated": dated,
        "counts": {"people": sum(1 for n in nodes if n[0] == 0), "places": sum(1 for n in nodes if n[0] == 1),
                   "events": sum(1 for n in nodes if n[0] == 2), "relations": len(edges),
                   "passages": len(plist)},
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("/*DATA*/null", blob)
    for k, v in data["counts"].items():
        page = page.replace("{{" + k + "}}", f"{v:,}")
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(page.encode()) // 1000} kB): {data['counts']}")


if __name__ == "__main__":
    main()
