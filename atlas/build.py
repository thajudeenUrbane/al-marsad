#!/usr/bin/env python3
"""Builds the Sky Atlas: the whole joined graph as one guided sky, in one page.

    .venv/bin/python atlas/build.py                 # writes atlas/index.html
    .venv/bin/python atlas/build.py --artifact OUT  # the same page without the document
                                                    # skeleton, for publishing as an Artifact

Reads build/graph-all.ttl (the joined graph of slice 11a: every corpus file, the full
Ibn Hishām layer included; runs ontology/build_graph.py if it is missing) through the
Observatory's extractor (site/observatory/obsdata.py), so every node, claim, status,
source and date is the one the reader tier and the Observatory show. Nothing about any
person is written here or in the page's code: new records become new stars on the next
build.

What the build adds, all from recorded data:
- the sky layout (layout.py): the Prophet ﷺ as the light at the centre, never a node;
  events on a spiral in the order Ibn Hishām's text tells them (the "ecliptic of the
  record"); the 50 Stories on an outer ring in reading order; everyone else settled
  by their recorded links;
- each claim's place in Ibn Hishām's text (its OpenITI milestone, read from its
  citation), each item's first mention, and where the text tells each event (the
  median milestone of the claims that cite it);
- the learning journeys of learn/journeys/, applied to this graph by learn/journeys.py;
- Arabic names from ontology/corpus/identity.csv;
- the membership lists of atlas/data/lists.json (proposed), matched by display name;
- marks the brief asks for (docs/handover/sky-guided-brief.md): opponents only where a
  claim records fighting against or opposing the Prophet ﷺ, the turning only where a
  claim carries the qualifier "accepted Islam later", and the lineage-only background.

The data is written as gzip, base64-encoded, inside the page; the page unpacks it with
the browser's DecompressionStream. One file, no external request, system fonts.
"""
from __future__ import annotations

