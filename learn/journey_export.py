#!/usr/bin/env python3
"""marsad-journey v1: every journey resolved into versioned, byte-stable JSON (design §7, §9-§11).

    .venv/bin/python learn/journey_export.py --graph build/graph-all.ttl --out DIR [--part-budget N] [--facade]
    .venv/bin/python learn/journey_export.py --lock

In process:
    resolve(site, journey, strings)       one journey, unsplit, as a dict
    resolve_all(site, folder=None)        every journey in learn/journeys, split into parts, and
                                          written to `folder` when one is given
    source_line(claim, depth, passages, t)  the one source-line function (design §7.2)
    atlas_projection(journey, strings)    the record the Sky Atlas builds from the v1 facade
    facade_lock()                         what learn/facade.lock must hold (design §11)

The contract is learn/FORMAT.md. Nothing here asserts anything: every sentence a page
can show is an i18n template key bound to claim IDs, and every value is recorded data
(names, labels, literals, citations, dates, counts) or a rule's own words. No entity ID
is written here; every entity comes from the graph through site/model.py, as the reader
pages do. Every file is canonical JSON (journeys.canonical) plus a newline: sorted keys,
lists in a fixed order whose ties end in a pid or a claim ID, no timestamps. Site.entities
is never iterated.

Software never writes a status, an approval or a story-mode decision: the export reads
the rule files and the list file, and writes only into the folder it is given (never
into learn/journeys/ or learn/lists/), plus learn/facade.lock with --lock.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
import weakref
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SITE = ROOT / "site"
for _p in (str(SITE), str(HERE)):
    if _p not in sys.path:
        sys.path.append(_p)   # appended: an importer's own modules keep their place on the path

from rdflib import BNode, Namespace, URIRef  # noqa: E402
from rdflib.namespace import RDFS, SKOS  # noqa: E402

import display  # noqa: E402
import journeys as J  # noqa: E402
import practice  # noqa: E402
from model import MRS, Site  # noqa: E402

FORMAT = "marsad-journey"
INDEX_FORMAT = "marsad-journeys"
PART_FORMAT = "marsad-journey-part"
RESEARCH_FORMAT = "marsad-journey-research"
PAGES_FORMAT = "marsad-learn-pages"
VERSION = 1
PART_BUDGET = 150_000                   # bytes per part and per research file (design §10)
DEPTHS = ("discover", "study", "research")
PUBLIC_MODES = ("all", "accepted")
EXPORT_MARKER = ".marsad-journey-export"
LOCK_FILE = HERE / "facade.lock"
LOCK_MESSAGE = ("The Atlas reads this. Rebuild atlas/index.html (atlas/build.py on build/graph-all.ttl) "
                "and run learn/journey_export.py --lock.")
_PROTECTED = tuple(HERE / folder for folder in ("journeys", "lists"))   # software never writes here
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
_POINT = re.compile(r"POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)", re.IGNORECASE)

STATUSES = ("proposed", "under_review", "accepted", "rejected", "superseded")
NOT_SHOWN = J.NOT_SHOWN                 # never Discover-eligible, never counted for a group
CAUTION = ("rejected", "superseded", "under_review", "proposed", "accepted")   # several statuses: the first
GLOSS_PREFIX = "AI gloss ("             # an assertion comment that is an AI gloss (design §7.0)
_GLOSS_LABEL = re.compile(r"^AI gloss \([^)]*\):\s*")
VIEW_VOCABULARY = ("sky", "stories", "time", "map", "globe", "book", "chains", "lineage")
CLAIM_PREFIXES = ("assertion/", "participation/", "link/")

DEPTH_POLICY = {
    "discover": {"status": False, "draft_note": False, "coverage_state": False, "accepted_share": False,
                 "source": "citation_short", "claims": "discover_flag_only", "basis": False, "recorded_by": False,
                 "notes": False, "gloss": False, "claim_ids": False, "order_notes": False, "rejected": False,
                 "ai_document_label": True, "narration": 3, "prompts": 1, "claim_list": 0, "next": 3},
    "study": {"status": True, "draft_note": True, "coverage_state": True, "accepted_share": True,
              "source": "full", "claims": "all", "basis": True, "recorded_by": True, "notes": True, "gloss": False,
              "claim_ids": False, "order_notes": True, "rejected": True, "ai_document_label": True,
              "narration": 6, "prompts": None, "claim_list": 40, "next": None},
    "research": {"status": True, "draft_note": True, "coverage_state": True, "accepted_share": True,
                 "source": "full", "claims": "all", "basis": True, "recorded_by": True, "notes": True, "gloss": True,
                 "claim_ids": True, "order_notes": True, "rejected": True, "ai_document_label": True,
                 "narration": 80, "prompts": None, "claim_list": 80, "next": None},
}
CLAIM_CAP = DEPTH_POLICY["research"]["claim_list"]       # claims kept per events or stories step
NARRATION_CAP = DEPTH_POLICY["research"]["narration"]    # narration items kept per step

# Narration (design §7.1): the order of predicate keys, then the templates. Every template
# is attributive: it says what the record says, never a verdict.
NARRATION_ORDER = ("rel_dated", "took_place_at", "rel_occurred_at", "part_of", "rel_part_of", "rel_led",
                   "rel_sheltered_at", "took_part", "rel_participated_in", "rel_present_at", "rel_witnessed",
                   "rel_absent_from", "rel_preceded", "rel_followed", "rel_fought_alongside", "rel_fought_against",
                   "rel_died_during")
NARRATION_TEMPLATES = {
    "took_part": "learn.narr.took_part", "rel_participated_in": "learn.narr.took_part",
    "rel_led": "learn.narr.rel_led", "rel_present_at": "learn.narr.rel_present_at",
    "rel_witnessed": "learn.narr.rel_witnessed", "rel_absent_from": "learn.narr.rel_absent_from",
    "part_of": "learn.narr.part_of", "rel_part_of": "learn.narr.part_of",
    "took_place_at": "learn.narr.took_place_at", "rel_occurred_at": "learn.narr.took_place_at",
    "rel_sheltered_at": "learn.narr.rel_sheltered_at", "rel_preceded": "learn.narr.rel_preceded",
    "rel_followed": "learn.narr.rel_followed", "rel_died_during": "learn.narr.rel_died_during",
}
NARR_ROLE = "learn.narr.took_part_role"
NARR_DATED = "learn.narr.rel_dated"
NARR_SIDE = {"rel_fought_alongside": "learn.narr.rel_fought_alongside",
             "rel_fought_against": "learn.narr.rel_fought_against"}
NARR_STORY = "learn.narr.story"
NARR_MARKER = "learn.narr.marker"
NARR_DEFAULT = "learn.narr.default"
NARR_DEFAULT_TEXT = "learn.narr.default_text"

# Prompts (design §7.3): ungraded, any status, each answered by claims or a link.
PROMPTS = {"event_who": "learn.prompt.event_who", "event_when": "learn.prompt.event_when",
           "event_where": "learn.prompt.event_where", "person_elsewhere": "learn.prompt.person_elsewhere",
           "person_contrary": "learn.prompt.person_contrary", "story_names": "learn.prompt.story_names"}
WHO_PKS = ("took_part", "rel_participated_in", "rel_led", "rel_present_at", "rel_witnessed")
WHERE_PKS = ("took_place_at", "rel_occurred_at")
NEXT = {"page": "learn.next.page", "also_in": "learn.next.also_in", "study": "learn.next.study"}
CHECK = {"miss": "learn.check.not_both", "see": "learn.check.see_record"}

# Interface texts the export names for its consumers (index.json "texts").
TEXTS = {"narration_more": "learn.narr.more", "no_work": "learn.discover.no_work",
         "prompt_note": "learn.prompt.note", "gloss_label": "learn.gloss.label",
         "ai_document": "learn.source.ai_document", "ai_source_note": "learn.ai_source_note",
         "ai_note": "learn.ai_note", "marker": NARR_MARKER, "group_against": "learn.group.against",
         "group_against_lead": "learn.group.against_lead", "undated": "learn.sort.undated",
         "source_label": "claim.source", "recorded_by": "claim.recorded_by", "not_recorded": "common.not_recorded"}
SORTS = {"default": "learn.sort.default", "az": "learn.sort.az", "links": "learn.sort.links"}
ORDER_KEYS = {"recorded": "learn.order.recorded", "prophet_first_then_name": "learn.order.prophet_first_then_name",
              "name": "learn.order.name", "e3": "learn.order.e3", "story": "learn.order.story"}
E3_TEXT = {"pending": "learn.order.e3_pending", "sources": "learn.order.e3_sources", "links": "learn.order.e3_links",
           "lists": "learn.order.e3_lists", "no_last": "learn.order.e3_no_last"}
GROUP_SIDE = "learn.rule.group_side"
SIDE_PKS = tuple(sorted(NARR_SIDE))


# --------------------------------------------------------------------------- small helpers
def local(iri) -> str:
    return re.split(r"[#/]", str(iri))[-1]


def exact_status(statuses: list[str]) -> str | None:
    """The claim's recorded status, never folded. A claim recorded with several statuses
    gives the most cautious of them here (CAUTION order); the full list goes in "statuses"."""
    if not statuses:
        return None
    if len(statuses) == 1:
        return statuses[0]
    return next((s for s in CAUTION if s in statuses), statuses[0])


def blob(obj) -> bytes:
    """A file's bytes: the canonical form plus a final newline."""
    return J.canonical(obj) + b"\n"


