"""
Shared code for the scholars' review queue (slice 3a): review/build_queue.py and
review/import_decisions.py. Nothing here changes a status; see import_decisions.py.

Reads, for one ontology directory (the repository's ontology/ by default, or a
temporary copy in the tests):
  * marsad.ttl and relations.ttl (vocabulary), every .ttl in corpus/ and examples/
    (the data, exactly the set build_graph.py loads, reviews.ttl included);
  * corpus/identity.csv (display names, identity rows) and corpus/id-renames.csv;
  * the private reviewer roster (import only; see load_roster).
No entity ID is written in this code: everything is looked up in the graph or the tables.
"""

from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from rdflib import RDF, RDFS, BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, PROV, SKOS

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "ontology"
MRS = Namespace("https://w3id.org/marsad/core#")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
BASE = "https://w3id.org/marsad/id/"
REVIEWS_FILE = "reviews.ttl"

# CURIE prefix -> IRI path segment, as the corpus files use them (docs/02 §5.2.1); rvw: is new in slice 3a.
SEGMENTS = {
    "per": "person", "plc": "place", "ev": "event", "grp": "group", "ast": "assertion", "agt": "agent",
    "act": "activity", "psg": "passage", "wit": "witness", "wrk": "work", "rpt": "report", "rvw": "review",
    "tmp": "temporal", "cvg": "coveragegap", "dsp": "dispute", "evl": "evaluation", "chn": "chain", "rte": "route",
}
PREFIX_OF = {seg: p for p, seg in SEGMENTS.items()}
PAYLOAD_RE = re.compile(r"^[0-9A-Za-z]{22}$")

STATUSES = ["proposed", "under_review", "accepted", "rejected", "superseded"]
OUTCOMES = {"accept": MRS.ro_accept, "reject": MRS.ro_reject, "needs_discussion": MRS.ro_needs_discussion}
OUTCOME_STATUS = {"accept": "accepted", "reject": "rejected", "needs_discussion": "under_review"}
CHECKS = {"report_in_source": MRS.rc_report_in_source, "chain_sound": MRS.rc_chain_sound,
          "summary_fair": MRS.rc_summary_fair, "identity": MRS.rc_identity}
QUESTIONS = {"same_as": MRS.ir_same_as, "distinct_from": MRS.ir_distinct_from}


def status_iri(name: str) -> URIRef:
    return MRS["as_" + name]


def status_name(iri) -> str | None:
    s = str(iri) if iri is not None else ""
    return s[len(str(MRS)) + 3:] if s.startswith(str(MRS) + "as_") else None


def key_of(mapping: dict, iri) -> str | None:
    return next((k for k, v in mapping.items() if v == iri), None)


def curie(iri) -> str:
    s = str(iri)
    if s.startswith(BASE):
        seg, _, payload = s[len(BASE):].partition("/")
        if seg in PREFIX_OF and payload:
            return f"{PREFIX_OF[seg]}:{payload}"
    if s.startswith(str(MRS)):
        return "mrs:" + s[len(str(MRS)):]
    return s


def expand(text: str) -> URIRef | None:
    """A CURIE (ast:Abc...) or a full al-Marsad IRI -> URIRef; None if it is neither."""
    text = (text or "").strip()
    if text.startswith(BASE):
        return URIRef(text)
    prefix, sep, payload = text.partition(":")
    if sep and prefix in SEGMENTS and PAYLOAD_RE.match(payload):
        return URIRef(f"{BASE}{SEGMENTS[prefix]}/{payload}")
    return None


def fold(text: str) -> str:
    """Lower case, no diacritics, for sorting and name matching."""
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).casefold()


def year_of(lexical: str) -> int | None:
    m = re.match(r"^(-?\d{1,6})-", str(lexical))
    return int(m.group(1)) if m else None


@dataclass
class Decision:
    """One mrs:ReviewDecision as recorded in reviews.ttl (or about to be)."""
    iri: URIRef
    target: URIRef
    reviewer: URIRef
    outcome: str
    checks: tuple = ()
    note: str | None = None
    citation: str | None = None
    day: str = ""
    status_before: str | None = None
    status_after: str | None = None
    question: str | None = None
    tradition: URIRef | None = None

    def content(self):
        """What makes two decisions by one reviewer on one target the same decision."""
        return (self.outcome, tuple(sorted(self.checks)), self.note or "", self.citation or "", self.day, self.question)

    def as_json(self) -> dict:
        return {"decision": self.outcome, "date": self.day, "reviewer_id": curie(self.reviewer),
                "checks": sorted(self.checks), "note": self.note, "citation": self.citation,
                "status_before": self.status_before, "status_after": self.status_after}


