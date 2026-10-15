"""The compact index the ask engine runs on, built from build/graph.ttl.

The index is read through the site's own model (site/model.py), so an answer rests on
exactly the claims the reader pages show, with the same names and statuses. Nothing is
hard-coded about entities: everything is found by type, and vocabulary terms (relation
types, participant roles) by their ontology names.

    .venv/bin/python -m ask.index [--graph build/graph.ttl] [--out FILE]   # write the index as JSON

Shape (all lists sorted, so the same graph always gives the same file):
  entities[i]  r: "kind/payload" (the page URL path), k: kind, l: primary label as
               recorded, n: display name (site rules), sk: sort key, u: 1 when the label
               names this entity alone (so the DSL can quote it), keys: name keys,
               cov: coverage, dates / death: recorded dates (text from the site's date
               rules, bounds), places, no (story number), ai (story from an
               AI-generated document), gaps (coverage-gap notes), by (who recorded it)
  claims[j]    id, k: a (assertion) | p (participation) | l (link), s / o: entity
               numbers, p: relation key, pl: the recorded relation label, c: relation
               class, role, rk (participant role key), q: qualifiers, st: status or
               null, src / cit / sty: source note, citation, story, ai, by
  agents       who recorded entities and claims ("by" is a number into this list)
Empty claim fields are left out (a missing field reads as null, 0 or []).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import Namespace, URIRef
from rdflib.namespace import RDF, RDFS

from ask import normalise
from ask.normalise import RULES, name_tokens

ROOT = normalise.ROOT
SITE = normalise.SITE
import display  # noqa: E402  (site/display.py)
from model import Site  # noqa: E402  (site/model.py)

MRS = Namespace("https://w3id.org/marsad/core#")
GRAPH = ROOT / "build" / "graph.ttl"
KIND_ORDER = ("person", "group", "event", "story", "place")
_PAREN = re.compile(r"\(([^()]*)\)")


def _local(iri) -> str:
    return re.split(r"[#/]", str(iri))[-1]


def _site_t():
    """The site's translator, used only for the site's date wording (display.format_extent)."""
    strings = json.loads((SITE / "i18n" / "en.json").read_text(encoding="utf-8"))

    def t(key: str, **kw) -> str:
        s = strings[key]
        return s.format(**kw) if kw else s
    return t


def entity_names(site: Site, e) -> list[str]:
    """Every name the graph records for an entity, plus forms derived from them:
    the label without its parenthesised part, each parenthesised part, the part before
    a colon, the display (popular) form, the recorded kunya and laqab, Arabic names of
    places; for the Prophet (found the way the site finds him) his recorded ism and
    the aliases listed in rules.json "linking.prophet_aliases"."""
    labels = [e.scholarly] + list(e.other_labels)
    names: list[str] = []
    for label in labels:
        base = display.strip_blessing_tail(label)
        names.append(base)
        bare = _PAREN.sub(" ", base).strip(" ,")
        if bare and bare != base:
            names.append(bare)
        for inner in _PAREN.findall(base):
            if inner.strip():
                names.append(inner.strip())
        if ": " in base:
            names.append(base.split(": ", 1)[0])
    names.append(e.name)
    names.extend(e.arabic)
    if e.kind == "person":
        for form in e.data.get("name_forms", []):
            if form.get("kunya"):
                names.append(form["kunya"])
            names.extend(form.get("laqab") or [])
            if e.prophet and form.get("ism"):
                names.append(form["ism"])
        if e.prophet:
            names.extend(RULES["linking"]["prophet_aliases"])
    out: list[str] = []
    for n in names:
        n = n.strip()
        if n and n not in out:
            out.append(n)
    return out


def _span(exts: list[dict], t) -> list[dict]:
    out = []
    for x in exts:
        f = display.format_extent(x, t)
        out.append({"t": f["text"], "notes": f["notes"],
                    "s": (x.get("earliest") or "")[:10] or None,
                    "e": (x.get("latest") or "")[:10] or None})
    return out


def build(graph: Path = GRAPH) -> dict:
    site = Site(graph)
    g = site.g
    t = _site_t()

    ents = sorted(site.entities.values(),
                  key=lambda e: (KIND_ORDER.index(e.kind), display.sort_key(e.name), e.pid))
    num = {e.iri: i for i, e in enumerate(ents)}

    # name keys, and which labels name one entity alone (within the kind)
    keys_of: dict[str, list[list[str]]] = {}
    for e in ents:
        ks: list[list[str]] = []
        for n in entity_names(site, e):
            k = name_tokens(n)
            if k and k not in ks:
                ks.append(k)
        keys_of[e.iri] = ks
    owners: dict[tuple, set] = defaultdict(set)
    for e in ents:
        for k in keys_of[e.iri]:
            owners[(e.kind, tuple(k))].add(e.iri)

    entities = []
    for e in ents:
        d = {"r": f"{e.kind}/{e.pid}", "k": e.kind, "l": e.scholarly, "n": e.name,
             "sk": display.sort_key(e.name), "keys": keys_of[e.iri], "cov": e.coverage}
        lk = tuple(name_tokens(e.scholarly))
        d["u"] = 1 if owners.get((e.kind, lk)) == {e.iri} else 0
        if e.kind in ("event", "story"):
            d["dates"] = _span(e.data.get("dates", []), t)
            d["places"] = [num[p] for p in e.data.get("places", []) if p in num]
        if e.kind == "person":
            d["death"] = _span(e.data.get("death", []), t)
        if e.kind == "story":
            d["no"] = e.data.get("number")
            work = e.data.get("work") or {}
            d["ai"] = 1 if work.get("ai") else 0
        gaps = [x["description"].text for x in e.data.get("gaps", []) if x.get("description")]
        if gaps:
            d["gaps"] = gaps
        d["by"] = "; ".join(a.label for a in e.agents)
        entities.append(d)

    # participant roles by (event, participant, role label) -> role key (from the role's IRI)
    role_key: dict[tuple, str] = {}
    for ev in g.subjects(MRS.hasParticipation, None):
        for part in g.objects(ev, MRS.hasParticipation):
            who, role = g.value(part, MRS.participant), g.value(part, MRS.participantRole)
            if who is None or role is None:
                continue
            role_key[(str(ev), str(who), site.vocab(role))] = _local(role).removeprefix("role_")

    seen: set[int] = set()
    raw = []
    for cl in site.claims.values():
        for c in cl:
            if id(c) in seen or c.subject not in num or c.object not in num:
                continue
            seen.add(id(c))
            if c.kind == "assertion":
                pred = g.value(URIRef(c.node), MRS.predicate)
                p = _local(pred).removeprefix("rel_")
                pl = c.predicate
            else:
                p = c.predicate.removeprefix("claim.")
                pl = None
            role = c.role.text if c.role else None
            rk = role_key.get((c.object, c.subject, role)) if c.kind == "participation" else None
            raw.append({
                "k": {"assertion": "a", "participation": "p", "link": "l"}[c.kind],
                "s": num[c.subject], "o": num[c.object], "p": p, "pl": pl, "c": c.relclass,
                "role": role, "rk": rk, "q": list(c.qualifiers), "st": c.status,
                "src": c.basis.text if c.basis else None, "cit": c.citation,
                "sty": num.get(c.story) if c.story else None, "ai": 1 if c.ai_draft else 0,
                "by": "; ".join(a.label for a in c.agents),
                "node": c.node,
            })
    kord = {"a": 0, "p": 1, "l": 2}
    raw.sort(key=lambda c: (kord[c["k"]], entities[c["s"]]["sk"], entities[c["s"]]["r"], c["p"],
                            entities[c["o"]]["sk"], entities[c["o"]]["r"], c["role"] or "", c["node"] or "",
                            c["src"] or "", c["cit"] or ""))
    claims = []
    counter = {"p": 0, "l": 0}
    for c in raw:
        node = c.pop("node")
        if c["k"] == "a":
            c["id"] = "/".join(str(node).rsplit("/", 2)[-2:])
        else:
            counter[c["k"]] += 1
            c["id"] = f"{'participation' if c['k'] == 'p' else 'link'}/{counter[c['k']]}"
        claims.append({k: c[k] for k in ("id", "k", "s", "o", "p", "pl", "c", "role", "rk", "q", "st",
                                         "src", "cit", "sty", "ai", "by")})

    # who recorded what: one table, referenced by number; empty fields are left out
    agents = sorted({x["by"] for x in entities + claims if x["by"]})
    anum = {a: i for i, a in enumerate(agents)}
    for x in entities + claims:
        by = x.pop("by")
        if by:
            x["by"] = anum[by]
    for c in claims:
        for k in [k for k, v in c.items() if v is None or v == [] or (k == "ai" and v == 0)]:
            del c[k]

    counts = {k: sum(1 for e in entities if e["k"] == k) for k in KIND_ORDER}
    status = defaultdict(int)
    for c in claims:
        status[c.get("st") or "none"] += 1
    gaps = []
    for e in entities:
        for gap in e.get("gaps", []):
            if gap not in gaps:
                gaps.append(gap)
    body = {"entities": entities, "claims": claims, "agents": agents}
    version = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]
    return {
        "version": version,
        "counts": counts,
        "status": dict(sorted(status.items())),
        "gaps": gaps,
        "entities": entities,
        "claims": claims,
        "agents": agents,
        "norm": {"marks": normalise.MARK_CHARS, "ccc": normalise.combining_ranges(),
                 "arabic_run": display._ARABIC_RUN.pattern, "pbuh": display.PBUH_SIGN,
                 "names": normalise.names.RULES},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Write the ask index as JSON.")
    ap.add_argument("--graph", default=str(GRAPH))
    ap.add_argument("--out", default="-")
    a = ap.parse_args(argv)
    ix = build(Path(a.graph))
    text = json.dumps(ix, ensure_ascii=False, separators=(",", ":"))
    if a.out == "-":
        print(f"{len(ix['entities'])} entities, {len(ix['claims'])} claims, {len(text):,} bytes, version {ix['version']}")
    else:
        Path(a.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
