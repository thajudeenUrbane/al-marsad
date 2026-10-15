#!/usr/bin/env python3
"""
Identity audit (slice 1a): one canonical ID per person, place and event.

Reads the three Turtle files that carry entity IRIs plus the stories-50
data, and writes ontology/corpus/identity.csv, one reviewable table.

    .venv/bin/python ontology/tools/identity_audit.py            # write the CSV, print a short report
    .venv/bin/python ontology/tools/identity_audit.py --list     # also print every IRI with labels and files
    .venv/bin/python ontology/tools/identity_audit.py --check    # exit 1 if the CSV on disk differs

It edits no .ttl file and not the stories-50 build. Everything it records
is unverified data: a shared name is evidence of a possible shared identity,
never a ruling. confidence says how much inference a row rests on:

    exact        one IRI, or IRIs whose labels are identical once diacritics,
                 case, al-, ibn/b. are normalised; a stories-50 name matched
                 on that same normalised full name
    probable     several IRIs merged on a label match that needed a variant
                 (parenthetical dropped, text after a comma dropped), or a
                 stories-50 name matched through a variant or by containment
    needs-review an unresolved collision, label conflict, ambiguous match,
                 or a provisional ID the project has not yet decided

Canonical ID rule: the IRI used in the most files; on a tie the one in
thawr.ttl; then the one that carries its own definition (rdf:type); then
alphabetical. New IDs are minted from a hash of the stories-50 slug, so the
table re-creates identically on every run.
"""

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import rdflib
from rdflib import RDF, RDFS, Namespace, URIRef

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ontology" / "corpus" / "identity.csv"
STORIES = ROOT / "stories-50" / "data.json"

FILES = [  # order is the tie-break order for labels: thawr first
    ("thawr", ROOT / "ontology" / "examples" / "thawr.ttl"),
    ("generation-1", ROOT / "ontology" / "corpus" / "generation-1.ttl"),
    ("seed-incidents", ROOT / "ontology" / "corpus" / "seed-incidents.ttl"),
]
FILE_ORDER = [n for n, _ in FILES]

BASE = "https://w3id.org/marsad/id/"
KINDS = {"person": "per", "place": "plc", "event": "ev"}  # IRI path segment -> CURIE prefix
KIND_OF_PREFIX = {v: k for k, v in KINDS.items()}
MRS = Namespace("https://w3id.org/marsad/core#")
COMMON_ISM = {"abu", "umm", "abd", "abdullah", "ibn", "bint"}
COLUMNS = ["kind", "canonical_id", "preferred_name_en", "name_ar", "variant_ids",
           "stories50_names", "source_files", "confidence", "note"]


# ---------------------------------------------------------------- names