class Tree:
    """One ontology directory, parsed: the vocabulary, every data file and the tables."""

    def __init__(self, ontology: Path = ONTOLOGY):
        self.ontology = Path(ontology).resolve()
        self.corpus = self.ontology / "corpus"
        self.reviews_path = self.corpus / REVIEWS_FILE
        self.vocab = Graph()
        for name in ("marsad.ttl", "relations.ttl"):
            self.vocab.parse(self.ontology / name, format="turtle")
        self.data_files = sorted(self.corpus.glob("*.ttl")) + sorted((self.ontology / "examples").glob("*.ttl"))
        self.texts = {f: f.read_text(encoding="utf-8") for f in self.data_files}
        self.graphs = {f: Graph().parse(data=self.texts[f], format="turtle") for f in self.data_files}
        self.graph = Graph()
        self.graph += self.vocab
        for g in self.graphs.values():
            self.graph += g
        self.identity = self._read_csv(self.corpus / "identity.csv")
        self.renames = {r["old_id"]: r["new_id"] for r in self._read_csv(self.corpus / "id-renames.csv")}
        self.names = {}
        for row in self.identity:
            iri = expand(row["canonical_id"])
            if iri is not None:
                self.names[iri] = (row["preferred_name_en"], row.get("name_ar", ""))

    @staticmethod
    def _read_csv(path: Path) -> list[dict]:
        if not path.exists():
            return []
        with path.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def fingerprint(self) -> str:
        h = hashlib.sha256()
        for f in [self.ontology / "marsad.ttl", self.ontology / "relations.ttl", *self.data_files, self.corpus / "identity.csv"]:
            h.update(f.name.encode() + b"\0" + f.read_bytes() + b"\0")
        return "sha256:" + h.hexdigest()[:16]

    # ---- names and labels -------------------------------------------------
    def label(self, node, prop=RDFS.label) -> str | None:
        values = sorted(self.graph.objects(node, prop), key=lambda l: (getattr(l, "language", None) not in (None, "en"), str(l)))
        return str(values[0]) if values else None

    def name(self, node) -> tuple[str, str]:
        """(English display name, Arabic name or ''): identity.csv first, then the graph's labels."""
        if node in self.names:
            return self.names[node]
        return (self.label(node) or self.label(node, SKOS.prefLabel) or curie(node), "")

    def entity_json(self, node) -> dict:
        en, ar = self.name(node)
        return {"id": curie(node), "name": en, "name_ar": ar or None}

    # ---- assertions -------------------------------------------------------
    def assertions(self) -> list[URIRef]:
        return sorted(set(self.graph.subjects(RDF.type, MRS.Assertion)), key=str)

    def status(self, a) -> str | None:
        values = set(self.graph.objects(a, MRS.assertionStatus))
        return status_name(next(iter(values))) if len(values) == 1 else None

    def files_declaring_status(self, a) -> list[Path]:
        return [f for f, g in self.graphs.items() if (a, MRS.assertionStatus, None) in g]

    def source_of(self, a) -> str:
        files = self.files_declaring_status(a) or [f for f, g in self.graphs.items() if (a, RDF.type, MRS.Assertion) in g]
        return files[0].stem if files else "unknown"

    def topic_of(self, a) -> str:
        cls = self.graph.value(self.graph.value(a, MRS.predicate), MRS.relationClass)
        local = str(cls).rsplit("#", 1)[-1] if cls is not None else ""
        return local[len("relclass_"):].replace("_", "-") if local.startswith("relclass_") else "unclassified"

    def topics(self) -> set[str]:
        out = {"identity", "unclassified"}
        for c in set(self.vocab.objects(None, MRS.relationClass)):
            local = str(c).rsplit("#", 1)[-1]
            if local.startswith("relclass_"):
                out.add(local[len("relclass_"):].replace("_", "-"))
        return out

    def sources(self) -> set[str]:
        return {f.stem for f in self.data_files if f.name != REVIEWS_FILE}

    def period_of(self, a) -> tuple[int, int] | None:
        """CE years spanned by the dated events the claim is about (subject or object); None if undated."""
        years = []
        for node in (self.graph.value(a, MRS.assertionSubject), self.graph.value(a, MRS.assertionObject)):
            for te in self.graph.objects(node, MRS.eventTemporalExtent):
                for corner in (MRS.earliestStart, MRS.latestStart, MRS.earliestEnd, MRS.latestEnd):
                    years += [y for y in (year_of(v) for v in self.graph.objects(te, corner)) if y is not None]
        return (min(years), max(years)) if years else None

    def qualifiers(self, a) -> list[str]:
        return sorted(self.label(q) or curie(q) for q in self.graph.objects(a, MRS.qualifier))

    # ---- sources ----------------------------------------------------------
    def works_of(self, passage) -> set:
        works, todo, seen = set(), [passage], set()
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            if (n, RDF.type, MRS.Work) in self.graph:
                works.add(n)
            todo += list(self.graph.objects(n, DCTERMS.isPartOf)) + list(self.graph.objects(n, MRS.inWitness))
            todo += list(self.graph.objects(n, DCTERMS.isVersionOf))
        return works

    def ai_generated(self, work) -> bool:
        makers = set(self.graph.objects(work, DCTERMS.creator)) | set(self.graph.objects(work, PROV.wasAttributedTo))
        return any((m, RDF.type, PROV.SoftwareAgent) in self.graph for m in makers)

    def passage_ai(self, passage) -> bool:
        return any(self.ai_generated(w) for w in self.works_of(passage))

    def basis_passages(self, a) -> list:
        report = self.graph.value(a, MRS.fromReport)
        found = list(self.graph.objects(report, MRS.locatedIn)) if report is not None else []
        found += [p for p in self.graph.objects(a, PROV.wasDerivedFrom) if (p, RDF.type, MRS.Passage) in self.graph]
        return sorted(set(found), key=str)

    def has_real_source(self, a) -> bool:
        """True if the claim rests on a Report located in a Passage of a work not generated by AI."""
        report = self.graph.value(a, MRS.fromReport)
        if report is None:
            return False
        return any(not self.passage_ai(p) for p in self.graph.objects(report, MRS.locatedIn))

    def ai_basis(self, a) -> bool:
        """True if the claim's only basis is an AI-generated document (as with every 50 Stories link)."""
        return not self.has_real_source(a) and any(self.passage_ai(p) for p in self.basis_passages(a))

    def story_of(self, a):
        """The narrative passage a claim was derived from (a passage that refers to an event), if any."""
        for p in sorted(self.graph.objects(a, PROV.wasDerivedFrom), key=str):
            if any((ev, RDF.type, MRS.Event) in self.graph for ev in self.graph.objects(p, CRM.P67_refers_to)):
                return p
        return None

    def notation(self, node) -> int | None:
        for v in self.graph.objects(node, SKOS.notation):
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
        return None

    def passage_json(self, p) -> dict:
        texts = list(self.graph.objects(p, CRM.P190_has_symbolic_content))
        en = [str(t) for t in texts if getattr(t, "language", None) != "ar"]
        ar = [str(t) for t in texts if getattr(t, "language", None) == "ar"]
        works = sorted(self.works_of(p), key=str)
        return {"citation": self.label(p, MRS.canonicalCitation), "title": self.label(p),
                "text": en[0] if en else None, "text_ar": ar[0] if ar else None,
                "work": self.label(works[0]) if works else None, "ai_generated": self.passage_ai(p)}

    def basis_json(self, a) -> dict:
        report = self.graph.value(a, MRS.fromReport)
        passages = [curie(p) for p in self.basis_passages(a)]
        if report is not None:
            matn = list(self.graph.objects(report, MRS.matnText))
            return {"kind": "report", "report": curie(report), "report_label": self.label(report),
                    "matn_ar": next((str(m) for m in matn if getattr(m, "language", None) == "ar"), None),
                    "matn": next((str(m) for m in matn if getattr(m, "language", None) != "ar"), None),
                    "passages": passages}
        return {"kind": "non_report", "text": self.label(a, MRS.nonReportBasis), "passages": passages}

    # ---- the review log ---------------------------------------------------
    def log_node(self):
        logs = sorted(self.graph.subjects(RDF.type, MRS.ReviewLog), key=str)
        return logs[0] if logs else None

    def default_tradition(self) -> URIRef:
        found = [t for t, v in self.vocab.subject_objects(MRS.declaredDefault)
                 if isinstance(v, Literal) and v.toPython() is True]
        if len(found) != 1:
            raise SystemExit(f"error: marsad.ttl must declare exactly one default tradition (found {len(found)})")
        return found[0]

    def decisions(self) -> list[Decision]:
        g = self.graph
        out = []
        for d in g.subjects(RDF.type, MRS.ReviewDecision):
            def one(p):
                return g.value(d, p)
            out.append(Decision(
                iri=d, target=one(MRS.reviewTarget), reviewer=one(MRS.reviewedBy),
                outcome=key_of(OUTCOMES, one(MRS.reviewOutcome)),
                checks=tuple(sorted(k for k, v in CHECKS.items() if (d, MRS.checkPerformed, v) in g)),
                note=str(one(MRS.reviewNote)) if one(MRS.reviewNote) is not None else None,
                citation=str(one(MRS.sourceCitation)) if one(MRS.sourceCitation) is not None else None,
                day=str(one(MRS.reviewDate)) if one(MRS.reviewDate) is not None else "", status_before=status_name(one(MRS.statusBefore)),
                status_after=status_name(one(MRS.statusAfter)), question=key_of(QUESTIONS, one(MRS.identityQuestion)),
                tradition=one(MRS.tradition)))
        return sorted(out, key=lambda x: (x.day, str(x.target), str(x.reviewer), str(x.iri)))

    def decisions_by_target(self) -> dict:
        out = {}
        for d in self.decisions():
            out.setdefault(d.target, []).append(d)
        return out

    # ---- identity rows ----------------------------------------------------
    def identity_row(self, iri) -> dict | None:
        return next((r for r in self.identity if expand(r["canonical_id"]) == iri), None)