import argparse
import base64
import csv
import gzip
import html
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SITE = ROOT / "site"
for p in (HERE, SITE / "observatory", SITE, ROOT / "learn"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from model import Site  # noqa: E402
from obsdata import KIND_ORDER, ObsData, Translator  # noqa: E402

import layout  # noqa: E402

GRAPH = ROOT / "build" / "graph-all.ttl"
OUT = HERE / "index.html"
IDENTITY = ROOT / "ontology" / "corpus" / "identity.csv"
JOURNEYS = ROOT / "learn" / "journeys"
STATIC = HERE / "static"
SIZE_LIMIT = 15_000_000  # the Artifact limit is 16 MB

GLOSS_PREFIX = "AI gloss (proposed; machine-written, not reviewed, not a translation): "
_MS = re.compile(r"OpenITI ms(\d+)")
# Predicates (without rel_) whose claims with the Prophet ﷺ make a person an opponent
# on the sky. fought_against counts in either direction; opposed only towards him.
OPPOSE_EITHER = {"fought_against"}
OPPOSE_TOWARDS = {"opposed"}
TURNED_QUALIFIER = "accepted Islam later"


def gloss_or_role(text: str | None) -> tuple[str | None, str | None]:
    if not text:
        return None, None
    if text.startswith(GLOSS_PREFIX):
        return text[len(GLOSS_PREFIX):], None
    return None, text


def split_citation(cit: str | None, prefixes: dict) -> tuple[int | None, str | None]:
    """A citation as (prefix index, rest): the edition statement is shared by
    thousands of claims, so it is written once."""
    if not cit:
        return None, None
    m = re.match(r"^(.*?\)), (vol\. .*)$", cit)
    if not m:
        return None, cit
    pre = m.group(1)
    if pre not in prefixes:
        prefixes[pre] = len(prefixes)
    return prefixes[pre], m.group(2)


def load_names_ar() -> dict[str, str]:
    out = {}
    with IDENTITY.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("name_ar"):
                out[row["canonical_id"].split(":", 1)[-1]] = row["name_ar"]
    return out


def load_lists(nodes: list[dict]) -> list[dict]:
    spec = json.loads((HERE / "data" / "lists.json").read_text(encoding="utf-8"))
    by_name = defaultdict(list)
    for i, nd in enumerate(nodes):
        if nd["k"] == "person":
            by_name[nd["n"]].append(i)
    out = []
    for ls in spec["lists"]:
        members = []
        for name in ls["members"]:
            hits = by_name.get(name, [])
            if len(hits) != 1:
                raise SystemExit(f"lists.json: {name!r} matches {len(hits)} people in the graph; it must match one")
            members.append(hits[0])
        out.append({"key": ls["key"], "m": members, "src": ls["source"], "st": spec["status"]})
    return out


def load_journeys(site: Site, index: dict[str, int], log) -> list[dict]:
    try:
        import journeys as jmod
    except ImportError as e:  # learn/ is part of the repository; say so if it is not there
        log(f"journeys skipped: {e}")
        return []
    strings = json.loads((ROOT / "learn" / "i18n" / "en.json").read_text(encoding="utf-8"))
    out = []
    for spec in jmod.load_specs(JOURNEYS):
        try:
            j = jmod.build(site, spec)
        except jmod.RuleError as e:
            log(f"journey {spec['slug']}: {e}")
            continue
        steps = [index[s.iri] for s in j.steps if s.iri in index]
        apart = [index[s.iri] for s in j.set_apart if s.iri in index]
        anchors = [index[a] for a in j.anchors if a in index]
        out.append({"key": spec["slug"], "title": strings.get(spec["title"], spec["slug"]),
                    "lead": strings.get(spec["lead"], ""), "type": spec["select"]["type"],
                    "status": spec["status"], "steps": steps, "apart": apart, "anchors": anchors})
    return out


class Sparse:
    """Columnar output: dense columns are lists, rare fields are {index: value}."""

    def __init__(self):
        self.cols: dict[str, dict] = defaultdict(dict)

    def put(self, i: int, key: str, value):
        if value is None or value == [] or value == "":
            return
        self.cols[key][i] = value

    def dense(self, n: int, key: str, default=None):
        col = self.cols.pop(key, {})
        return [col.get(i, default) for i in range(n)]

    def sparse(self):
        return {k: {str(i): v for i, v in sorted(col.items())} for k, col in sorted(self.cols.items())}


def table(values: list) -> tuple[list, dict]:
    order, ix = [], {}
    for v in values:
        if v not in ix:
            ix[v] = len(order)
            order.append(v)
    return order, ix


def payload(data: ObsData, site: Site, log) -> dict:
    nodes, claims = data.nodes, data.claims
    n = len(nodes)
    light = [i for i, nd in enumerate(nodes) if nd["k"] == "person" and nd["_ent"].prophet]
    if len(light) != 1:
        raise SystemExit(f"the light needs exactly one person recognised as the Prophet; found {len(light)}")
    light = light[0]
    names_ar = load_names_ar()

    # ---- claims: a place in the text for each, and the tables they share
    preds, pred_ix = table([(c["pk"], c["p"], c["c"]) for c in claims])
    kinds_c, kc_ix = table([c["k"] for c in claims])
    quals, q_ix = table(sorted({q for c in claims for q in c.get("q", [])}))
    prefixes: dict[str, int] = {}
    C = Sparse()
    cms = [None] * len(claims)
    first_ms: dict[int, int] = {}
    all_ms: dict[int, list] = defaultdict(list)
    for ci, c in enumerate(claims):
        m = _MS.search(c.get("cit") or "")
        if m:
            ms = int(m.group(1))
            cms[ci] = ms
            for x in (c["s"], c["o"]):
                all_ms[x].append(ms)
                if x not in first_ms or ms < first_ms[x]:
                    first_ms[x] = ms
        gloss, role = gloss_or_role(c.get("r"))
        cp, cs = split_citation(c.get("cit"), prefixes)
        C.put(ci, "g", gloss)
        C.put(ci, "r", role)
        C.put(ci, "cp", cp)
        C.put(ci, "cs", cs)
        C.put(ci, "ms", cms[ci])
        C.put(ci, "q", [q_ix[q] for q in c.get("q", [])])
        for key in ("w", "b", "rep", "chain", "mode", "chk", "chkb", "ord", "sty", "id"):
            C.put(ci, key, c.get(key))
    cl = {
        "s": [c["s"] for c in claims], "o": [c["o"] for c in claims],
        "p": [pred_ix[(c["pk"], c["p"], c["c"])] for c in claims],
        "k": [kc_ix[c["k"]] for c in claims],
        "st": [1 if c.get("st") == "proposed" else (0 if c.get("st") is None else 2) for c in claims],
        "src": [c.get("src") if c.get("src") is not None else -1 for c in claims],
        **C.sparse(),
    }

    # where the text tells each event: the median milestone of the claims that cite it
    # (an event's first mention is often an aside long before its own chapter)
    tell_ms = {i: sorted(v)[len(v) // 2] for i, v in all_ms.items() if nodes[i]["k"] == "event"}

    # ---- marks the brief asks for, each resting on recorded claims
    opp, turned = set(), set()
    has_claim, not_kin = set(), set()
    for ci, c in enumerate(claims):
        s, o, pk = c["s"], c["o"], c["pk"]
        if pk in OPPOSE_EITHER and light in (s, o) and s != o:
            opp.add(o if s == light else s)
        if pk in OPPOSE_TOWARDS and o == light and s != light:
            opp.add(s)
        if TURNED_QUALIFIER in c.get("q", []):
            for x in (s, o):
                if nodes[x]["k"] == "person" and x != light:
                    turned.add(x)
        has_claim.update((s, o))
        if c["c"] != "kinship":
            not_kin.update((s, o))
    # the background layer (F11): people the graph knows only from lineages
    background = {i for i, nd in enumerate(nodes)
                  if nd["k"] == "person" and i != light and i in has_claim and i not in not_kin
                  and not nd.get("tb") and not nd["_stories"]}

    # ---- nodes
    kinds = list(KIND_ORDER)
    covs, cov_ix = table([nd["cov"] or "" for nd in nodes])
    tbks = ["sahabi", "tabii", "tabi_al_tabiin"]
    S = Sparse()
    for i, nd in enumerate(nodes):
        e = nd["_ent"]
        S.put(i, "sch", nd.get("sch"))
        ar = (nd.get("ar") or [None])[0] if nd["k"] == "place" else names_ar.get(nd["id"])
        if nd["k"] == "place" and not ar:
            ar = names_ar.get(nd["id"])
        if ar and ar != nd["n"]:
            S.put(i, "ar", ar)
        if nd["rec"] != [0]:
            S.put(i, "rec", nd["rec"])
        if nd.get("tbk") in tbks:
            S.put(i, "tb", tbks.index(nd["tbk"]))
        S.put(i, "tr", nd.get("tr"))
        S.put(i, "d", [[a, b, t] for a, b, t, _n in nd.get("d", [])])
        S.put(i, "death", [[a, b, t] for a, b, t, _n in nd.get("death", [])])
        S.put(i, "geo", nd.get("geo"))
        S.put(i, "pt", nd.get("pt"))
        S.put(i, "no", nd.get("no"))
        S.put(i, "part", nd.get("part"))
        S.put(i, "partl", nd.get("partl"))
        S.put(i, "cit", nd.get("cit"))
        S.put(i, "work", nd.get("work"))
        S.put(i, "disp", nd.get("disp"))
        S.put(i, "gaps", nd.get("gaps"))
        S.put(i, "sub", nd.get("sub"))
        S.put(i, "ms", first_ms.get(i))
        S.put(i, "mt", tell_ms.get(i))
        S.put(i, "yr", nd["_marks"][0][0] if nd["_marks"] else None)
        S.put(i, "pl", nd["_places"][0] if nd["_places"] else None)
        S.put(i, "other", sorted(set(e.other_names or []) - {nd["n"]})[:6] if getattr(e, "other_names", None) else None)
        flags = (1 if i in opp else 0) | (2 if i in turned else 0) | (4 if i in background else 0)
        S.put(i, "f", flags or None)
    nd_out = {
        "k": [kinds.index(nd["k"]) for nd in nodes],
        "n": [nd["n"] for nd in nodes],
        "id": [nd["id"] for nd in nodes],
        "cv": [cov_ix[nd["cov"] or ""] for nd in nodes],
        **S.sparse(),
    }

    # ---- reports and chains (the evidence ladder)
    reports = [{k: v for k, v in r.items() if v not in (None, [], "")} for r in data.reports]
    chains = [{k: v for k, v in ch.items() if v not in (None, [], "")} for ch in data.chains]

    # ---- layout, lists, journeys
    sky = layout.sky(nodes, data.links, tell_ms, light, background)
    index = {nd["_iri"]: i for i, nd in enumerate(nodes)}
    lists = load_lists(nodes)
    journeys = load_journeys(site, index, log)
    counts = data.counts()
    counts["opponents"] = len(opp)
    counts["turned"] = len(turned & opp)
    counts["background"] = len(background)
    counts["in_text"] = len(first_ms)
    meta = {
        "light": light, "kinds": kinds, "cov": covs, "tb": tbks, "preds": preds, "ck": kinds_c,
        "quals": quals, "citp": [p for p, _ in sorted(prefixes.items(), key=lambda kv: kv[1])],
        "gloss_prefix": GLOSS_PREFIX, "sources": data.sources, "strings": data.strings,
        "counts": counts, "ms_max": max(first_ms.values()) if first_ms else 0,
        "ecliptic": sky["ecliptic"], "lists": lists, "journeys": journeys,
    }
    return {"meta": meta, "nodes": nd_out, "claims": cl, "reports": reports, "chains": chains,
            "pos": sky["pos"]}


def render(pl: dict, artifact: bool) -> str:
    tpl = (STATIC / "template.html").read_text(encoding="utf-8")
    css = (STATIC / "atlas.css").read_text(encoding="utf-8")
    js = "\n".join((STATIC / f).read_text(encoding="utf-8") for f in ("gl.js", "atlas.js"))
    if "</script" in js.lower() or "</style" in css.lower():
        raise ValueError("inline script or style would close its own tag")
    en = json.loads((HERE / "i18n" / "en.json").read_text(encoding="utf-8"))
    ar = json.loads((HERE / "i18n" / "ar.json").read_text(encoding="utf-8"))
    missing = sorted(set(en) - set(ar))
    if missing:
        raise SystemExit(f"ar.json lacks {len(missing)} keys, e.g. {missing[:5]}")
    land = json.loads((HERE / "data" / "land.json").read_text(encoding="utf-8"))
    raw = json.dumps(pl, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    packed = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode("ascii")
    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    values = {"CSS": css, "JS": js, "DATA": packed, "I18N_EN": dump(en), "I18N_AR": dump(ar),
              "LAND": dump(land), "RAW_BYTES": str(len(raw))}

    def sub(m):
        key = m.group(1)
        if key.startswith("t:"):
            return html.escape(en[key[2:]])
        return values[key]

    page = re.sub(r"\{\{([A-Z0-9_]+|t:[a-z0-9_.]+)\}\}", sub, tpl)
    if artifact:  # the Artifact host adds the document skeleton itself
        head = page[page.index("<head>") + 6:page.index("</head>")]
        head = re.sub(r'<meta charset="utf-8">\s*|<meta name="viewport"[^>]*>\s*', "", head)
        body = page[page.index("<body>") + 6:page.rindex("</body>")]
        page = head.strip() + "\n" + body.strip() + "\n"
    return page


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", default=str(GRAPH))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--artifact", default=None, help="also write the page without its document skeleton here")
    a = ap.parse_args(argv)
    graph = Path(a.graph)
    if not graph.exists():
        print(f"{graph} not found; running ontology/build_graph.py", file=sys.stderr)
        subprocess.run([sys.executable, str(ROOT / "ontology" / "build_graph.py")], check=True, cwd=ROOT)
    notes: list[str] = []
    t = Translator(json.loads((SITE / "observatory" / "i18n" / "en.json").read_text(encoding="utf-8")))
    site = Site(graph)
    data = ObsData(site, t)
    pl = payload(data, site, notes.append)
    page = render(pl, artifact=False)
    if len(page.encode("utf-8")) > SIZE_LIMIT:
        raise SystemExit(f"page is {len(page.encode()):,} bytes, over {SIZE_LIMIT:,}")
    Path(a.out).write_text(page, encoding="utf-8")
    c = pl["meta"]["counts"]
    print(f"wrote {a.out} ({len(page.encode()):,} bytes)")
    print(f"  {c['nodes']:,} items ({', '.join(f'{v:,} {k}' for k, v in c['kinds'].items())}); "
          f"{c['assertions']:,} claims, all {', '.join(c['status'])}")
    print(f"  opponents {c['opponents']}, of whom turned {c['turned']}; lineage-only {c['background']:,}; "
          f"named in Ibn Hisham's text {c['in_text']:,}")
    print(f"  journeys: {', '.join(f'{j['key']} ({len(j['steps'])})' for j in pl['meta']['journeys']) or 'none'}")
    for note in notes:
        print("  " + note)
    if a.artifact:
        Path(a.artifact).write_text(render(pl, artifact=True), encoding="utf-8")
        print(f"wrote {a.artifact}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
