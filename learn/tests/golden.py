"""Golden values that guard the E1 Hijrah Study page (design §3.7) and the v1 step
order of the three journeys (§3.8), recorded on the v1 engine and renderer before
learn-v2 changed either.

Only hashes and counts are stored, in golden_e1.json and golden_v1_order.json; no
entity ID is written anywhere. The functions here are the exact recipe, so a later
stage can recompute every value:

    page_sha(html)              sha256 of the page with every href and id attribute
                                value blanked and every whitespace run collapsed
    held_page(html)             the held v2 Study page (design §3.7) with the additions a
                                hold permits taken out, so that page_sha(held_page(v2))
                                must equal the v1 page_sha256: nav.journey-depths, the
                                empty s-* anchor spans, and the data-depth, data-total and
                                data-steps attributes of <article> (design §8). Base-relative
                                links need nothing: page_sha blanks every href value.
    order_facts(site, journey)  sha12 of the ordered step, set-apart and anchor pids
    content_facts(site, journey)  sha12 of what the v1 page shows of the record: the
                                ordered steps, each step's entity fields, and every
                                claim about a step or behind a reason, as sorted rows

    .venv/bin/python learn/tests/golden.py [site/dist]   prints the current values

sha12 is the design's canonical form (§3.5): NFC strings, sorted keys, compact
separators, UTF-8, the first 12 hex digits of the sha256.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEARN = HERE.parent
ROOT = LEARN.parent
E1_FILE = HERE / "golden_e1.json"
ORDER_FILE = HERE / "golden_v1_order.json"
HIJRAH = "hijrah-step-by-step"


def _nfc(obj):
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {_nfc(k): _nfc(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_nfc(v) for v in obj]
    return obj


def sha12(obj) -> str:
    raw = json.dumps(_nfc(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


_ATTR = re.compile(r'(?<=\s)(href|id)="[^"]*"')


def normalise_page(src: str) -> str:
    """The page with every href="..." and id="..." value blanked, whitespace collapsed."""
    return re.sub(r"\s+", " ", _ATTR.sub(r'\1=""', src)).strip()


def page_sha(src: str) -> str:
    return hashlib.sha256(normalise_page(src).encode("utf-8")).hexdigest()


_DEPTH_NAV = re.compile(r'<nav\b[^>]*\sclass="(?:[^"]*\s)?journey-depths(?:\s[^"]*)?"[^>]*>.*?</nav>', re.S)
_ANCHOR = re.compile(r'<span\b[^>]*\sid="s-[^"]*"[^>]*>\s*</span>')
_ARTICLE = re.compile(r"<article\b[^>]*>")
_ARTICLE_V2 = re.compile(r'\s(?:data-depth|data-total|data-steps)="[^"]*"')


def held_page(src: str) -> str:
    """A held Study page less the v2 additions that §3.7 and §8 permit on it. On a v1
    page, which has none of them, this returns the page unchanged."""
    src = _DEPTH_NAV.sub("", src)
    src = _ANCHOR.sub("", src)
    return _ARTICLE.sub(lambda m: _ARTICLE_V2.sub("", m.group(0)), src)


def _pid(site, iri: str | None) -> str | None:
    e = site.entity(iri) if iri else None
    return e.pid if e else iri


def claim_row(site, c) -> list:
    return [c.kind, _pid(site, c.subject), c.predicate, _pid(site, c.object), c.status, c.citation,
            c.basis.text if c.basis else None, c.role.text if c.role else None, sorted(c.qualifiers),
            sorted(a.label for a in c.agents), c.node.rsplit("/", 1)[-1] if c.node else None]


def entity_row(e) -> list:
    d = e.data
    return [e.kind, e.pid, e.name, e.scholarly, e.coverage, e.coverage_label, e.subtype,
            json.dumps(d.get("dates") or [], sort_keys=True), sorted(d.get("places") or []),
            d.get("number"), d.get("part_label")]


def order_facts(site, j) -> dict:
    steps = [st.entity.pid for st in j.steps]
    apart = [st.entity.pid for st in j.set_apart]
    anchors = [_pid(site, a) for a in j.anchors]
    return {"steps": len(steps), "steps_sha": sha12(steps), "apart": len(apart), "apart_sha": sha12(apart),
            "anchors": len(anchors), "anchors_sha": sha12(anchors)}


def content_facts(site, j) -> dict:
    claims = []
    for st in j.steps:
        for c in site.claims.get(st.iri, []):
            claims.append(claim_row(site, c))
        for r in st.reasons + st.links:
            for c in r.claims:
                claims.append(claim_row(site, c))
            claims.append(["reason", st.entity.pid, r.kind, _pid(site, r.other), r.word, r.label])
        claims.append(["order", st.entity.pid, st.order_note, _pid(site, st.order_ref)])
    rows = sorted(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in claims)
    about = sum(len(site.claims.get(st.iri, [])) for st in j.steps)
    return {"steps": len(j.steps), "steps_sha": sha12([st.entity.pid for st in j.steps]),
            "claims": about, "content_v1_sha": sha12({"steps": [entity_row(st.entity) for st in j.steps],
                                                      "rows": rows})}


def fingerprint(g) -> str:
    """obsdata.ObsData.fingerprint: sha256 over the sorted triples without a blank node."""
    from rdflib import BNode
    lines = sorted(f"{s.n3()} {p.n3()} {o.n3()}" for s, p, o in g
                   if not isinstance(s, BNode) and not isinstance(o, BNode))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:12]


def current(dist: Path, graph: Path = ROOT / "build" / "graph.ttl") -> dict:
    sys.path.insert(0, str(ROOT / "site"))
    sys.path.insert(0, str(LEARN))
    from model import Site
    import journeys as J
    site = Site(graph)
    built = {j.slug: j for j in J.build_all(site, J.load_specs(LEARN / "journeys"))}
    page = (Path(dist) / "learn" / HIJRAH / "index.html").read_text(encoding="utf-8")
    return {"page_sha256": page_sha(held_page(page)), "hijrah": content_facts(site, built[HIJRAH]),
            "order": {slug: order_facts(site, j) for slug, j in sorted(built.items())},
            "fingerprint": fingerprint(site.g)}


if __name__ == "__main__":
    print(json.dumps(current(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "site" / "dist"), indent=1))