# ---------------------------------------------------------------------------
# Identity rows: which needs-review flags are ID bookkeeping, not identity questions
# ---------------------------------------------------------------------------
# A note is "|"-separated. A part matching one of these says the row is flagged for
# the slice-1a ID problems that slice 1d fixed (re-minted, see id-renames.csv), or
# only explains a merge/non-merge. Any other part is a real question and keeps the
# row in the queue (unknown notes are treated as real, never dropped).
ID_ONLY_NOTES = [
    (re.compile(r"^IRI nearly identical to "), "slice-1a ID collision (fixed by the slice 1d re-mint)"),
    (re.compile(r"^slice 1d \(.*\): ID re-minted"), "record of the slice 1d re-mint"),
    (re.compile(r"stays needs-review only for the ID collision"), "flag kept only for the ID collision"),
    (re.compile(r"stays needs-review \(ID minted in slice 1a by hash"), "slice-1a hash-minted ID (re-minted in slice 1d)"),
    (re.compile(r"^merged on shared normalised label: "), "label merge; alone it gives 'probable', not needs-review"),
    (re.compile(r"^placeholder label, never merged on name"), "explains why two placeholders were not merged"),
]


def note_flags(note: str) -> list[tuple[str, str | None]]:
    """[(note part, ID-only reason or None)]"""
    out = []
    for part in [p.strip() for p in (note or "").split("|") if p.strip()]:
        reason = next((why for rx, why in ID_ONLY_NOTES if rx.search(part)), None)
        out.append((part, reason))
    return out


