"""The observatory's view of the unified graph: nodes, links, claims and sources.

Everything is read from build/graph.ttl through site/model.py (the reader tier's loader),
so names, URLs and statuses match the reader pages. No entity ID is written here: every
entity is found by its rdf:type, and the few vocabulary terms used below are relation or
concept names from ontology/marsad.ttl, never entity IDs.

Nothing is invented. A link exists only where the graph records a claim, a participation
record, an event's place, a part-of link or a transmission link. A date exists only where
the graph records both bounds of a temporal extent. A location exists only where a place
carries a WKT point whose confidence is not "unlocated".

Output order never depends on Python's hash seed: claims are sorted, and the source,
string and report tables are numbered after sorting.
"""
from __future__ import annotations

import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
if str(SITE) not in sys.path:
    sys.path.insert(0, str(SITE))

import display  # noqa: E402
from model import MRS, Site  # noqa: E402
from rdflib import BNode, Namespace, URIRef  # noqa: E402
from rdflib.namespace import RDF, RDFS  # noqa: E402

GEO = Namespace("http://www.opengis.net/ont/geosparql#")

KIND_ORDER = ("person", "group", "place", "event", "story")
CLASSES = ("participation", "kinship", "social_political", "spatial", "transmission")

# Relation (vocabulary) names, without the rel_ prefix, whose claim says the person was
# NOT there. They never place a person in time or space.
ABSENCE_PREDICATES = {"absent_from"}

# Line class for the links that are not Assertions (they carry no relation type).
LINK_KIND_CLASS = {
    "claim.took_part": "participation",
    "claim.took_place_at": "spatial",
    "claim.part_of": "participation",
}

# Order of the generation (tabaqa) concepts, by concept name in ontology/marsad.ttl.
# The vocabulary records no order; this is the order of the generations themselves.
TABAQA_ORDER = ("sahabi", "tabii", "tabi_al_tabiin")

_POINT = re.compile(r"POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)", re.IGNORECASE)
_ISO = re.compile(r"^(-?\d{1,6})-(\d\d)-(\d\d)")


def year_value(iso: str | None, end: bool = False) -> float | None:
    """Fractional Gregorian year of a recorded bound (its position inside the year, no
    calendar conversion). An end bound of 31 December lands just before the next year."""
    if not iso:
        return None
    m = _ISO.match(iso)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    frac = (mo - 1) / 12.0 + (d - 1) / 372.0
    if end:
        frac += 1 / 372.0
    return round(y + frac, 3)


def local(iri) -> str:
    return re.split(r"[#/]", str(iri))[-1]


class Translator:
    """Reads site/observatory/i18n/en.json. A missing key raises KeyError (display.t_opt
    relies on that)."""

    def __init__(self, strings: dict):
        self.d = strings

    def __call__(self, key: str, **kw) -> str:
        s = self.d[key]
        return s.format(**kw) if kw else s


def _src_key(agent) -> tuple:
    return ("agent", agent.label, bool(agent.software))