def public_mode() -> str:
    """display.PUBLIC_MODE once reader-r3 adds it, else $MARSAD_PUBLIC_MODE, else "all"."""
    mode = getattr(display, "PUBLIC_MODE", None) or os.environ.get("MARSAD_PUBLIC_MODE") or "all"
    if mode not in PUBLIC_MODES:
        raise J.RuleError(f"public mode {mode!r} must be one of {PUBLIC_MODES}")
    return mode


def fingerprint(g) -> str:
    """The Atlas's corpus fingerprint, reproduced exactly (obsdata.ObsData.fingerprint):
    sha256 over the sorted N3 lines of every triple without a blank node, 12 hex digits.
    It cannot see blank-node data (participations, roles, relative anchors); content_sha can."""
    lines = sorted(f"{s.n3()} {p.n3()} {o.n3()}" for s, p, o in g
                   if not isinstance(s, BNode) and not isinstance(o, BNode))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:12]


def graph_info(site: Site, graph_file=None) -> dict:
    name = None
    if graph_file is not None:
        p = Path(graph_file)
        try:
            name = p.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            name = p.name
    return {"file": name, "fingerprint": fingerprint(site.g), "triples": len(site.g)}


def _table(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


class Translator:
    """t(key, **kw) over learn keys first, then the site's; a missing key raises KeyError
    (display.t_opt relies on that)."""

    def __init__(self, *tables: dict):
        self.tables = tables

    def raw(self, key: str) -> str:
        for table in self.tables:
            if key in table:
                return table[key]
        raise KeyError(key)

    def __call__(self, key: str, **kw) -> str:
        s = self.raw(key)
        return s.format(**kw) if kw else s


def translators(i18n: dict | None = None) -> dict:
    """{"en": Translator, "ar": Translator} over the learn and site strings."""
    i18n = J.load_i18n() if i18n is None else i18n
    return {lang: Translator(i18n.get(lang) or {}, _table(SITE / "i18n" / f"{lang}.json")) for lang in ("en", "ar")}


# --------------------------------------------------------------------------- the source line (design §7.2)
_LOCATOR = re.compile(r"(?:vol\. \d+, )?pp?\. \d+(?:[–-]\d+)?|Part \d+, story \d+")
_PARENS = re.compile(r"\s*\([^()]*\)")


def short_citation(cite: str) -> str:
    """Discover's short form: the work and its first locator ("vol. N, p. N", "pp. N–N" or
    "Part N, story N"), with parenthesised remarks left out and everything after the first
    ";" cut. A citation without such a locator keeps its words up to the first ";"."""
    text = cite
    while _PARENS.search(text):
        text = _PARENS.sub("", text)
    text = re.sub(r"[()]", "", text.split(";", 1)[0]).strip()
    m = _LOCATOR.search(text)
    if not m:
        return text
    work = text[:m.start()].rstrip(" ,")
    return f"{work}, {m.group(0)}" if work else m.group(0)


def short_matches(cite: str) -> bool:
    """True when the citation has a locator that the short form keeps."""
    text = cite
    while _PARENS.search(text):
        text = _PARENS.sub("", text)
    return bool(_LOCATOR.search(text.split(";", 1)[0]))


def source_line(claim: dict, depth: str, passages: dict, t) -> str | None:
    """The source text of an exported claim at a depth. Discover: the short citation, and
    only for a Discover-eligible claim (None otherwise: there is no fallback there). Study
    and Research: the full citation, else the recorded basis, else who recorded it, else
    "not yet recorded". A claim from an AI-generated document carries the AI-document
    label at every depth. `t(key, **kw)` is the translator (Translator, or the renderer's)."""
    p = passages.get(claim.get("passage") or "") or {}
    if depth == "discover":
        if not claim.get("discover") or not p.get("short"):
            return None
        text = p["short"]
    elif p.get("cite"):
        text = p["cite"]
    elif claim.get("basis"):
        text = display.honour(claim["basis"])
    elif claim.get("recorded_by"):
        text = t("claim.recorded_by", value="; ".join(a["label"] for a in claim["recorded_by"]))
    else:
        text = t("common.not_recorded")
    if claim.get("ai_document"):
        text = t("learn.source.ai_document", source=text)
    return text


# --------------------------------------------------------------------------- claim IDs (design §10 references)
_INDEX: "weakref.WeakKeyDictionary[Site, ClaimIndex]" = weakref.WeakKeyDictionary()


class ClaimIndex:
    """A stable ID for every claim of a Site: "assertion/{local name}" (the Atlas's ObsData
    claim id), "participation/{event pid}/{person pid}/{role local or none}" and
    "link/{pk}/{subject pid}/{object pid}". Built once per Site, in sorted order."""

    def __init__(self, site: Site):
        self.site = site
        self.cid: dict[int, str] = {}
        self.claim: dict[str, object] = {}
        self.role: dict[str, str | None] = {}
        roles = self._roles()
        used: dict[tuple[str, str], set] = {}
        pending = []
        for iri in sorted(site.claims):
            for c in site.claims[iri]:
                if id(c) not in self.cid:
                    self.cid[id(c)] = ""
                    pending.append(c)
        for c in pending:
            role = None
            if c.kind == "assertion":
                cid = "assertion/" + local(c.node)
            elif c.kind == "participation":
                key = (c.object, c.subject)
                want = c.role.text if c.role else None
                taken = used.setdefault(key, set())
                cands = [r for r in roles.get(key, []) if self._label(r) == want and r not in taken] or [None]
                role = cands[0]
                taken.add(role)
                cid = f"participation/{self.pid(c.object)}/{self.pid(c.subject)}/{local(role) if role else 'none'}"
            else:
                cid = f"link/{c.predicate.split('.', 1)[-1]}/{self.pid(c.subject)}/{self.pid(c.object)}"
            base, n = cid, 1
            while cid in self.claim:
                n += 1
                cid = f"{base}~{n}"
            self.cid[id(c)] = cid
            self.claim[cid] = c
            self.role[cid] = role

    def _roles(self) -> dict[tuple[str, str], list[str | None]]:
        g = self.site.g
        out: dict[tuple[str, str], set] = {}
        for ev in sorted({str(s) for s in g.subjects(MRS.hasParticipation, None) if isinstance(s, URIRef)}):
            for part in g.objects(URIRef(ev), MRS.hasParticipation):
                who = g.value(part, MRS.participant)
                if who is None:
                    continue
                role = g.value(part, MRS.participantRole)
                out.setdefault((ev, str(who)), set()).add(str(role) if role is not None else None)
        return {k: sorted(v, key=lambda r: (r is None, r or "")) for k, v in out.items()}

    def _label(self, role: str | None) -> str | None:
        return self.site.vocab(URIRef(role)) if role else None

    def pid(self, iri: str) -> str:
        e = self.site.entity(iri)
        return e.pid if e is not None else local(iri)

    def id_of(self, c) -> str:
        return self.cid[id(c)]


def claim_index(site: Site) -> ClaimIndex:
    if site not in _INDEX:
        _INDEX[site] = ClaimIndex(site)
    return _INDEX[site]


# --------------------------------------------------------------------------- needs: what a step refers to
class Needs:
    """The claims, entities, passages and terms a piece of the export refers to."""

    def __init__(self):
        self.claims: set[str] = set()
        self.entities: set[str] = set()
        self.passages: set[str] = set()
        self.terms: set[str] = set()

    def update(self, other: "Needs"):
        self.claims |= other.claims
        self.entities |= other.entities
        self.passages |= other.passages
        self.terms |= other.terms


# --------------------------------------------------------------------------- the resolver
class Resolver:
    """Resolves built journeys (journeys.Journey) into marsad-journey dicts. One per Site."""

    def __init__(self, site: Site, *, i18n: dict | None = None, lists_root=None, bank: list | None = None,
                 graph: dict | None = None, mode: str | None = None):
        self.site = site
        self.g = site.g
        self.ix = claim_index(site)
        self.i18n = J.load_i18n() if i18n is None else i18n
        self.t = translators(self.i18n)
        self.lists_root = lists_root
        self.bank = practice.bank(site.g) if bank is None else bank
        self.graph = graph or graph_info(site)
        self.mode = mode or public_mode()
        self.keys: set[str] = set()          # every i18n key the export references
        self._ref_iri: dict[str, str] = {}
        self._claims: dict[str, dict] = {}
        self._glosses: dict[str, str] = {}
        self._passages: dict[str, dict] = {}
        self._entities: dict[str, dict] = {}
        self._terms: dict[str, dict] = {}
        self._claim_needs: dict[str, Needs] = {}
        self._kinship: dict[str, bool] = {}
        self._jl = None
        self._accept = None
        self.entity_index: dict[str, list] = {}   # IRI -> [(slug, n)], for next.also_in
        self.stop_urls: dict[str, dict] = {}       # slug -> {IRI: {depth: url}}
        self.doors: dict[str, str] = {}

    # ------------------------------------------------------------------ keys and refs
    def k(self, key: str) -> str:
        self.keys.add(key)
        return key

    def has(self, key: str) -> bool:
        try:
            self.t["en"].raw(key)
        except KeyError:
            return False
        return True

    def ref(self, iri: str) -> str:
        e = self.site.entity(iri)
        r = f"{e.kind}/{e.pid}" if e is not None else f"node/{local(iri)}"
        self._ref_iri.setdefault(r, iri)
        return r

    def cid(self, c) -> str:
        return self.ix.id_of(c)

    def statuses(self, c) -> list[str]:
        return sorted(J.claim_statuses(self.site, c))

    def eligible(self, c) -> bool:
        """Discover-eligible (design §7.0): a citation (a work and a locator), and no rejected
        or superseded status; in accepted mode, also the status accepted."""
        if not c.citation:
            return False
        st = self.statuses(c)
        if set(st) & set(NOT_SHOWN):
            return False
        return not (self.mode == "accepted" and st != ["accepted"])

    def jl(self):
        if self._jl is None:
            import journey_lists
            self._jl = journey_lists
            self._accept = journey_lists.acceptance_events(self.site)
        return self._jl

    # ------------------------------------------------------------------ claims
    def pk(self, c) -> str:
        if c.kind == "assertion":
            return local(self.g.value(URIRef(c.node), MRS.predicate) or "")
        if c.kind == "participation":
            return "took_part"
        return c.predicate.split(".", 1)[-1]

    def _lits(self, node, prop) -> list[str]:
        out = [(o.language != "en", str(o)) for o in self.g.objects(node, prop) if hasattr(o, "language")]
        return [text for _, text in sorted(out)]

    def claim(self, cid: str) -> dict:
        """The exported record of one claim (design §10 Claim), built once."""
        if cid in self._claims:
            return self._claims[cid]
        c = self.ix.claim[cid]
        needs = Needs()
        pk = self.pk(c)
        needs.terms.add(f"pk:{pk}")
        rec = {"kind": c.kind, "pk": pk, "s": self.ref(c.subject)}
        needs.entities.add(rec["s"])
        if c.literal is not None:
            rec["text"] = {"value": c.literal.text, "lang": c.literal.lang}
        else:
            rec["o"] = self.ref(c.object)
            needs.entities.add(rec["o"])
        st = self.statuses(c)
        rec["status"] = exact_status(st)
        if len(st) > 1:
            rec["statuses"] = st
        rec["discover"] = self.eligible(c)
        if c.passage:
            p = "passage/" + local(c.passage)
            rec["passage"] = p
            needs.passages.add(p)
            self.passage(p, c.passage, needs)
        agents = sorted({(a.label, bool(a.software)) for a in c.agents})
        if agents:
            rec["recorded_by"] = [{"label": label, "software": sw} for label, sw in agents]
        if any(sw for _, sw in agents):
            rec["software"] = True
        if c.ai_draft:
            rec["ai_document"] = True
        if c.kind == "assertion":
            node = URIRef(c.node)
            basis = self._lits(node, MRS.nonReportBasis)
            if basis:
                rec["basis"] = basis[0]
            comments = self._lits(node, RDFS.comment)
            glosses = [x for x in comments if x.startswith(GLOSS_PREFIX)]
            notes = [x for x in comments if not x.startswith(GLOSS_PREFIX)]
            if glosses:
                self._glosses[cid] = "\n".join(_GLOSS_LABEL.sub("", x, count=1) if _GLOSS_LABEL.match(x)
                                               else x[len(GLOSS_PREFIX):] for x in sorted(glosses))
            if notes:
                rec["note"] = {"text": "; ".join(notes), "ai_document": bool(c.ai_draft)}
            quals = sorted({local(q) for q in self.g.objects(node, MRS.qualifier)})
            if quals:
                rec["qualifiers"] = quals
                for q in quals:
                    needs.terms.add(f"q:{q}")
                    self._term(f"q:{q}", self._qualifier_iri(node, q))
            voice = self.g.value(node, MRS.voice)
            if voice is not None:
                rec["voice"] = local(voice)
                needs.terms.add(f"voice:{rec['voice']}")
                self._term(f"voice:{rec['voice']}", str(voice))
            at = self.g.value(node, MRS.atEvent)
            if at is not None:
                rec["at_event"] = self.ref(str(at))
                needs.entities.add(rec["at_event"])
            self._term(f"pk:{pk}", str(self.g.value(node, MRS.predicate)))
        else:
            self._term(f"pk:{pk}", None, key=c.predicate)
        if c.kind == "participation":
            role = self.ix.role.get(cid)
            if role:
                rec["role"] = local(role)
                needs.terms.add(f"role:{rec['role']}")
                self._term(f"role:{rec['role']}", role)
        self._claims[cid] = rec
        self._claim_needs[cid] = needs
        return rec

    def _qualifier_iri(self, node, q: str) -> str:
        for o in sorted(self.g.objects(node, MRS.qualifier), key=str):
            if local(o) == q:
                return str(o)
        return q

    def claim_needs(self, cid: str) -> Needs:
        self.claim(cid)
        return self._claim_needs[cid]

    def gloss(self, cid: str) -> str | None:
        self.claim(cid)
        return self._glosses.get(cid)

    def passage(self, p: str, iri: str, needs: Needs) -> dict:
        if p not in self._passages:
            info = self.site.passage_info(URIRef(iri))
            work = info.get("work") or {}
            cite = info.get("citation")
            rec = {"cite": cite, "short": short_citation(cite) if cite else None, "work": work.get("label"),
                   "ai_document": bool(work.get("ai"))}
            if info.get("story") and self.site.entity(info["story"]) is not None:
                rec["story"] = self.ref(info["story"])
            self._passages[p] = rec
        if self._passages[p].get("story"):
            needs.entities.add(self._passages[p]["story"])
        return self._passages[p]

    def _term(self, ref: str, iri: str | None, key: str | None = None):
        """A label for a pk, qualifier, role, voice or geometry term: the graph's
        skos:prefLabel or rdfs:label (en, and ar where recorded), or for a link without a
        relation type, the site's i18n label of the link (key)."""
        if ref in self._terms:
            return
        rec = {}
        if iri and iri.startswith(("http://", "https://")):
            node = URIRef(iri)
            for lang in ("en", "ar"):
                for prop in (SKOS.prefLabel, RDFS.label):
                    vals = sorted(str(o) for o in self.g.objects(node, prop) if getattr(o, "language", None) == lang)
                    if not vals and lang == "en":
                        vals = sorted(str(o) for o in self.g.objects(node, prop)
                                      if getattr(o, "language", None) in (None, ""))
                    if vals:
                        rec[lang] = vals[0]
                        break
            rec.setdefault("en", local(iri))
        elif key:
            for lang in ("en", "ar"):
                try:
                    rec[lang] = self.t[lang].raw(key)
                except KeyError:
                    pass
            rec.setdefault("en", " ".join(key.split(".", 1)[-1].split("_")))
        else:
            rec["en"] = ref.split(":", 1)[-1]
        self._terms[ref] = rec

    # ------------------------------------------------------------------ entities
    def entity(self, ref: str) -> dict:
        if ref in self._entities:
            return self._entities[ref]
        iri = self._ref_iri[ref]
        e = self.site.entity(iri)
        if e is None:
            rec = {"kind": "node", "name": self.site.label_of(iri), "scholarly": self.site.label_of(iri)}
            self._entities[ref] = rec
            return rec
        rec = {"kind": e.kind, "name": e.name, "scholarly": e.scholarly, "links": len(self.site.claims.get(iri, []))}
        if e.kind == "group" and e.subtype:
            rec["subtype"] = e.subtype
        if e.prophet:
            rec["prophet"] = True
        if e.coverage:
            rec["coverage_state"] = e.coverage
        if e.kind in J.EVENT_KINDS:
            dates = [self.date(x) for x in e.data.get("dates") or []]
            if dates:
                rec["dates"] = sorted(dates, key=J.canonical)
            places = sorted({self.ref(p) for p in e.data.get("places") or []})
            if places:
                rec["places"] = places
        if e.kind == "story":
            if e.data.get("number") is not None:
                rec["number"] = e.data["number"]
            if e.data.get("part_label"):
                rec["part_label"] = e.data["part_label"]
            work = e.data.get("work") or {}
            if work.get("label"):
                rec["work"] = work["label"]
            if work.get("ai"):
                rec["ai_document"] = True
        if e.kind == "place":
            geo = self.geo(e)
            if geo is not None:
                rec["geo"] = geo
        self._entities[ref] = rec
        return rec

    def entity_needs(self, ref: str) -> set[str]:
        """The further entities an entity record refers to: an event's places."""
        return set(self.entity(ref).get("places") or [])

    def entity_terms(self, ref: str) -> set[str]:
        geo = self.entity(ref).get("geo") or {}
        return {x for x in (f"lc:{geo['confidence']}" if geo.get("confidence") else None,
                            f"gb:{geo['basis']}" if geo.get("basis") else None) if x}

    def date(self, x: dict) -> dict:
        out = {k: x.get(k) for k in ("native", "calendar", "earliest", "latest", "precision", "basis")}
        out["text"] = {lang: display.format_extent(x, self.t[lang])["text"] for lang in ("en", "ar")}
        if x.get("relative"):
            out["relative"] = True
        if x.get("disputed"):
            out["disputed"] = True
        return out

    def geo(self, e) -> dict | None:
        """A place's location, as obsdata._node_place reads it: one WKT point (lon, then
        lat) with its confidence and basis keys and the place's recorded-by agents; several
        different points give {"many": n} and none is chosen; only "unlocated" states give
        {"unlocated": true}; no geometry state, no geo."""
        g = self.g
        pts, unlocated = [], []
        for gs in g.objects(URIRef(e.iri), MRS.geometryState):
            conf = g.value(gs, MRS.locationConfidence)
            conf_key = local(conf)[3:] if conf is not None else None
            basis = g.value(gs, MRS.geometryBasis)
            basis_key = local(basis)[3:] if basis is not None else None
            if conf is not None:
                self._term(f"lc:{conf_key}", str(conf))
            if basis is not None:
                self._term(f"gb:{basis_key}", str(basis))
            geom = g.value(gs, MRS.geometry)
            wkt = g.value(geom, GEO.asWKT) if geom is not None else None
            if conf_key == "unlocated":
                unlocated.append(basis_key)
                continue
            if wkt is None:
                continue
            m = _POINT.search(str(wkt))
            if m:
                pt = (float(m.group(1)), float(m.group(2)), conf_key, basis_key)
                if all(p[:3] != pt[:3] for p in pts):
                    pts.append(pt)
        pts.sort(key=lambda p: (p[0], p[1], p[2] or "", p[3] or ""))
        agents = [{"label": label, "software": sw} for label, sw in sorted({(a.label, bool(a.software)) for a in e.agents})]
        if len(pts) == 1:
            lon, lat, conf_key, basis_key = pts[0]
            return {"lon": lon, "lat": lat, "confidence": conf_key, "basis": basis_key, "recorded_by": agents}
        if len(pts) > 1:
            return {"many": len(pts)}
        if unlocated:
            return {"unlocated": True, "basis": sorted(b for b in unlocated if b)[0] if any(unlocated) else None}
        return None

    def located(self, place_ref: str) -> bool:
        geo = self.entity(place_ref).get("geo") or {}
        return "lon" in geo and "lat" in geo

    def kinship(self, iri: str) -> bool:
        if iri not in self._kinship:
            self._kinship[iri] = any(c.relclass == "kinship" for c in self.site.claims.get(iri, []))
        return self._kinship[iri]

    # ------------------------------------------------------------------ narration (design §7.1)
    def sentence(self, cid: str, markers: list[str]) -> tuple[str, dict]:
        c = self.ix.claim[cid]
        rec = self.claim(cid)
        pk = rec["pk"]
        s, o, text = rec["s"], rec.get("o"), rec.get("text")
        o_ent = self.site.entity(c.object) if o else None
        if o and o_ent is not None and o_ent.kind == "story":
            t, slots = NARR_STORY, {"subject": s, "object": o}
        elif c.kind == "participation":
            t, slots = (NARR_ROLE, {"subject": s, "object": o, "role": f"role:{rec['role']}"}) if rec.get("role") \
                else (NARRATION_TEMPLATES["took_part"], {"subject": s, "object": o})
        elif pk in NARR_SIDE and rec.get("at_event") and o:
            t, slots = NARR_SIDE[pk], {"subject": s, "object": o, "event": rec["at_event"]}
        elif pk == "rel_dated" and text:
            t, slots = NARR_DATED, {"subject": s, "text": text}
        elif pk in NARRATION_TEMPLATES and o:
            t, slots = NARRATION_TEMPLATES[pk], {"subject": s, "object": o}
        elif text:
            t, slots = NARR_DEFAULT_TEXT, {"subject": s, "text": text, "relation": f"pk:{pk}"}
        else:
            t, slots = NARR_DEFAULT, {"subject": s, "object": o, "relation": f"pk:{pk}"}
        if markers:
            slots["markers"] = [{"t": self.k(NARR_MARKER), "marker": f"q:{q}"} for q in markers]
        return self.k(t), slots

    def narration(self, cids: list[str], apart_q: set[str]) -> list[dict]:
        """Merged, ordered narration items: one per distinct sentence (template and slots),
        each keeping every claim behind it."""
        items: dict[bytes, dict] = {}
        for cid in cids:
            rec = self.claim(cid)
            markers = sorted(q for q in rec.get("qualifiers") or [] if q in apart_q)
            t, slots = self.sentence(cid, markers)
            key = J.canonical([t, slots])
            if key not in items:
                items[key] = {"t": t, "c": [], **slots}
            items[key]["c"].append(cid)
        out = []
        for item in items.values():
            item["c"] = sorted(set(item["c"]))
            item["d"] = "discover" if any(self.claim(x)["discover"] for x in item["c"]) else "study"
            out.append(item)

        def rank(item):
            pks = [self.claim(x)["pk"] for x in item["c"]]
            ranks = [(NARRATION_ORDER.index(p), "") if p in NARRATION_ORDER else (len(NARRATION_ORDER), p)
                     for p in pks]
            cites = sorted((self._passages.get(self.claim(x).get("passage") or "") or {}).get("cite") or "\uffff"
                           for x in item["c"])
            return (min(ranks), cites[0], item["c"][0])

        return sorted(out, key=rank)[:NARRATION_CAP]

    # ------------------------------------------------------------------ a step
    def claims_about(self, iri: str) -> list[str]:
        """Every claim about an entity, in the cap order (the v1 claim-list order)."""
        cs = self.site.claims.get(iri, [])
        rows = sorted(((c.kind != "assertion", display.sort_key(self.site.label_of(c.subject)), c.predicate,
                        c.object, self.cid(c)) for c in cs))
        return list(dict.fromkeys(row[-1] for row in rows))

    def step(self, j, st, n: int | None, group: str) -> tuple[dict, Needs]:
        e = st.entity
        t = j.spec["select"]["type"]
        needs = Needs()
        sref = self.ref(e.iri)
        needs.entities.add(sref)

        def ids(claims) -> list[str]:
            out = [self.cid(c) for c in claims]
            needs.claims.update(out)
            return out

        def reason(r) -> dict:
            out = {"kind": r.kind}
            if r.other:
                out["other"] = self.ref(r.other)
                needs.entities.add(out["other"])
            if r.word is not None:
                out["word"] = r.word
            if r.label is not None:
                out["label"] = r.label
            if r.kind == "part" and e.kind == "story" and (e.data.get("work") or {}).get("ai"):
                out["ai_document"] = True
            out["claims"] = ids(r.claims)
            return out

        rec = {"key": e.pid, "ref": sref, "n": n, "group": group,
               "reasons": [reason(r) for r in st.reasons], "links": [reason(r) for r in st.links]}
        if st.order_note:
            rec["order"] = {"note": st.order_note, "ref": self.ref(st.order_ref) if st.order_ref else None}
            if rec["order"]["ref"]:
                needs.entities.add(rec["order"]["ref"])
        rec["records"] = ids(st.records)
        rec["contrary"] = ids(st.contrary)
        sides: dict[tuple, list[str]] = {}
        for c in st.side:
            cr = self.claim(self.cid(c))
            sides.setdefault((cr["pk"], cr.get("at_event"), cr.get("o")), []).append(self.cid(c))
        rec["side"] = []
        for (pk, at, other), cids in sorted(sides.items(), key=lambda kv: (kv[0][0], kv[0][1] or "", kv[0][2] or "")):
            needs.claims.update(cids)
            rec["side"].append({"pk": pk, "at": at, "with": other, "claims": sorted(cids)})
        if st.side_conflict:
            rec["side_conflict"] = True
        apart_q = {local(J.term(q, "set_apart")) for q in j.spec["select"].get("set_apart") or []}
        if t == "people":
            narr_in = [self.cid(c) for c in st.side + st.records + st.contrary]
        elif t == "stories":
            narr_in = [self.cid(c) for c in st.records]
        else:
            narr_in = self.claims_about(e.iri)
        seen = list(dict.fromkeys(narr_in))
        total, eligible = len(seen), sum(1 for x in seen if self.claim(x)["discover"])
        listed = seen[:CLAIM_CAP]
        if t in ("events", "stories"):
            rec["claims"] = {"ids": listed, "total": total}
        needs.claims.update(listed)
        rec["counts"] = {"records": total, "discover": eligible}
        rec["narration"] = self.narration(listed, apart_q)
        for item in rec["narration"]:
            for slot in ("subject", "object", "event"):
                if item.get(slot):
                    needs.entities.add(item[slot])
        rec["prompts"] = self.prompts(j, st, listed, needs)
        rec["next"] = self.next(j, st)
        rec["hints"] = self.hints(e)
        if st.e3 is not None:
            rec["e3"] = {"tier": st.e3["tier"], "pos": st.e3["pos"], "links": st.e3["links"],
                         "accepted_islam": self.acceptance(st.e3["accepted_islam"], needs)}
        return rec, needs

    def acceptance(self, records: list[dict], needs: Needs) -> list[dict]:
        out = []
        for r in records:
            ev = self.ref(r["event"])
            needs.entities.add(ev)
            cids = sorted(self.cid(c) for c in r["claims"])
            needs.claims.update(cids)
            out.append({"event": ev, "earliest": r["earliest"], "latest": r["latest"], "precision": r["precision"],
                        "claims": cids})
        return out

    def prompts(self, j, st, listed: list[str], needs: Needs) -> list[dict]:
        e = st.entity
        sref = self.ref(e.iri)
        out = []

        def add(name: str, slot: str, answer: dict):
            claims = answer.get("claims")
            if claims is not None:
                if not claims:
                    return
                needs.claims.update(claims)
                d = "discover" if any(self.claim(x)["discover"] for x in claims) else "study"
            else:
                d = "discover"
            out.append({"id": f"{j.slug}:{e.pid}:{name}", "t": self.k(PROMPTS[name]), "slots": {slot: sref},
                        "answer": answer, "graded": False, "d": d})

        about = [(x, self.claim(x)) for x in listed]

        def person(x: str) -> bool:
            who = self.site.entity(self.ix.claim[x].subject)
            return who is not None and who.kind == "person"

        if e.kind == "event":
            add("event_who", "event", {"claims": [x for x, r in about
                                                  if r["pk"] in WHO_PKS and r.get("o") == sref and person(x)]})
            add("event_when", "event", {"claims": [x for x, r in about if r["pk"] == "rel_dated" and r["s"] == sref]})
            add("event_where", "event", {"claims": [x for x, r in about if r["pk"] in WHERE_PKS and r["s"] == sref]})
        elif e.kind == "story":
            named = [self.cid(c) for c in st.records] if st.records else [x for x, r in about if r.get("o") == sref]
            add("story_names", "story", {"claims": named})
        elif e.kind == "person":
            add("person_elsewhere", "person", {"href": f"{e.kind}/{e.pid}/#evidence"})
            add("person_contrary", "person", {"claims": [self.cid(c) for c in st.contrary]})
        return out

    def next(self, j, st) -> list[dict]:
        e = st.entity
        sref = self.ref(e.iri)
        out = [{"t": self.k(NEXT["page"]), "ref": sref, "href": f"{e.kind}/{e.pid}/#evidence", "d": "discover"}]
        study = (self.stop_urls.get(j.slug) or {}).get(e.iri, {}).get("study")
        if study:
            out.append({"t": self.k(NEXT["study"]), "ref": sref, "href": study, "d": "discover", "only": "discover"})
        for slug, n in self.entity_index.get(e.iri, []):
            if slug == j.slug:
                continue
            urls = (self.stop_urls.get(slug) or {}).get(e.iri) or {}
            door = self.doors.get(slug)
            out.append({"t": self.k(NEXT["also_in"]), "ref": sref, "journey": slug, "n": n,
                        "href": urls.get(door), "urls": dict(sorted(urls.items())), "d": "discover"})
        return out

    def hints(self, e) -> dict:
        """View hints, chosen by rule from a closed vocabulary (design §7.6). They carry no fact."""
        views = []
        if e.kind == "event":
            if any(x.get("earliest") and x.get("latest") for x in e.data.get("dates") or []):
                views.append("time")
            places = sorted({self.ref(p) for p in e.data.get("places") or []})
            if len(places) == 1 and self.located(places[0]):
                views.append("map")
        elif e.kind == "story":
            views.append("stories")
        elif e.kind == "person" and self.kinship(e.iri):
            views.append("lineage")
        if not views:
            views.append("sky")
        return {"views": views, "focus": None if e.prophet else self.ref(e.iri), "light": bool(e.prophet),
                "chosen_by": "rule"}

    # ------------------------------------------------------------------ a journey
    def text(self, key: str | None) -> dict | None:
        if not key:
            return None
        self.k(key)
        return {"key": key, "en": (self.i18n.get("en") or {}).get(key), "ar": (self.i18n.get("ar") or {}).get(key)}

    def rule_text(self, j) -> list[dict]:
        """The order sentences of the rule box, each with the depth it starts at (design §6.7)."""
        applied = j.order_applied or j.spec["order"]
        shown = "prophet_first_then_name" if applied == "e3_pending" else applied
        out = [{"t": self.k(ORDER_KEYS[shown]), "d": "discover"}]
        if j.spec["order"] == "e3" and j.lists:
            ls = j.lists
            if applied == "e3_pending":
                out.append({"t": self.k(E3_TEXT["pending"]), "d": "study",
                            "slots": {"file": ls["file"], "state": ls["state"]}})
            else:
                out.append({"t": self.k(E3_TEXT["sources"]), "d": "discover",
                            "slots": {"sources": [s["text"] for s in ls["sources"]]}})
                out.append({"t": self.k(E3_TEXT["links"]), "d": "discover"})
                out.append({"t": self.k(E3_TEXT["lists"]), "d": "study",
                            "slots": {"file": ls["file"], "state": ls["state"], "sha": ls["sha"]}})
            out.append({"t": self.k(E3_TEXT["no_last"]), "d": "study"})
        if j.spec["select"].get("group_by") == "side":
            out.append({"t": self.k(GROUP_SIDE), "d": "discover"})
        return out

    def journey(self, j, plan: dict | None = None) -> "Resolved":
        spec = j.spec
        slug = spec["slug"]
        t = spec["select"]["type"]
        if self.mode == "accepted":
            raise J.RuleError(f"{slug}: public mode 'accepted' needs resolve(accepted_only=True), which does not "
                              "exist yet; the export stops here rather than show claims that are not accepted")
        sha = J.rule_sha(spec, lists_root=self.lists_root, i18n=self.i18n)
        steps, step_needs = [], []
        for n, st in enumerate(j.steps, 1):
            rec, needs = self.step(j, st, n, st.group)
            steps.append(rec)
            step_needs.append(needs)
        for st in j.set_apart:
            rec, needs = self.step(j, st, None, "apart")
            steps.append(rec)
            step_needs.append(needs)
        for needs in step_needs:
            self.close(needs)
        anchors = [self.ref(a) for a in j.anchors]
        excluded = [{"ref": self.ref(iri), "reason": why} for iri, why in j.excluded]
        head_refs = sorted(set(anchors) | {x["ref"] for x in excluded} | {s["ref"] for s in steps})
        head_needs = Needs()
        head_needs.entities.update(head_refs)
        self.close(head_needs)
        everything = Needs()
        for needs in step_needs + [head_needs]:
            everything.update(needs)
        tables = self.tables(everything)
        glosses = {cid: self.gloss(cid) for cid in sorted(everything.claims) if self.gloss(cid)}
        keys = [s["key"] for s in steps]
        plan = plan or default_plan(keys)
        urls = stop_urls(slug, spec["door"], plan, keys)

        stops = []
        for st, rec in zip(j.steps, steps):
            stops.append({"key": rec["key"], "ref": rec["ref"], "n": rec["n"], "group": rec["group"],
                          "urls": urls[rec["key"]]})
        if t == "people":
            self.sorts(j, stops)
        apart = []
        quals = {local(J.term(q, "set_apart")) for q in spec["select"].get("set_apart") or []}
        for st, rec in zip(j.set_apart, steps[len(j.steps):]):
            because: dict[str, list[str]] = {}
            for c in st.records + st.contrary:
                for q in self.claim(self.cid(c)).get("qualifiers") or []:
                    if q in quals:
                        because.setdefault(q, []).append(self.cid(c))
            apart.append({"key": rec["key"], "ref": rec["ref"], "urls": urls[rec["key"]],
                          "because": [{"qualifier": f"q:{q}", "claims": sorted(set(v))} for q, v in sorted(because.items())]})
        lists = None
        if j.lists:
            lists = {"file": j.lists["file"], "state": j.lists["state"], "applied": j.lists["applied"],
                     "sha": j.lists["sha"], "sources_complete": j.lists["sources_complete"],
                     "stale_approval": j.lists["stale_approval"], "sources": copy.deepcopy(j.lists["sources"])}
        groups = []
        for gr in j.groups:
            groups.append({"key": gr.key, "t": self.k(gr.t) if gr.t else None, "lead": self.k(gr.lead) if gr.lead else None,
                           "from": gr.start + 1, "to": gr.end})
        behind = [tables["claims"][x] for x in sorted(behind_stops(steps))]
        share = {"accepted": sum(1 for r in behind if r["status"] == "accepted"),
                 "of": sum(1 for r in behind if r["kind"] == "assertion"),
                 "no_status": sum(1 for r in behind if r["status"] is None)}
        ai_works = sorted({p["work"] for p in tables["passages"].values() if p.get("ai_document") and p.get("work")}
                          | {r["work"] for r in tables["entities"].values() if r.get("ai_document") and r.get("work")})
        sm = J.story_mode(spec, lists_root=self.lists_root, i18n=self.i18n)
        doc = {
            "format": FORMAT, "version": VERSION, "slug": slug, "kind": spec.get("kind", "official"),
            "state": J.state(spec, lists_root=self.lists_root, i18n=self.i18n),
            "stale_approval": J.stale_approval(spec, lists_root=self.lists_root, i18n=self.i18n),
            "rule_sha": sha, "approved_by": copy.deepcopy(spec.get("approved_by") or []), "listed": True,
            "title": self.text(spec["title"]), "lead": self.text(spec["lead"]), "lead_study": self.text(spec.get("lead_study")),
            "door": spec["door"], "type": t, "select": copy.deepcopy(spec["select"]), "order": spec["order"],
            "order_applied": j.order_applied or spec["order"], "lists": lists, "graph": dict(self.graph),
            "accepted_share": share, "story_mode": {"open": sm["open"], "stale": sm["stale"], "approved_by": sm["approved_by"]},
            "hold_study": bool(spec.get("hold_study", False)), "order_conflict": j.order_conflict,
            "mixes_stories_and_events": j.mixes_stories_and_events, "universe": j.universe,
            "part_labels": list(j.part_labels), "groups": groups, "anchors": anchors, "excluded": excluded,
            "checkpoint": self.checkpoint(j), "rule_text": self.rule_text(j),
            "ai_documents": ai_works,
            "ai_note": {"discover": self.k(TEXTS["ai_source_note"]), "study": self.k(TEXTS["ai_note"])} if ai_works else None,
            "stops": stops, "set_apart": apart,
            "reader": {"url": f"learn/{slug}/", "anchor": "s-{key}"},
            "steps": steps, **tables, "glosses": glosses,
            "trace": {st.entity.pid: {"hop": st.hop} for st in j.steps + j.set_apart},
        }
        doc["content_sha"] = content_sha(doc)
        return Resolved(doc, step_needs, head_refs, plan)

    def sorts(self, j, stops: list[dict]):
        """sort: {default, az, links, accepted_islam} per people stop (design §6.5)."""
        jl = self.jl()
        by_key = {st.entity.pid: st for st in j.steps}
        az = sorted(stops, key=lambda s: (display.sort_key(by_key[s["key"]].entity.name), s["key"]))
        links = {s["key"]: len(self.site.claims.get(by_key[s["key"]].iri, [])) for s in stops}
        by_links = sorted(stops, key=lambda s: (-links[s["key"]], display.sort_key(by_key[s["key"]].entity.name), s["key"]))
        records = {}
        for s in stops:
            st = by_key[s["key"]]
            records[st.iri] = st.e3["accepted_islam"] if st.e3 is not None else \
                jl.accepted_islam_records(self.site, st.iri, self._accept)
        rank = jl.accepted_islam_rank(self.site, records)
        pos_az = {s["key"]: n for n, s in enumerate(az, 1)}
        pos_links = {s["key"]: n for n, s in enumerate(by_links, 1)}
        for s in stops:
            s["sort"] = {"default": s["n"], "az": pos_az[s["key"]], "links": pos_links[s["key"]],
                         "accepted_islam": rank[by_key[s["key"]].iri]}

    def checkpoint(self, j) -> dict:
        """Practice questions (accepted claims only, practice.bank) about the journey: every
        entity a question is about is a step or an anchor."""
        inside = {st.iri for st in j.steps} | set(j.anchors)
        items = sorted(q["id"] for q in self.bank if all(a in inside for a in q["about"]))
        return {"items": items, "graded_from": "accepted",
                "feedback": {"miss": self.k(CHECK["miss"]), "see": self.k(CHECK["see"])}}

    def close(self, needs: Needs):
        """Add what the claims and entities refer to, so every reference resolves."""
        for cid in sorted(needs.claims):
            needs.update(self.claim_needs(cid))
        for r in sorted(needs.entities):
            needs.entities |= self.entity_needs(r)
        for r in sorted(needs.entities):
            needs.terms |= self.entity_terms(r)

    def tables(self, needs: Needs) -> dict:
        return {"claims": {c: self.claim(c) for c in sorted(needs.claims)},
                "passages": {p: self._passages[p] for p in sorted(needs.passages)},
                "entities": {r: self.entity(r) for r in sorted(needs.entities)},
                "terms": {t: self._terms[t] for t in sorted(needs.terms) if t in self._terms}}


class Resolved:
    """A resolved journey: the unsplit document and what each step refers to."""

    def __init__(self, doc: dict, step_needs: list[Needs], head_refs: list[str], plan: dict):
        self.doc, self.step_needs, self.head_refs, self.plan = doc, step_needs, head_refs, plan


def behind_stops(steps: list[dict]) -> set[str]:
    """The claims behind the stops: their reasons and links, records, contrary and side
    claims, and an events or stories step's claim list (not the sort data)."""
    out: set[str] = set()
    for s in steps:
        for r in s["reasons"] + s["links"]:
            out.update(r["claims"])
        out.update(s["records"])
        out.update(s["contrary"])
        for side in s["side"]:
            out.update(side["claims"])
        out.update((s.get("claims") or {}).get("ids") or [])
    return out


# --------------------------------------------------------------------------- content digest, pages and URLs
LAYOUT_KEYS = ("graph", "content_sha", "parts", "research", "state", "stale_approval", "approved_by", "story_mode",
               "rule_sha", "reader", "title", "lead", "lead_study", "hold_study", "door", "listed", "rule_text",
               "ai_note")


def content_sha(doc: dict) -> str:
    """sha12 of the canonical unsplit journey (stops, steps, claims, passages, entities,
    terms, glosses, order data) without its layout (URLs, part lists, the graph
    fingerprint), its approval layer, its wording and itself. A changed participation or
    role changes it even when the graph fingerprint, which cannot see blank nodes, does not."""
    body = {k: v for k, v in doc.items() if k not in LAYOUT_KEYS}
    body["stops"] = [{k: v for k, v in s.items() if k not in ("urls", "part")} for s in doc.get("stops") or []]
    body["set_apart"] = [{k: v for k, v in s.items() if k not in ("urls", "part")} for s in doc.get("set_apart") or []]
    body["steps"] = [{k: v for k, v in s.items() if k != "next"} for s in doc.get("steps") or []]
    return J.sha12(body)


def default_plan(keys: list[str]) -> dict:
    """One page per depth, holding every stop (stage C's reader passes its own split)."""
    return {d: [list(keys)] for d in DEPTHS}


def page_url(slug: str, door: str, depth: str, k: int) -> str:
    base = f"learn/{slug}/" if depth == door else f"learn/{slug}/{depth}/"
    return base if k == 1 else f"{base}p{k}/"


def check_plan(slug: str, plan: dict, keys: list[str]):
    for depth in DEPTHS:
        pages = plan.get(depth)
        if not pages or any(not p for p in pages) or [k for p in pages for k in p] != keys:
            raise J.RuleError(f"{slug}: the page plan for {depth} must cut the stops, in order, into non-empty pages")


def stop_urls(slug: str, door: str, plan: dict, keys: list[str]) -> dict:
    check_plan(slug, plan, keys)
    out: dict[str, dict] = {key: {} for key in keys}
    for depth in DEPTHS:
        for k, page in enumerate(plan[depth], 1):
            for key in page:
                out[key][depth] = f"{page_url(slug, door, depth, k)}#s-{key}"
    return out


def journey_pages(slug: str, door: str, plan: dict) -> list[dict]:
    out = []
    for depth in DEPTHS:
        pages = plan[depth]
        for k, page in enumerate(pages, 1):
            path = page_url(slug, door, depth, k)
            out.append({"path": path, "file": f"{path}index.html", "kind": "journey", "journey": slug,
                        "depth": depth, "page": k, "pages": len(pages), "door": depth == door,
                        "first": page[0], "last": page[-1]})
    return out


def default_extra_pages(n_questions: int) -> list[dict]:
    """The learn index and the practice pages a reader build makes (render_learn pages
    QUESTIONS_PER_PAGE questions each)."""
    from render_learn import QUESTIONS_PER_PAGE
    n = max(1, -(-n_questions // QUESTIONS_PER_PAGE))
    out = [{"path": "learn/", "file": "learn/index.html", "kind": "index", "depth": "discover", "page": 1, "pages": 1,
            "first": None, "last": None}]
    for k in range(1, n + 1):
        path = "learn/practice/" if k == 1 else f"learn/practice/{k}/"
        out.append({"path": path, "file": f"{path}index.html", "kind": "practice", "depth": "study", "page": k,
                    "pages": n, "first": None, "last": None})
    return out


# --------------------------------------------------------------------------- split into parts
def _part(doc: dict, resolver: Resolver, idx: list[int], needs: list[Needs], k: int) -> tuple[dict, dict]:
    want = Needs()
    for i in idx:
        want.update(needs[i])
    tables = resolver.tables(want)
    part = {"format": PART_FORMAT, "version": VERSION, "slug": doc["slug"], "part": k,
            "graph": {"fingerprint": doc["graph"]["fingerprint"]}, "content_sha": doc["content_sha"],
            "steps": [doc["steps"][i] for i in idx], **tables}
    research = {"format": RESEARCH_FORMAT, "version": VERSION, "slug": doc["slug"], "part": k,
                "glosses": {c: doc["glosses"][c] for c in sorted(want.claims) if c in doc["glosses"]},
                "trace": {doc["steps"][i]["key"]: doc["trace"][doc["steps"][i]["key"]] for i in idx}}
    return part, research


def split(resolver: Resolver, res: Resolved, budget: int = PART_BUDGET) -> tuple[dict, list[dict], list[dict]]:
    """The head, the parts and the research files of a resolved journey. Parts are cut
    greedily in stop order; each holds at least one stop and stays within `budget` bytes,
    and so does its research file. A single stop over the budget is a RuleError."""
    doc = res.doc
    steps = doc["steps"]
    cuts: list[list[int]] = []
    cur: list[int] = []

    def fits(idx):
        part, research = _part(doc, resolver, idx, res.step_needs, len(cuts) + 1)
        return len(blob(part)) <= budget and len(blob(research)) <= budget

    for i in range(len(steps)):
        if fits(cur + [i]):
            cur.append(i)
            continue
        if not cur or not fits([i]):
            part, research = _part(doc, resolver, [i], res.step_needs, len(cuts) + 1)
            raise J.RuleError(f"{doc['slug']}: stop {steps[i]['key']} alone needs {len(blob(part))} bytes "
                              f"({len(blob(research))} in its research file), over the part budget of {budget}")
        cuts.append(cur)
        cur = [i]
    if cur:
        cuts.append(cur)
    parts, researches = [], []
    where: dict[str, str] = {}
    for k, idx in enumerate(cuts, 1):
        part, research = _part(doc, resolver, idx, res.step_needs, k)
        parts.append(part)
        researches.append(research)
        for i in idx:
            where[steps[i]["key"]] = f"part-{k}.json"
    head = {k: v for k, v in doc.items() if k not in ("steps", "claims", "passages", "entities", "terms", "glosses", "trace")}
    head = copy.deepcopy(head)
    for s in head["stops"] + head["set_apart"]:
        s["part"] = where[s["key"]]
    head["parts"] = [f"part-{k}.json" for k in range(1, len(parts) + 1)]
    head["research"] = [f"research-{k}.json" for k in range(1, len(parts) + 1)]
    head["entities"] = {r: {"kind": doc["entities"][r]["kind"], "name": doc["entities"][r]["name"]}
                        for r in res.head_refs}
    return head, parts, researches


# --------------------------------------------------------------------------- the whole export
def _prepare(r: Resolver, journeys: list, plans: dict) -> dict:
    """Page plans, stop URLs and the entity index, for every journey (next.also_in reads them)."""
    plans = dict(plans or {})
    for j in journeys:
        stops = j.steps + j.set_apart
        keys = [st.entity.pid for st in stops]
        plans.setdefault(j.slug, default_plan(keys))
        urls = stop_urls(j.slug, j.spec["door"], plans[j.slug], keys)
        r.stop_urls[j.slug] = {st.iri: urls[st.entity.pid] for st in stops}
        r.doors[j.slug] = j.spec["door"]
        for n, st in enumerate(j.steps, 1):
            r.entity_index.setdefault(st.iri, []).append((j.slug, n))
        for st in j.set_apart:
            r.entity_index.setdefault(st.iri, []).append((j.slug, None))
    for iri in r.entity_index:
        r.entity_index[iri].sort(key=lambda x: (x[0], x[1] or 0))
    return plans


def resolve(site: Site, journey, strings: dict | None = None, *, lists_root=None, bank: list | None = None,
            graph_file=None, plan: dict | None = None) -> dict:
    """One built journey (journeys.build), resolved and unsplit (design §10). Alone, it
    cannot name the other journeys a stop is also in; resolve_all does."""
    r = Resolver(site, i18n=strings, lists_root=lists_root, bank=bank,
                 graph=graph_info(site, graph_file) if graph_file is not None else None)
    plans = _prepare(r, [journey], {journey.slug: plan} if plan else None)
    return r.journey(journey, plans[journey.slug]).doc


def resolve_all(site: Site, folder=None, *, journeys: list | None = None, journeys_dir=None, lists_root=None,
                strings: dict | None = None, bank: list | None = None, plans: dict | None = None,
                extra_pages: list | None = None, part_budget: int = PART_BUDGET, graph_file=None,
                facade: bool = False) -> dict:
    """Every journey, resolved and split; written to `folder` (index.json, strings.json,
    pages.json, and journeys/{slug}/ with journey.json, part-{k}.json and research-{k}.json)
    when one is given. `plans` ({slug: {depth: [[stop keys of a page], ...]}}) and
    `extra_pages` come from the reader build; without them every depth is one page.
    Returns {"index", "journeys": {slug: unsplit doc}, "files": {path: bytes}, "digest", "facade"}."""
    mode = public_mode()
    i18n = J.load_i18n() if strings is None else strings
    if journeys is None:
        specs = J.load_specs(journeys_dir or HERE / "journeys", lists_root=lists_root)
        journeys = J.build_all(site, specs, lists_root=lists_root)
    bank = practice.bank(site.g) if bank is None else bank
    r = Resolver(site, i18n=i18n, lists_root=lists_root, bank=bank, graph=graph_info(site, graph_file), mode=mode)
    plans = _prepare(r, journeys, plans)

    out: dict[str, bytes] = {}
    docs, entries, pages = {}, [], []
    for j in journeys:
        res = r.journey(j, plans[j.slug])
        head, parts, researches = split(r, res, part_budget)
        docs[j.slug] = res.doc
        jfolder = f"journeys/{j.slug}"
        out[f"{jfolder}/journey.json"] = blob(head)
        for part, research in zip(parts, researches):
            out[f"{jfolder}/part-{part['part']}.json"] = blob(part)
            out[f"{jfolder}/research-{research['part']}.json"] = blob(research)
        pages += journey_pages(j.slug, j.spec["door"], plans[j.slug])
        entries.append(index_entry(head, plans[j.slug], f"{jfolder}/journey.json"))
    pages += extra_pages if extra_pages is not None else default_extra_pages(len(bank))
    pages.sort(key=lambda p: p["path"])
    lists = next((d["lists"] for d in docs.values() if d.get("lists")), None)
    jl = r.jl()
    states = sorted({e.get("coverage_state") for d in docs.values() for e in d["entities"].values()} - {None})
    labels = {"status": {s: r.k(f"status.{s}") for s in STATUSES + ("none",)},
              "coverage": {c: r.k(f"coverage.{c}") for c in states if r.has(f"coverage.{c}")},
              "type": {k: r.k(f"type.{k}") for k in ("person", "group", "place", "event", "story")},
              "status_line": r.k("status.label"), "coverage_line": r.k("coverage.label")}
    index = {
        "format": INDEX_FORMAT, "version": VERSION, "graph": dict(r.graph), "public_mode": mode, "depths": list(DEPTHS),
        "depth_policy": DEPTH_POLICY, "background_rule": J.background_info(site),
        "lists": {k: lists[k] for k in ("file", "state", "applied", "sha", "sources_complete")} if lists else None,
        "sorts": {**{k: r.k(v) for k, v in SORTS.items()},
                  "accepted_islam": {"t": r.k("learn.sort.accepted_islam"), "rule": copy.deepcopy(jl.ACCEPTANCE_RULE),
                                     "needs": jl.ACCEPTANCE_NEEDS, "undated": r.k(TEXTS["undated"])}},
        "view_vocabulary": list(VIEW_VOCABULARY), "narration_order": list(NARRATION_ORDER),
        "texts": {k: r.k(v) for k, v in sorted(TEXTS.items())}, "labels": labels,
        "strings": "strings.json", "pages": "pages.json",
        "entities": {}, "journeys": entries,
    }
    for iri, hits in sorted(r.entity_index.items(), key=lambda kv: site.entity(kv[0]).pid):
        index["entities"][site.entity(iri).pid] = [[slug, site.entity(iri).pid, n] for slug, n in hits]
    out["index.json"] = blob(index)
    out["strings.json"] = blob(strings_doc(r))
    out["pages.json"] = blob({"format": PAGES_FORMAT, "version": VERSION, "pages": pages})
    projection = None
    if facade:
        projection = facade_doc(journeys, i18n.get("en") or {})
        out["facade.json"] = blob(projection)
    digest = J.sha12({p: hashlib.sha256(out[p]).hexdigest() for p in sorted(out)})
    if folder is not None:
        write_export(folder, out)
    return {"index": index, "journeys": docs, "files": out, "digest": digest,
            "facade": projection["digest"] if projection else facade_digest(journeys, i18n.get("en") or {})}


def index_entry(head: dict, plan: dict, file: str) -> dict:
    return {"slug": head["slug"], "kind": head["kind"], "state": head["state"], "stale_approval": head["stale_approval"],
            "rule_sha": head["rule_sha"], "content_sha": head["content_sha"], "listed": head["listed"],
            "title": head["title"], "lead": head["lead"], "lead_study": head["lead_study"], "door": head["door"],
            "type": head["type"], "order": head["order"], "order_applied": head["order_applied"],
            "groups": [g["key"] for g in head["groups"]], "steps": len(head["stops"]), "apart": len(head["set_apart"]),
            "excluded": len(head["excluded"]), "accepted_share": head["accepted_share"],
            "story_mode": {"open": head["story_mode"]["open"], "stale": head["story_mode"]["stale"]},
            "parts": len(head["parts"]), "file": file,
            "urls": {d: [page_url(head["slug"], head["door"], d, k) for k in range(1, len(plan[d]) + 1)] for d in DEPTHS}}


def strings_doc(r: Resolver) -> dict:
    """Every i18n key the export references, in en and (where there is one) ar. Plural
    keys come with their .one and .other forms."""
    out = {"en": {}, "ar": {}}
    for key in sorted(r.keys):
        for lang in ("en", "ar"):
            t = r.t[lang]
            for k in (key, f"{key}.one", f"{key}.other"):
                try:
                    out[lang][k] = t.raw(k)
                except KeyError:
                    pass
        if not any(k in out["en"] for k in (key, f"{key}.one")):
            raise J.RuleError(f"the export names the i18n key {key!r}, which learn/i18n/en.json does not hold")
    return out


# --------------------------------------------------------------------------- writing
def _protected(folder: Path) -> bool:
    here = Path(folder).resolve()
    return any(here == p or p in here.parents or here in p.parents for p in _PROTECTED) or here in (ROOT, HERE)


def write_export(folder, payload: dict[str, bytes]):
    """Write the export files into `folder`, which must be new, empty or a previous export
    (it holds EXPORT_MARKER). Refuses learn/journeys/, learn/lists/ and their parents."""
    root = Path(folder)
    if _protected(root):
        raise J.RuleError(f"{root}: the export never writes into the rule or list folders, or above them")
    if root.exists():
        if any(root.iterdir()) and not (root / EXPORT_MARKER).is_file():
            raise J.RuleError(f"{root} is not empty and holds no previous export ({EXPORT_MARKER}); refusing to write")
        for old in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if old.is_dir():
                old.rmdir()
            else:
                old.unlink()
    root.mkdir(parents=True, exist_ok=True)
    for rel in sorted(payload):
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload[rel])
    (root / EXPORT_MARKER).write_bytes(b"made by learn/journey_export.py; safe to delete and rebuild\n")


# --------------------------------------------------------------------------- the Atlas facade (design §11)
def atlas_projection(journey, strings: dict) -> dict:
    """The record atlas/build.py load_journeys builds from one journey, with IRIs where it
    puts node numbers (None where it puts -1), plus the computed story_mode.open.
    `journey.spec` is a load_specs copy; `strings` is the flat en table."""
    spec = journey.spec
    why = []
    for st in journey.steps:
        rs = [[r.kind, r.other or None, r.word or r.label or ""] for r in st.reasons]
        for c in st.records[:3]:
            o = c.object if c.subject == st.iri else c.subject
            rs.append(["record", o, c.predicate if not c.predicate_is_key
                       else " ".join(c.predicate.split(".")[-1].split("_"))])
        why.append(rs)
    return {"key": spec["slug"], "title": strings.get(spec["title"], spec["slug"]), "lead": strings.get(spec["lead"], ""),
            "type": spec["select"]["type"], "status": spec["status"], "steps": [s.iri for s in journey.steps],
            "apart": [s.iri for s in journey.set_apart], "anchors": list(journey.anchors), "why": why,
            "story_mode": {"open": bool((spec.get("story_mode") or {}).get("open"))}}


def facade_doc(journeys: list, strings: dict) -> dict:
    projections = [atlas_projection(j, strings) for j in journeys]
    return {"facade_version": J.FACADE_VERSION, "journeys": projections, "digest": J.sha12(projections)}


def facade_digest(journeys: list, strings: dict) -> str:
    """sha12 of the Atlas projection of these journeys: if it changes, atlas/index.html needs a rebuild."""
    return J.sha12([atlas_projection(j, strings) for j in journeys])


def _fixtures():
    path = HERE / "tests" / "fixtures.py"
    spec = importlib.util.spec_from_file_location("journey_lock_fixtures", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _computed(spec: dict, lists_root) -> dict:
    out = copy.deepcopy(spec)
    out["status"] = J.state(spec, lists_root=lists_root)
    out["story_mode"] = J.story_mode(spec, lists_root=lists_root)
    return out


def facade_engine() -> list:
    """The projections of fixed fixture rules on fixtures.facade_graph(): events; people in
    the e3 order with a reviewed fixture list; people with side groups; stories."""
    fx = _fixtures()
    site = fx.site_of(fx.facade_graph())
    with tempfile.TemporaryDirectory() as tmp:
        fx.reviewed_list_file(tmp, ["Person C", "Person A"], ["Person C", "Person A", "Person B"])
        rules = [fx.events_spec(["Hijra"]),
                 fx.people_spec(words=("Badr",), order="e3", not_words=["expedition"]),
                 fx.people_spec(words=("Badr",), order="prophet_first_then_name", group_by="side",
                                not_words=["expedition"]),
                 fx.stories_spec(["Makkan"])]
        out = []
        for rule in rules:
            spec = _computed(J.validate(rule), tmp)
            out.append(atlas_projection(J.build(site, spec, lists_root=tmp), {}))
    return out


def facade_inputs(journeys_dir=None, lists_root=None) -> list:
    """What the Atlas sees of the shipped rule files: the facade-visible fields (slug,
    title and lead keys and their en text, the rule and its order), the computed status
    and story_mode.open, and the list file's content and state."""
    en = J.load_i18n().get("en") or {}
    out = []
    for spec in J.load_specs(journeys_dir or HERE / "journeys", lists_root=lists_root):
        state = None
        path = J.lists_file(spec, lists_root)
        if path is not None:
            try:
                import journey_lists
                state = journey_lists.load_lists(path, where=spec["lists"])["state"]
            except J.RuleError:
                state = "unreadable"
        out.append({"slug": spec["slug"], "title": spec["title"], "lead": spec["lead"],
                    "title_en": en.get(spec["title"]), "lead_en": en.get(spec["lead"]), "select": spec["select"],
                    "order": spec["order"], "lists": spec.get("lists"), "status": spec["status"],
                    "story_mode_open": spec["story_mode"]["open"],
                    "list_content": J.lists_sha(spec, lists_root=lists_root), "list_state": state})
    return out


def facade_lock(journeys_dir=None, lists_root=None) -> dict:
    """What learn/facade.lock must hold."""
    return {"facade_version": J.FACADE_VERSION, "inputs": J.sha12(facade_inputs(journeys_dir, lists_root)),
            "engine": J.sha12(facade_engine())}


def write_lock() -> dict:
    lock = facade_lock()
    LOCK_FILE.write_bytes(blob(lock))
    return lock


# --------------------------------------------------------------------------- command line
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export every journey as marsad-journey v1 JSON (learn/FORMAT.md).")
    ap.add_argument("--graph", default=str(ROOT / "build" / "graph.ttl"))
    ap.add_argument("--out", help="the folder to write the export into")
    ap.add_argument("--part-budget", type=int, default=PART_BUDGET)
    ap.add_argument("--facade", action="store_true", help="also write facade.json, the Atlas projection")
    ap.add_argument("--lock", action="store_true", help="rewrite learn/facade.lock")
    a = ap.parse_args(argv)
    if a.lock:
        lock = write_lock()
        print(f"learn/facade.lock: facade {lock['facade_version']}, inputs {lock['inputs']}, engine {lock['engine']}")
        if not a.out:
            return 0
    if not a.out:
        ap.error("--out is required (or give --lock alone)")
    graph = Path(a.graph)
    if not graph.is_file():
        ap.error(f"{graph} not found: run ontology/build_graph.py first")
    site = Site(graph)
    res = resolve_all(site, a.out, part_budget=a.part_budget, graph_file=graph, facade=a.facade)
    idx = res["index"]
    print(f"export: {a.out}, {len(idx['journeys'])} journeys, {len(res['files'])} files, digest {res['digest']}")
    print(f"  graph {idx['graph']['file']}: fingerprint {idx['graph']['fingerprint']}, {idx['graph']['triples']} triples")
    for e in idx["journeys"]:
        sizes = [len(b) for p, b in sorted(res["files"].items()) if p.startswith(f"journeys/{e['slug']}/part-")]
        print(f"  {e['slug']}: {e['steps']} stops (+{e['apart']} apart), parts {e['parts']} (largest {max(sizes)} B), "
              f"{e['state']}, order {e['order_applied']}, rule_sha {e['rule_sha']}, content_sha {e['content_sha']}")
    print(f"  atlas facade {res['facade']}: if this changed, rebuild atlas/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