def id_only(row: dict) -> bool:
    flags = note_flags(row.get("note", ""))
    return bool(flags) and all(reason for _, reason in flags) and any(
        "collision" in reason or "hash-minted" in reason for _, reason in flags)


# ---------------------------------------------------------------------------
# Scope: what a roster grant covers
# ---------------------------------------------------------------------------
# scope  := grant (";" grant)*        a unit is in scope if ANY grant matches it
# grant  := condition (" " condition)* every condition of the grant must hold
# condition:
#   source:STEM     the claim is declared in that data file (stories-50, generation-1, ...)
#   topic:NAME      the relation class of the claim's predicate (relations.ttl), or identity
#   period:A..B     the claim is about a dated event lying within CE years A..B (undated never matches)
SCOPE_RE = re.compile(r"^(source|topic|period):(\S+)$")


def parse_scope(text: str, topics: set, sources: set) -> list[list[tuple]]:
    grants = []
    for raw in (text or "").split(";"):
        conds = []
        for token in raw.split():
            m = SCOPE_RE.match(token)
            if not m:
                raise ValueError(f"scope condition {token!r} is not source:..., topic:... or period:A..B")
            facet, value = m.groups()
            if facet == "topic" and value not in topics:
                raise ValueError(f"unknown topic {value!r} (known: {', '.join(sorted(topics))})")
            if facet == "source" and value not in sources:
                raise ValueError(f"unknown source {value!r} (known: {', '.join(sorted(sources))})")
            if facet == "period":
                pm = re.match(r"^(-?\d+)\.\.(-?\d+)$", value)
                if not pm or int(pm.group(1)) > int(pm.group(2)):
                    raise ValueError(f"period {value!r} must be CE years A..B with A <= B")
                value = (int(pm.group(1)), int(pm.group(2)))
            conds.append((facet, value))
        if conds:
            grants.append(conds)
    return grants