def strip_marks(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _token(t):
    if t in ("b", "bin"):
        return "ibn"
    if t == "bnt":
        return "bint"
    t = re.sub(r"[iu]llah$", "ullah", t)
    if len(t) > 3 and t.endswith("ah"):
        t = t[:-1]  # Aishah/Aisha, Hamzah/Hamza, Ruqayyah/Ruqayya
    return t


def norm(s):
    """Normalise a name: strip diacritics, hamza/ayn marks, case, al-, ibn/b."""
    s = strip_marks(s).lower()
    s = re.sub(r"[ʿʾʻʼ'’‘`]", "", s)
    s = s.replace("ﷺ", " ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks = [_token(t) for t in s.split() if t not in ("al", "el", "the")]
    return " ".join(toks)


def label_variants(label):
    """Normalised forms of one label: (full, looser forms, parenthetical contents)."""
    full = norm(label)
    bare = re.sub(r"\s*[\(\[][^)\]]*[\)\]]", "", label).strip()
    loose = []
    for v in (bare, bare.split(",")[0]):
        n = norm(v)
        if n and n != full and n not in loose:
            loose.append(n)
    inner = [norm(m) for m in re.findall(r"[\(\[]([^)\]]+)[\)\]]", label)]
    return full, loose, [n for n in inner if n and n != full]


# -------------------------------------------------------------- loading

def curie(iri):
    rest = str(iri)[len(BASE):]
    seg, payload = rest.split("/", 1)
    return f"{KINDS[seg]}:{payload}"


def kind_of(iri):
    return KIND_OF_PREFIX[curie(iri).split(":")[0]]


def is_entity(x):
    return isinstance(x, URIRef) and any(str(x).startswith(f"{BASE}{k}/") for k in KINDS)


def load_turtle():
    """-> files-per-IRI, labels-per-IRI, Arabic names per IRI, defined set, IDs seen in raw text."""
    used = defaultdict(set)
    labels = defaultdict(lambda: defaultdict(list))  # iri -> file -> [labels]
    arabic = defaultdict(set)
    defined = defaultdict(set)
    text_ids = defaultdict(set)
    for name, path in FILES:
        g = rdflib.Graph()
        g.parse(path, format="turtle")
        for s, p, o in g:
            for x in (s, o):
                if is_entity(x):
                    used[x].add(name)
        for s, _, o in g.triples((None, RDFS.label, None)):
            if is_entity(s):
                labels[s][name].append(str(o))
        for s, _, o in g.triples((None, RDF.type, None)):
            if is_entity(s):
                defined[s].add(name)
        for s, _, ph in g.triples((None, MRS.namePhase, None)):
            for _, _, n in g.triples((ph, MRS.phaseName, None)):
                if is_entity(s) and getattr(n, "language", None) == "ar":
                    arabic[s].add(str(n))
        raw = path.read_text(encoding="utf-8")
        for m in re.finditer(r"\b(per|plc|ev):([A-Za-z0-9]+)", raw):
            text_ids[name].add(f"{m.group(1)}:{m.group(2)}")
        for m in re.finditer(re.escape(BASE) + r"(person|place|event)/([A-Za-z0-9]+)", raw):
            text_ids[name].add(f"{KINDS[m.group(1)]}:{m.group(2)}")
    return used, labels, arabic, defined, text_ids


def label_list(iri, labels):
    out = []
    for name in FILE_ORDER:
        for lab in labels[iri].get(name, []):
            if lab not in out:
                out.append(lab)
    return out


# --------------------------------------------------------------- audit

def edit_distance(a, b, cap=3):
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def near_pairs(iris):
    """Pairs of IRIs whose opaque payloads differ by at most 2 edits."""
    ids = sorted(curie(i) for i in iris)
    out = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if edit_distance(a.split(":")[1], b.split(":")[1], 2) <= 2:
                out.append((a, b))
    return out


class DSU:
    def __init__(self, items):
        self.p = {i: i for i in items}

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def b62(n, length=22):
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    out = ""
    while n and len(out) < length:
        n, r = divmod(n, 62)
        out += alphabet[r]
    return out.ljust(length, "0")


def mint(prefix, key, taken_payloads):
    i = 0
    while True:
        h = hashlib.sha256(f"marsad-identity-1a|{prefix}|{key}|{i}".encode()).digest()
        payload = b62(int.from_bytes(h, "big"))
        if payload not in taken_payloads:
            return f"{prefix}:{payload}", payload
        i += 1


def build():
    used, labels, arabic, defined, text_ids = load_turtle()
    info = {}  # curie -> dict
    for iri in used:
        c = curie(iri)
        info[c] = {
            "iri": iri, "kind": kind_of(iri), "files": sorted(used[iri], key=FILE_ORDER.index),
            "labels": label_list(iri, labels), "ar": sorted(arabic.get(iri, ())),
            "defined": bool(defined.get(iri)),
        }
    report = {"info": info, "text_ids": text_ids}

    # (a) near-identical IRIs, same kind and across kinds
    same_kind, cross_kind = [], []
    for a, b in near_pairs(used):
        (same_kind if info[a]["kind"] == info[b]["kind"] else cross_kind).append((a, b))
    report["near_same_kind"], report["near_cross_kind"] = same_kind, cross_kind

    # (b) cluster IRIs of one kind that share a normalised label
    dsu = DSU(info)
    by_full = defaultdict(list)
    by_loose = defaultdict(list)
    for c, d in info.items():
        for lab in d["labels"]:
            if "unidentified" in lab.lower():
                continue  # placeholder label ("Route waypoint (unidentified)"): says nothing about identity
            full, loose, _ = label_variants(lab)
            by_full[(d["kind"], full)].append(c)
            for n in [full] + loose:
                by_loose[(d["kind"], n)].append(c)
    for members in by_full.values():
        for m in members[1:]:
            dsu.union(members[0], m)
    for members in by_loose.values():
        for m in members[1:]:
            dsu.union(members[0], m)
    clusters = defaultdict(list)
    for c in info:
        clusters[dsu.find(c)].append(c)
    report["same_label_diff_iri"] = sorted(sorted(v) for v in clusters.values() if len(v) > 1)

    def pick(members):
        return sorted(members, key=lambda c: (-len(info[c]["files"]), "thawr" not in info[c]["files"],
                                              not info[c]["defined"], c))[0]

    rows = []
    owner = {}
    collisions = defaultdict(list)  # curie -> near-identical curies that are a different entity
    for a, b in same_kind:
        if dsu.find(a) != dsu.find(b):
            collisions[a].append(b)
            collisions[b].append(a)

    for members in clusters.values():
        canon = pick(members)
        d = info[canon]
        variants = sorted(m for m in members if m != canon)
        files = sorted({f for m in members for f in info[m]["files"]}, key=FILE_ORDER.index)
        names = d["labels"] or [l for m in sorted(members) for l in info[m]["labels"]]
        ar = sorted({a for m in members for a in info[m]["ar"]})
        row = {
            "kind": d["kind"], "canonical_id": canon, "preferred_name_en": names[0] if names else "",
            "name_ar": ";".join(ar), "variant_ids": ";".join(variants), "stories50_names": "",
            "source_files": ";".join(files), "confidence": "exact", "_notes": [],
            "_members": members,
        }
        all_labels = sorted({l for m in members for l in info[m]["labels"]})
        if len(members) > 1:
            row["confidence"] = "probable"
            row["_notes"].append("merged on shared normalised label: " + "; ".join(
                f"{m} = {' / '.join(info[m]['labels']) or '(no label)'}" for m in sorted(members)))
        elif len(all_labels) > 1:
            if len({norm(l) for l in all_labels}) > 1:
                row["confidence"] = "needs-review"
                row["_notes"].append("label differs between files for the same IRI: " + " | ".join(all_labels))
            else:
                row["_notes"].append("label spelling differs between files: " + " | ".join(all_labels))
        if any("unidentified" in l.lower() for l in all_labels):
            row["confidence"] = "needs-review"
            row["_notes"].append("placeholder label, never merged on name: " + " | ".join(all_labels))
        if not all_labels:
            row["confidence"] = "needs-review"
            row["_notes"].append("no label in any file")
        for m in members:
            owner[m] = row
        rows.append(row)

    for a, others in collisions.items():
        row = owner[a]
        row["confidence"] = "needs-review"
        row["_notes"].append(f"IRI nearly identical to {', '.join(sorted(others))}, which is a different entity "
                             "by label; do not merge or trim IDs")
    return report, rows, owner, info, dsu


# ----------------------------------------------------------- stories-50

def stories_rows(rows, info):
    d = json.loads(STORIES.read_text(encoding="utf-8"))
    raw_by_name = defaultdict(list)
    for raw, name in d["merges"]:
        raw_by_name[name].append(raw)
    split_raw = {n: raw for raw, names in d["splits"] for n in names}

    person_rows = [r for r in rows if r["kind"] == "person"]
    idx_full, idx_loose, tok_sets = defaultdict(list), defaultdict(list), []
    row_labels = {}
    for r in person_rows:
        row_labels[id(r)] = sorted({l for m in r["_members"] for l in info[m]["labels"]})
        for lab in row_labels[id(r)]:
            full, loose, inner = label_variants(lab)
            idx_full[full].append(r)
            for n in loose + inner:
                idx_loose[n].append(r)
            tok_sets.append((set(full.split()), r))

    ism_count_stories = defaultdict(int)
    for p in d["people"]:
        ism_count_stories[label_variants(p["name"])[0].split()[0]] += 1
    ism_count_rows = defaultdict(int)
    for r in person_rows:
        for ism in {label_variants(l)[0].split()[0] for l in row_labels[id(r)]}:
            ism_count_rows[ism] += 1

    taken = {c.split(":")[1] for c in info}
    new_rows, mapped = [], defaultdict(list)
    for p in d["people"]:
        forms = [p["name"]] + raw_by_name.get(p["name"], [])
        names = list(dict.fromkeys(forms + [a for a in p["aka"] if a not in forms]))
        mine_full, mine_loose, mine_inner = label_variants(p["name"])
        cands = {}  # id(row) -> (tier, row)
        for r in idx_full.get(mine_full, []):
            cands.setdefault(id(r), (1, r))
        if not cands:  # variants of the stories name against variants of the Turtle labels
            keys = [mine_full] + mine_loose + mine_inner + [label_variants(a)[0] for a in p["aka"]]
            for k in keys:
                for r in idx_full.get(k, []) + idx_loose.get(k, []):
                    cands.setdefault(id(r), (2, r))
        if not cands:  # containment: all tokens of the shorter name inside the longer, 2+ tokens
            mine = set(mine_full.split())
            for toks, r in tok_sets:
                short, long_ = (mine, toks) if len(mine) <= len(toks) else (toks, mine)
                if len(short) >= 2 and short <= long_ and ("ibn" not in short or len(short) >= 3):
                    cands.setdefault(id(r), (3, r))
        if len(cands) == 1:
            tier, r = next(iter(cands.values()))
            mapped[id(r)].append((p, names, tier))
            continue
        notes = []
        if len(cands) > 1:
            notes.append("ambiguous, not mapped: could be " + "; ".join(sorted(
                f"{r['canonical_id']} {r['preferred_name_en']}" for _, r in cands.values())))
        else:  # no match: a distinctive first name shared with exactly one Turtle person, for a human to judge
            ism = mine_full.split()[0]
            if ism not in COMMON_ISM and ism_count_stories[ism] == 1:
                same = [r for r in person_rows if ism_count_rows[ism] == 1
                        and any(label_variants(l)[0].split()[:1] == [ism] for l in row_labels[id(r)])]
                for r in same:
                    notes.append(f"shares the first name '{ism}' with {r['canonical_id']} {r['preferred_name_en']}; "
                                 "a rare first name; may or may not be the same person, not merged")
        cid, payload = mint("per", p["id"], taken)
        taken.add(payload)
        if len(names) > 1:
            notes.append("name forms merged by stories-50 build.py ALIASES/aka: " + " / ".join(names))
        if p["name"] in split_raw:
            notes.append(f"split out of the stories-50 string \"{split_raw[p['name']]}\" by build.py SPLITS")
        needs = any(n.startswith(("ambiguous", "shares the first name")) for n in notes)
        conf = "needs-review" if needs else ("probable" if notes else "exact")
        new_rows.append({
            "kind": "person", "canonical_id": cid, "preferred_name_en": p["name"], "name_ar": "",
            "variant_ids": "", "stories50_names": ";".join(names), "source_files": "stories-50",
            "confidence": conf, "_notes": ["new ID; no match in the three Turtle files"] + notes,
        })

    for r in rows:  # attach mapped stories people to their Turtle rows
        hits = mapped.get(id(r))
        if not hits:
            continue
        allnames = list(dict.fromkeys(n for _, names, _ in hits for n in names))
        r["stories50_names"] = ";".join(allnames)
        r["source_files"] += ";stories-50"
        worst = max(t for _, _, t in hits)
        if worst > 1:
            if r["confidence"] == "exact":
                r["confidence"] = "probable"
            r["_notes"].append("stories-50 name matched through a " + ("name variant" if worst == 2 else "contained name")
                               + ": " + " / ".join(allnames))
        if len(hits) > 1:
            r["confidence"] = "needs-review"
            r["_notes"].append("more than one stories-50 person maps to this ID: " + ", ".join(p["name"] for p, _, _ in hits))

    for g in sorted(d["groups"], key=str.lower):
        cid, payload = mint("grp", norm(g), taken)
        taken.add(payload)
        new_rows.append({
            "kind": "group", "canonical_id": cid, "preferred_name_en": g, "name_ar": "", "variant_ids": "",
            "stories50_names": g, "source_files": "stories-50", "confidence": "needs-review",
            "_notes": ["stories-50 group, not a person; no grp: prefix exists in the Turtle files, so this ID is provisional"],
        })
    return new_rows, d


def finish(rows):
    order = {"person": 0, "place": 1, "event": 2, "group": 3}
    rows = sorted(rows, key=lambda r: (order[r["kind"]], r["preferred_name_en"].lower(), r["canonical_id"]))
    out = []
    for r in rows:
        r = dict(r)
        r["note"] = " | ".join(r.get("_notes", []))
        out.append({c: r[c] for c in COLUMNS})
    return out


def to_csv(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true", help="print every IRI with labels and files")
    ap.add_argument("--check", action="store_true", help="exit 1 if identity.csv is out of date")
    args = ap.parse_args()

    report, ttl_rows, owner, info, dsu = build()
    new_rows, sdata = stories_rows(ttl_rows, info)
    final = finish(ttl_rows + new_rows)

    # every IRI exactly once, every stories-50 person exactly once
    seen = [r["canonical_id"] for r in final] + [v for r in final for v in r["variant_ids"].split(";") if v]
    assert len(seen) == len(set(seen)), "an ID appears twice"
    assert set(info) <= set(seen), "an IRI is missing from the table"
    story_names = [p["name"] for p in sdata["people"]]
    per_hits = defaultdict(int)
    for r in final:
        if r["kind"] == "person":
            for n in r["stories50_names"].split(";"):
                if n in story_names:
                    per_hits[n] += 1
    assert all(per_hits[n] == 1 for n in story_names), "a stories-50 person is missing or doubled"
    assert len(story_names) == len(sdata["people"]) == len(set(story_names))

    text = to_csv(final)
    if args.check:
        same = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("identity.csv is up to date" if same else "identity.csv differs from a fresh run")
        sys.exit(0 if same else 1)
    OUT.write_text(text, encoding="utf-8")

    if args.list:
        for c in sorted(info, key=lambda c: (info[c]["kind"], c)):
            d = info[c]
            print(f"{c}  [{','.join(d['files'])}]  {' | '.join(d['labels']) or '(no label)'}")
        print()

    count = lambda kind: sum(1 for d in info.values() if d["kind"] == kind)
    k = lambda kind: sum(1 for r in final if r["kind"] == kind)
    conf = lambda v: sum(1 for r in final if r["confidence"] == v)
    print(f"IRIs found: {len(info)} (person {count('person')}, place {count('place')}, event {count('event')})")
    print(f"rows: {len(final)} (person {k('person')}, place {k('place')}, event {k('event')}, group {k('group')})")
    print(f"confidence: exact {conf('exact')}, probable {conf('probable')}, needs-review {conf('needs-review')}")
    print(f"IRI merges (same label, different IRI): {len(report['same_label_diff_iri'])} clusters")
    for grp in report["same_label_diff_iri"]:
        print("   ", " = ".join(grp), "::", info[grp[0]]["labels"][:1])
    print(f"near-identical IRIs, same kind: {len(report['near_same_kind'])} pairs")
    for a, b in report["near_same_kind"]:
        same = dsu.find(a) == dsu.find(b)
        print(f"    {a} ~ {b}  {'SAME entity (drift)' if same else 'DIFFERENT entities (collision)'}: "
              f"{(info[a]['labels'] or ['?'])[0]} / {(info[b]['labels'] or ['?'])[0]}")
    print(f"near-identical payloads across kinds: {len(report['near_cross_kind'])} pairs")
    ids_in_text = {i for s in report["text_ids"].values() for i in s}
    print(f"IDs seen in file text but not in the parsed graph: {len(ids_in_text - set(info))}")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