class ObsData:
    def __init__(self, site: Site, t: Translator):
        self.site, self.g, self.t = site, site.g, t
        self.nodes: list[dict] = []
        self.index: dict[str, int] = {}
        self.links: list[dict] = []
        self.claims: list[dict] = []
        self.sources: list[dict] = []
        self.strings: list[str] = []
        self.reports: list[dict] = []
        self._reports_by_iri: dict[str, dict] = {}
        self.chains: list[dict] = []
        self._build_nodes()
        self._build_claims()
        self._build_chains()
        self._finalize()
        self._build_links()
        self._derive()

    # ------------------------------------------------------------------ helpers
    def _agent_key(self, agents):
        if not agents:
            return None
        return _src_key(sorted(agents, key=lambda a: a.label)[0])

    # ------------------------------------------------------------------ nodes
    def _build_nodes(self):
        s = self.site
        ents = []
        for kind in KIND_ORDER:
            ents.extend(s.by_kind[kind])  # A-Z within a kind, ties by ID (model.py)
        for e in ents:
            node = {
                "id": e.pid, "k": e.kind, "n": e.name, "u": s.url(e.iri),
                "cov": e.coverage,
                "rec": [_src_key(a) for a in sorted(e.agents, key=lambda a: a.label)],
            }
            if e.subtype and e.kind == "group":
                node["sub"] = e.subtype
            if e.kind == "person" and not e.prophet and display.popularize(e.scholarly) != e.scholarly:
                node["sch"] = e.scholarly
            self.index[e.iri] = len(self.nodes)
            node["_iri"] = e.iri
            node["_ent"] = e
            self.nodes.append(node)
        for node in self.nodes:
            e = node["_ent"]
            getattr(self, f"_node_{e.kind}")(node, e)

    def _extent_items(self, exts) -> list[list]:
        """[[y0, y1, text, notes]] for each recorded extent. y0/y1 are None unless both
        bounds are recorded (an open range is never placed on the time axis)."""
        out = []
        for ext in exts:
            f = display.format_extent(ext, self.t)
            y0 = year_value(ext.get("earliest"))
            y1 = year_value(ext.get("latest"), end=True)
            if y0 is None or y1 is None or y1 < y0:
                y0 = y1 = None
            item = [y0, y1, f["text"], f["notes"]]
            if item not in out:
                out.append(item)
        out.sort(key=lambda x: (x[0] is None, x[0] or 0, x[1] or 0, x[2] or ""))
        return out

    def _gaps(self, e) -> list[str]:
        return sorted(g["description"].text for g in (e.data.get("gaps") or []) if g.get("description"))

    def _node_person(self, node, e):
        d = e.data
        if d.get("tabaqa"):
            tb = self.g.value(URIRef(e.iri), MRS.tabaqa)
            node["tb"] = d["tabaqa"]
            key = local(tb) if tb is not None else ""
            node["tbk"] = key[3:] if key.startswith("tb_") else key
        if d.get("transmitter_role"):
            node["tr"] = d["transmitter_role"]
        deaths = self._extent_items(d.get("death") or [])
        if deaths:
            node["death"] = deaths
        aff = []
        for a in d.get("affiliations") or []:
            if a.get("place") and a["place"] in self.index:
                aff.append([self.index[a["place"]], a.get("type")])
        if aff:
            node["aff"] = sorted(aff, key=lambda x: (x[0], x[1] or ""))
        if self._gaps(e):
            node["gaps"] = self._gaps(e)

    def _node_group(self, node, e):
        if self._gaps(e):
            node["gaps"] = self._gaps(e)

    def _node_place(self, node, e):
        g = self.g
        pts, confs = [], set()
        for gs in g.objects(URIRef(e.iri), MRS.geometryState):
            conf = g.value(gs, MRS.locationConfidence)
            conf_key = local(conf)[3:] if conf is not None else None
            if conf is not None and self.site.vocab(conf):
                confs.add(self.site.vocab(conf))
            geom = g.value(gs, MRS.geometry)
            wkt = g.value(geom, GEO.asWKT) if geom is not None else None
            if wkt is None or conf_key == "unlocated":
                continue
            m = _POINT.search(str(wkt))
            if m:
                pt = (float(m.group(1)), float(m.group(2)), self.site.vocab(conf))
                if pt not in pts:
                    pts.append(pt)
        pts.sort(key=lambda p: (p[0], p[1], p[2] or ""))
        if len(pts) == 1:
            node["geo"] = [pts[0][0], pts[0][1], pts[0][2]]
        elif len(pts) > 1:
            node["geoMany"] = len(pts)  # several different points: none is chosen
        if confs:
            node["conf"] = sorted(confs)
        if e.arabic:
            node["ar"] = e.arabic[:2]
        types = sorted(e.data.get("types") or [])
        if types:
            node["pt"] = types
        if self._gaps(e):
            node["gaps"] = self._gaps(e)

    def _node_event(self, node, e):
        dates = self._extent_items(e.data.get("dates") or [])
        if dates:
            node["d"] = dates
        disputes = []
        for dsp in e.data.get("disputes") or []:
            disputes.append({
                "q": dsp["question"].text if dsp.get("question") else None,
                "st": dsp.get("status"),
                "pos": sorted(p["claim"].text for p in dsp.get("positions", []) if p.get("claim")),
            })
        if disputes:
            node["disp"] = sorted(disputes, key=lambda x: x["q"] or "")
        if self._gaps(e):
            node["gaps"] = self._gaps(e)

    def _node_story(self, node, e):
        d = e.data
        if d.get("number") is not None:
            node["no"] = d["number"]
        if d.get("part_number") is not None:
            node["part"] = d["part_number"]
        if d.get("part_label"):
            node["partl"] = d["part_label"]
        if d.get("citation"):
            node["cit"] = d["citation"]
        w = d.get("work")
        if w and w.get("label"):
            node["work"] = ("work", w["label"], bool(w["ai"]))
        dates = self._extent_items(d.get("dates") or [])
        if dates:
            node["d"] = dates

    # ------------------------------------------------------------------ reports
    def _report(self, rep) -> str | None:
        """A report (e.g. a Hadith) with its passage, chain and recorded gradings.
        Returns its IRI; the table is numbered in _finalize."""
        if rep is None:
            return None
        key = str(rep)
        if key in self._reports_by_iri:
            return key
        g, s = self.g, self.site
        label = s.first_lit(rep, RDFS.label)
        passage = g.value(rep, MRS.locatedIn)
        cit = g.value(passage, MRS.canonicalCitation) if passage is not None else None
        grades = []
        for ev in g.subjects(MRS.evaluationTarget, rep):
            evaluator = g.value(ev, MRS.evaluator)
            ev_label = s.first_lit(evaluator, RDFS.label) if evaluator is not None else None
            why = s.first_lit(ev, MRS.justification)
            grades.append({
                "grade": s.vocab(g.value(ev, MRS.grade)),
                "by": display.popularize(ev_label.text) if ev_label else None,
                "scheme": s.vocab(g.value(ev, MRS.gradeScheme)),
                "tradition": s.vocab(g.value(ev, MRS.tradition)),
                "why": why.text if why else None,
                "rec": self._agent_key(s.agents_of(ev)),
                "cov": s.vkey(g.value(ev, MRS.coverageState), "cs_"),
            })
        grades.sort(key=lambda x: (x["grade"] or "", x["by"] or ""))
        chain = g.value(rep, MRS.hasChain)
        self._reports_by_iri[key] = {
            "label": label.text if label else None,
            "genre": s.vocab(g.value(rep, MRS.reportGenre)),
            "asc": s.vocab(g.value(rep, MRS.terminalAscription)),
            "cit": str(cit) if cit is not None else None,
            "grades": grades,
            "chain": str(chain) if chain is not None else None,
            "rec": self._agent_key(s.agents_of(rep)),
            "cov": s.vkey(g.value(rep, MRS.coverageState), "cs_"),
        }
        return key

    # ------------------------------------------------------------------ claims
    def _build_claims(self):
        s, g = self.site, self.g
        seen, ordered = set(), []
        for iri in sorted(s.claims):
            for c in s.claims[iri]:
                if id(c) not in seen:
                    seen.add(id(c))
                    ordered.append(c)
        out = []
        for c in ordered:
            if c.subject not in self.index or c.object not in self.index:
                continue
            claim = {"s": self.index[c.subject], "o": self.index[c.object]}
            if c.kind == "assertion":
                node = URIRef(c.node)
                pk = local(g.value(node, MRS.predicate))
                pk = pk[4:] if pk.startswith("rel_") else pk
                claim.update({"k": "a", "p": c.predicate, "pk": pk,
                              "c": c.relclass or "participation", "id": local(node), "st": c.status})
            else:
                claim.update({"k": "p" if c.kind == "participation" else "l",
                              "p": self.t(c.predicate) if c.predicate_is_key else c.predicate,
                              "pk": c.predicate.split(".", 1)[-1],
                              "c": LINK_KIND_CLASS.get(c.predicate, "participation"), "st": None})
            claim["src"] = self._agent_key(c.agents)
            if c.role and c.role.text:
                claim["r"] = c.role.text
            if c.qualifiers:
                claim["q"] = sorted(c.qualifiers)
            if c.basis and c.basis.text:
                claim["b"] = c.basis.text
            if c.citation:
                claim["cit"] = c.citation
            if c.story and c.story in self.index:
                claim["sty"] = self.index[c.story]
            if c.passage:
                w = s.passage_info(URIRef(c.passage)).get("work")
                if w and w.get("label"):
                    claim["w"] = ("work", w["label"], bool(w["ai"]))
            if c.kind == "assertion":
                rep = self._report(g.value(URIRef(c.node), MRS.fromReport))
                if rep is not None:
                    claim["rep"] = rep
            out.append(claim)
        out.sort(key=self._claim_order)
        self.claims = out

    @staticmethod
    def _claim_order(x):
        return (x["s"], x["o"], x["k"], x["p"], x.get("id", ""), x.get("r", ""), x.get("b", ""), x.get("ord", 0))

    # ------------------------------------------------------------------ transmission chains
    def _build_chains(self):
        g, s = self.g, self.site
        for ch in sorted(g.subjects(RDF.type, MRS.TransmissionChain), key=str):
            links = []
            for ln in g.objects(ch, MRS.hasLink):
                fr, to = g.value(ln, MRS.fromNarrator), g.value(ln, MRS.toNarrator)
                order = g.value(ln, MRS.linkOrder)
                chk = g.value(ln, MRS.contactCheck)
                links.append({
                    "from": str(fr) if fr is not None else None, "to": str(to) if to is not None else None,
                    "order": int(str(order)) if order is not None and str(order).isdigit() else None,
                    "mode": s.vocab(g.value(ln, MRS.transmissionMode)),
                    "check": s.vocab(g.value(chk, MRS.checkResult)) if chk is not None else None,
                    "check_basis": s.vocab(g.value(chk, MRS.checkBasis)) if chk is not None else None,
                })
            links.sort(key=lambda x: (x["order"] is None, x["order"] or 0, x["from"] or "", x["to"] or ""))
            label = s.first_lit(ch, RDFS.label)
            collector = g.value(ch, MRS.collector)
            terminal = g.value(ch, MRS.terminalNarrator)
            reports = sorted(g.subjects(MRS.hasChain, ch), key=str)
            ci = len(self.chains)
            chain = {
                "label": label.text if label else None,
                "collector": self.index.get(str(collector)) if collector is not None else None,
                "terminal": self.index.get(str(terminal)) if terminal is not None else None,
                "rec": self._agent_key(s.agents_of(ch)),
                "cov": s.vkey(g.value(ch, MRS.coverageState), "cs_"),
                "rep": self._report(reports[0]) if reports else None,
                "links": [],
            }
            for ln in links:
                if ln["from"] in self.index and ln["to"] in self.index:
                    a, b = self.index[ln["from"]], self.index[ln["to"]]
                    chain["links"].append([a, b, ln["order"], ln["mode"], ln["check"], ln["check_basis"]])
                    claim = {"s": a, "o": b, "k": "t", "p": self.t("claim.transmitted_to"),
                             "pk": "transmitted_to", "c": "transmission", "st": None,
                             "src": chain["rec"], "chain": ci}
                    if ln["mode"]:
                        claim["mode"] = ln["mode"]
                    if ln["check"]:
                        claim["chk"] = ln["check"]
                        if ln["check_basis"]:
                            claim["chkb"] = ln["check_basis"]
                    if ln["order"] is not None:
                        claim["ord"] = ln["order"]
                    if chain["rep"] is not None:
                        claim["rep"] = chain["rep"]
                    self.claims.append(claim)
            self.chains.append(chain)
        self.claims.sort(key=self._claim_order)

    # ------------------------------------------------------------------ number the tables
    def _finalize(self):
        # reports, by IRI
        rep_iris = sorted(self._reports_by_iri)
        rep_ix = {iri: i for i, iri in enumerate(rep_iris)}
        self.reports = [self._reports_by_iri[iri] for iri in rep_iris]
        # sources: every agent or work key used anywhere, sorted
        keys = set()

        def visit(k):
            if k is not None:
                keys.add(k)

        for n in self.nodes:
            for k in n["rec"]:
                visit(k)
            visit(n.get("work"))
        for c in self.claims:
            visit(c.get("src"))
            visit(c.get("w"))
        for r in self.reports:
            visit(r["rec"])
            for gr in r["grades"]:
                visit(gr["rec"])
        for ch in self.chains:
            visit(ch["rec"])
        order = sorted(keys)
        six = {k: i for i, k in enumerate(order)}
        self.sources = [{"kind": k[0], "label": k[1], "ai": k[2]} for k in order]
        for n in self.nodes:
            n["rec"] = [six[k] for k in n["rec"]]
            if "work" in n:
                n["work"] = six[n["work"]]
        strings: dict[str, int] = {}
        for c in self.claims:
            if c.get("src") is not None:
                c["src"] = six[c["src"]]
            if "w" in c:
                c["w"] = six[c["w"]]
            if "rep" in c:
                c["rep"] = rep_ix[c["rep"]]
            if "b" in c:
                if c["b"] not in strings:
                    strings[c["b"]] = len(strings)
                    self.strings.append(c["b"])
                c["b"] = strings[c["b"]]
        for r in self.reports:
            r["rec"] = six[r["rec"]] if r["rec"] is not None else None
            for gr in r["grades"]:
                gr["rec"] = six[gr["rec"]] if gr["rec"] is not None else None
            r.pop("chain", None)
        for ch in self.chains:
            ch["rec"] = six[ch["rec"]] if ch["rec"] is not None else None
            ch["rep"] = rep_ix[ch["rep"]] if ch["rep"] is not None else None

    # ------------------------------------------------------------------ links
    def _build_links(self):
        groups: dict[tuple, list[int]] = defaultdict(list)
        for ci, c in enumerate(self.claims):
            a, b = sorted((c["s"], c["o"]))
            groups[(a, b, c["c"])].append(ci)
        for (a, b, cls), cis in sorted(groups.items()):
            self.links.append({"a": a, "b": b, "c": cls, "cl": cis})

    # ------------------------------------------------------------------ derived per node
    def _derive(self):
        """Dated marks, located places and story ties per node, from recorded data only."""
        n = len(self.nodes)
        self.adj: list[list[int]] = [[] for _ in range(n)]
        for li, l in enumerate(self.links):
            self.adj[l["a"]].append(li)
            if l["b"] != l["a"]:
                self.adj[l["b"]].append(li)
        for node in self.nodes:
            node["_marks"], node["_places"], node["_stories"] = [], [], []
        # events (and any dated story): their own recorded dates
        for node in self.nodes:
            if node["k"] in ("event", "story"):
                for y0, y1, text, _notes in node.get("d", []):
                    if y0 is not None:
                        node["_marks"].append([y0, y1, text, None])
        # people: dated events they took part in (absence claims excluded), and death dates
        for i, node in enumerate(self.nodes):
            if node["k"] != "person":
                continue
            seen = set()
            for li in self.adj[i]:
                for ci in self.links[li]["cl"]:
                    c = self.claims[ci]
                    other = c["o"] if c["s"] == i else c["s"]
                    if self.nodes[other]["k"] != "event" or c.get("pk") in ABSENCE_PREDICATES or other in seen:
                        continue
                    seen.add(other)
                    for y0, y1, _t, _n in self.nodes[other].get("d", []):
                        if y0 is not None:
                            node["_marks"].append([y0, y1, self.nodes[other]["n"], other])
            for y0, y1, text, _notes in node.get("death", []):
                if y0 is not None:
                    node["_marks"].append([y0, y1, text, None])
        for node in self.nodes:
            node["_marks"].sort(key=lambda m: (m[0], m[1], str(m[2]), m[3] if m[3] is not None else -1))
        # located places: an event's recorded place; a person's place claims (migrated to,
        # died at, ...) and place affiliations. Absence claims are skipped.
        for i, node in enumerate(self.nodes):
            counts: dict[int, int] = defaultdict(int)
            if node["k"] != "place":
                for li in self.adj[i]:
                    for ci in self.links[li]["cl"]:
                        c = self.claims[ci]
                        other = c["o"] if c["s"] == i else c["s"]
                        o = self.nodes[other]
                        if o["k"] != "place" or "geo" not in o or c.get("pk") in ABSENCE_PREDICATES:
                            continue
                        counts[other] += 1
                for pi, _t in node.get("aff", []):
                    if "geo" in self.nodes[pi]:
                        counts[pi] += 1
            node["_places"] = sorted(counts, key=lambda p: (-counts[p], self.nodes[p]["n"], p))
        # stories each node is tied to
        for i, node in enumerate(self.nodes):
            st = set()
            for li in self.adj[i]:
                other = self.links[li]["b"] if self.links[li]["a"] == i else self.links[li]["a"]
                if self.nodes[other]["k"] == "story" and other != i:
                    st.add(other)
            node["_stories"] = sorted(st, key=lambda x: (self.nodes[x].get("no", 9999), x))

    # ------------------------------------------------------------------ facts for the page
    def counts(self) -> dict:
        by_kind = defaultdict(int)
        for n in self.nodes:
            by_kind[n["k"]] += 1
        status = defaultdict(int)
        for c in self.claims:
            if c["k"] == "a":
                status[c["st"] or "none"] += 1
        return {
            "kinds": {k: by_kind[k] for k in KIND_ORDER},
            "nodes": len(self.nodes),
            "assertions": sum(status.values()),
            "status": dict(sorted(status.items())),
            "records": sum(1 for c in self.claims if c["k"] != "a"),
            "links": len(self.links),
            "dated_events": sum(1 for n in self.nodes if n["k"] == "event" and any(d[0] is not None for d in n.get("d", []))),
            "events": by_kind["event"],
            "dated_nodes": sum(1 for n in self.nodes if n["_marks"]),
            "tabaqa": sum(1 for n in self.nodes if n.get("tb")),
            "located": sum(1 for n in self.nodes if n["k"] == "place" and "geo" in n),
            "places": by_kind["place"],
            "chains": len(self.chains),
            "chain_links": sum(len(ch["links"]) for ch in self.chains),
            "reviewed": sum(v for k, v in status.items() if k not in ("proposed", "none", "under_review")),
        }

    def fingerprint(self) -> str:
        """A short corpus fingerprint: SHA-256 over the sorted triples that carry no
        blank node (blank-node labels change from one parse to the next)."""
        lines = sorted(f"{s.n3()} {p.n3()} {o.n3()}" for s, p, o in self.g
                       if not isinstance(s, BNode) and not isinstance(o, BNode))
        return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:12]