def scope_matches(grants: list, facets: dict) -> bool:
    def holds(facet, value):
        if facet == "source":
            return value in facets["sources"]
        if facet == "topic":
            return value == facets["topic"]
        period = facets.get("period")
        return period is not None and value[0] <= period[0] and period[1] <= value[1]
    return any(all(holds(f, v) for f, v in grant) for grant in grants)


def describe_facets(facets: dict) -> str:
    period = facets.get("period")
    return (f"source {'/'.join(sorted(facets['sources']))}, topic {facets['topic']}, "
            f"period {'%d..%d' % period if period else 'undated'}")


# ---------------------------------------------------------------------------
# The private roster
# ---------------------------------------------------------------------------
ROSTER_COLUMNS = ["reviewer_id", "name", "role", "scope", "granted_on", "granted_by", "revoked_on"]
ROLES = ["reader", "contributor", "researcher", "reviewer", "scholar", "editor", "translator", "board"]  # docs/06 §3.1
DECIDING_ROLES = {"claim": {"reviewer", "scholar"}, "identity": {"reviewer", "scholar", "editor"}}


@dataclass
class Grant:
    reviewer: URIRef
    name: str
    role: str
    scope: list
    scope_text: str
    granted_on: date
    granted_by: str
    revoked_on: date | None = None

    def active_on(self, day: date) -> bool:
        return self.granted_on <= day and (self.revoked_on is None or day < self.revoked_on)


def parse_day(text: str, what: str) -> date:
    try:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", text or ""):
            raise ValueError
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{what} {text!r} is not a date (YYYY-MM-DD)") from None


def load_roster(path: Path, tree: Tree) -> dict:
    """reviewer IRI -> [Grant]. Raises ValueError with the row number on any problem."""
    path = Path(path)
    if not path.exists():
        raise ValueError(f"roster {path} not found. Copy review/roster.example.csv to review/roster.csv "
                         "(gitignored, never committed) and fill it in, or pass --roster")
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in ROSTER_COLUMNS[:-1] if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"roster {path.name}: missing column(s) {', '.join(missing)}")
        rows = list(reader)
    topics, sources = tree.topics(), tree.sources()
    out, names = {}, {}
    for n, row in enumerate(rows, start=2):
        row = {k: (v or "").strip() for k, v in row.items() if k}
        where = f"roster {path.name} row {n}"
        iri = expand(row["reviewer_id"])
        if iri is None or not row["reviewer_id"].startswith("agt:"):
            raise ValueError(f"{where}: reviewer_id {row['reviewer_id']!r} must be an agt: ID minted with ontology/tools/mint_id.py")
        if not row["name"]:
            raise ValueError(f"{where}: name is empty")
        if names.setdefault(iri, row["name"]) != row["name"]:
            raise ValueError(f"{where}: {row['reviewer_id']} has two different names in the roster")
        if row["role"] not in ROLES:
            raise ValueError(f"{where}: role {row['role']!r} is not one of {', '.join(ROLES)} (docs/06 §3.1)")
        if not row["granted_by"]:
            raise ValueError(f"{where}: granted_by is empty")
        try:
            scope = parse_scope(row["scope"], topics, sources)
            granted = parse_day(row["granted_on"], "granted_on")
            revoked = parse_day(row["revoked_on"], "revoked_on") if row.get("revoked_on") else None
        except ValueError as e:
            raise ValueError(f"{where}: {e}") from None
        if revoked and revoked < granted:
            raise ValueError(f"{where}: revoked_on is before granted_on")
        out.setdefault(iri, []).append(Grant(iri, row["name"], row["role"], scope, row["scope"], granted, row["granted_by"], revoked))
    return out


# ---------------------------------------------------------------------------
# reviews.ttl, written in one fixed layout so diffs stay readable
# ---------------------------------------------------------------------------
REVIEWS_PREFIXES = [("mrs", str(MRS)), ("prov", str(PROV)), ("rdfs", str(RDFS)),
                    ("xsd", "http://www.w3.org/2001/XMLSchema#")] + \
                   [(p, f"{BASE}{SEGMENTS[p]}/") for p in ("rvw", "agt", "ast", "per", "plc", "ev", "grp")]
REVIEWS_HEADER = """#################################################################
#
#  REVIEW DECISIONS (slice 3a) -- the review log
#
#  GENERATED by review/import_decisions.py from the decision files that
#  reviewers send. Do not edit by hand.
#
#  Each mrs:ReviewDecision is one reviewer's accept / reject / needs
#  discussion on one claim (or one identity question), with the checks
#  made, the note, the date, the real source cited if any, and the
#  status the claim moved from and to. Every status change is logged,
#  attributed and reversible (docs/06 §10). Only these decisions move
#  a claim's status; software never decides.
#
#  Reviewers appear by opaque ID only. Their names are kept in the
#  maintainer's private roster, which never enters this repository;
#  public pages say "Reviewed by the review board".
#
#################################################################
"""
REVIEWER_LABEL = "Reviewer for the review board (opaque ID; the name is held privately by the maintainer)"
LOG_LABEL = "Review log"
LOG_COMMENT = ("The review decisions of al-Marṣad's reviewers, by opaque reviewer ID, in the first review board's "
               "declared-default lens. Nothing in this file names a person.")


def turtle_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + '"'


def turtle_iri(iri) -> str:
    s = str(iri)
    for p, ns in REVIEWS_PREFIXES:
        local = s[len(ns):] if s.startswith(ns) else None
        if local and (PAYLOAD_RE.match(local) or (p == "mrs" and re.match(r"^\w+$", local))):
            return f"{p}:{local}"
    return f"<{s}>"


def render_reviews(log, reviewers, decisions: list[Decision]) -> str:
    out = [f"@prefix {p}:{' ' * (5 - len(p))}<{ns}> ." for p, ns in REVIEWS_PREFIXES]
    out += ["", REVIEWS_HEADER, f"{turtle_iri(log)}", "    a mrs:ReviewLog ;",
            f"    rdfs:label {turtle_string(LOG_LABEL)}@en ;", f"    rdfs:comment {turtle_string(LOG_COMMENT)}@en .", ""]
    if reviewers:
        out += ["# Reviewers: opaque IDs only.", ""]
        for r in sorted(reviewers, key=str):
            out += [turtle_iri(r), "    a prov:Person ;", f"    rdfs:label {turtle_string(REVIEWER_LABEL)}@en .", ""]
    if decisions:
        out += ["# Decisions, by date.", ""]
    for d in sorted(decisions, key=lambda x: (x.day, str(x.target), str(x.reviewer), str(x.iri))):
        lines = ["    a mrs:ReviewDecision", f"    mrs:reviewTarget {turtle_iri(d.target)}",
                 f"    mrs:reviewedBy {turtle_iri(d.reviewer)}", f"    mrs:reviewOutcome {turtle_iri(OUTCOMES[d.outcome])}"]
        if d.checks:
            lines.append("    mrs:checkPerformed " + " , ".join(turtle_iri(CHECKS[c]) for c in sorted(d.checks)))
        if d.question:
            lines.append(f"    mrs:identityQuestion {turtle_iri(QUESTIONS[d.question])}")
        if d.note:
            lines.append(f"    mrs:reviewNote {turtle_string(d.note)}")
        if d.citation:
            lines.append(f"    mrs:sourceCitation {turtle_string(d.citation)}")
        lines.append(f'    mrs:reviewDate "{d.day}"^^xsd:date')
        lines.append(f"    mrs:tradition {turtle_iri(d.tradition)}")
        if d.status_before:
            lines.append(f"    mrs:statusBefore {turtle_iri(status_iri(d.status_before))}")
        if d.status_after:
            lines.append(f"    mrs:statusAfter {turtle_iri(status_iri(d.status_after))}")
        out += [turtle_iri(d.iri), " ;\n".join(lines) + " .", ""]
    return "\n".join(out)


def strip_bnodes(g: Graph):
    plain = {t for t in g if not any(isinstance(x, BNode) for x in t)}
    return plain, len(g) - len(plain)


# ---------------------------------------------------------------------------
# Locating one triple's object in Turtle text (for the status edit)
# ---------------------------------------------------------------------------

def mask_turtle(text: str) -> str:
    """Same length as text, with string literal contents and comments blanked, IRIs kept."""
    out, i, n = list(text), 0, len(text)
    while i < n:
        c = text[i]
        if c == "<":
            j = text.find(">", i)
            i = n if j < 0 else j + 1
        elif c == "#":
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif c in "\"'":
            q = c * 3 if text.startswith(c * 3, i) else c
            j = i + len(q)
            while j < n and not text.startswith(q, j):
                j += 2 if text[j] == "\\" else 1
            end = min(n, j + len(q))
            for k in range(i + len(q), min(n, j)):
                if out[k] != "\n":
                    out[k] = " "
            i = end
        else:
            i += 1
    return "".join(out)


def statement_end(masked: str, start: int) -> int:
    depth, i, n = 0, start, len(masked)
    while i < n:
        c = masked[i]
        if c == "<":
            j = masked.find(">", i)
            i = n if j < 0 else j + 1
            continue
        if c in "[(":
            depth += 1
        elif c in "])":
            depth -= 1
        elif c == "." and depth == 0 and (i + 1 == n or masked[i + 1].isspace()):
            return i + 1
        i += 1
    return n


def file_prefixes(text: str) -> dict:
    return {p: ns for p, ns in re.findall(r"@prefix\s+([A-Za-z][\w-]*|):\s*<([^>]*)>\s*\.", text)}


def term_pattern(iri: str, prefixes: dict) -> str:
    alts = [re.escape(f"<{iri}>")]
    for p, ns in prefixes.items():
        if iri.startswith(ns) and re.match(r"^[\w-]+$", iri[len(ns):]):
            alts.append(re.escape(f"{p}:{iri[len(ns):]}") + r"(?![\w:-])")
    return "(?:" + "|".join(alts) + ")"


def locate_object(text: str, masked: str, subject: str, predicate: str, obj: str) -> list[tuple[int, int]]:
    """Spans of `obj` written as the object of (subject, predicate) at the top level of a statement about subject."""
    prefixes = file_prefixes(text)
    s_rx = re.compile(term_pattern(subject, prefixes))
    po_rx = re.compile(term_pattern(predicate, prefixes) + r"\s+(" + term_pattern(obj, prefixes) + r")")
    spans = []
    for m in s_rx.finditer(masked):
        before = masked[:m.start()].rstrip()
        if before and not before.endswith("."):
            continue  # not in subject position
        end = statement_end(masked, m.end())
        depth = 0
        pos = m.end()
        for pm in po_rx.finditer(masked, m.end(), end):
            seg = masked[pos:pm.start()]
            depth += seg.count("[") + seg.count("(") - seg.count("]") - seg.count(")")
            pos = pm.start()
            if depth == 0:
                spans.append(pm.span(1))
    return spans


def replace_term(text: str, span: tuple[int, int], new_iri: str) -> str:
    old = text[span[0]:span[1]]
    if old.startswith("<"):
        new = f"<{new_iri}>"
    else:
        prefix = old.split(":", 1)[0]
        ns = file_prefixes(text)[prefix]
        new = f"{prefix}:{new_iri[len(ns):]}"
    return text[:span[0]] + new + text[span[1]:]


FREE_TEXT_LIMITS = {"note": 4000, "citation": 500}
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\+\d[\d\s().-]{6,}\d")


def private_data_in(text: str, roster_names) -> str | None:
    """Why `text` may not enter the public record, or None."""
    folded = fold(text)
    for name in roster_names:
        if name and fold(name) in folded:
            return "a reviewer's name"
    if EMAIL_RE.search(text):
        return "an email address"
    if PHONE_RE.search(text):
        return "a phone number"
    return None

