"""Journeys: ordered walks through the graph, chosen by rules, never by hand.

A journey is a JSON file in learn/journeys/. It names no entity ID and holds no prose:
its title and lead are i18n keys, and its steps come from selection rules that this
module applies to build/graph.ttl (read through site/model.py, so every step links to
the same page the reader tier builds). The rule language is small on purpose; every
rule is printed in plain words on the journey's page, so a reviewer approves the rule,
not a hand-made list.

Three step types:
  events   events and stories whose recorded name contains a word (or a phrase, and
           none of the words a rule leaves out), plus the events the record links to
           them in the directions the rule names (their parts, their wholes, the events
           their own dates are placed against, other event-to-event claims), up to
           `max_links` links away.
           Order "recorded": recorded dates and before/after links decide; where the
           record says nothing, dated steps first, then story order, then name.
  people   people with a recorded participation in the events chosen as above.
           Other claims (for example "absent from") are shown beside, never used to
           choose. People whose every record carries a set-apart qualifier are listed
           apart. Order: the Prophet first (if present), then name; no ranking. Order
           "e3" (design §6) reads a list file of names (learn/journey_lists.py): until
           both approvers have reviewed it, it is the same order, the Prophet ﷺ, then
           A to Z. With group_by "side", the people recorded as fighting against the
           Prophet ﷺ at the event come after the others, as a labelled group.
  stories  the stories in a part of a story document whose title contains a word,
           with the people each story names. Order: the document's reading order.

Background (design §5): events recorded only after the Prophet's ﷺ death, events too
coarsely dated to place either side of it, and events before 570 are never chosen and
never walked through; background(site) is the one hook, and each journey lists what it
left out (Journey.excluded).

A journey is a draft until its file records the approval of both the maintainer and
the scholars' review board, each on the current hash of the rule (rule_sha). Software
never writes that approval, a status or a story-mode decision: load_specs returns
copies with the computed state, and nothing here writes a file.

The Sky Atlas imports this module (atlas/build.py, load_journeys). The names it uses
are kept: load_specs, build(site, spec, links=None), build_all, RuleError, Journey.steps
/ set_apart / anchors, Step.iri / reasons / records / contrary, Reason.kind (the v1
kinds) / other / word / label, and the Claim fields. New fields only have defaults.
"""
from __future__ import annotations

import copy
import datetime
import hashlib
import json
import re
import unicodedata
import weakref
from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Namespace, URIRef
from rdflib.namespace import RDFS

import display
from model import CRM, MRS, Claim, Entity, Site

FACADE_VERSION = 2                     # what the Atlas imports (design §11)

TIME = Namespace("http://www.w3.org/2006/time#")
MRSV = Namespace("https://w3id.org/marsad/vocab/")
PREFIXES = {"mrs": str(MRS), "mrsv": str(MRSV)}

HERE = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]   # list paths in a rule resolve against this, never the cwd
I18N_DIR = HERE / "i18n"

# Allen relations recorded on a relative date anchor that give an order.
BEFORE = {TIME.before, TIME.intervalBefore, TIME.intervalMeets}
AFTER = {TIME.after, TIME.intervalAfter, TIME.intervalMetBy}
# Event-to-event claims that give an order: subject before object, or after it.
CLAIM_BEFORE = {MRS.rel_preceded}
CLAIM_AFTER = {MRS.rel_followed}
# Claims that record a person's side at an event (design §6.4).
SIDE = {MRS.rel_fought_alongside: "alongside", MRS.rel_fought_against: "against"}
NOT_SHOWN = ("rejected", "superseded")   # statuses that never count for a group or at Discover

STEP_TYPES = ("events", "people", "stories")
EVENT_KINDS = ("event", "story")
FOLLOW = ("parts", "wholes", "date_anchors", "event_claims")   # see Links
ORDERS = {"events": ("recorded",), "people": ("prophet_first_then_name", "name", "e3"), "stories": ("story",)}
DOORS = ("study", "discover")          # study: evidence first; discover: story first (R9)
APPROVERS = ("maintainer", "review_board")
JOURNEY_KINDS = ("official",)          # method journeys and teacher lessons are not files here (§4)
GROUP_BY = ("side",)
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED_SLUGS = ("assets", "practice", "data")   # folders of site/dist/learn/ that are not journeys
KEY = re.compile(r"^[a-z_]+(?:\.[a-z0-9_]+)+$")
DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
WORD = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")       # a word that tokens() can produce
HEX12 = re.compile(r"^[0-9a-f]{12}$")
LISTS_PATH = re.compile(r"^[a-z0-9_-]+(/[a-z0-9_.-]+)*\.json$")
NOTE_MAX = 300
TEXT_ROLES = ("title", "lead", "lead_study")       # the i18n texts a rule_sha covers
LAYER_KEYS = ("status", "approved_by", "story_mode", "hold_study")   # outside rule_sha
RESERVED_LAST = ("last_if", "last")
ROUND4_Q2 = ("is reserved: a 'died as a disbeliever, last' rule waits for round 4 Q2. No recorded term "
             "exists yet, and rel_fought_against, rel_opposed and q_accepted_islam_later are not proxies for it")

# Words that are review language: never on a Discover page (design §8), never in a list source.
REVIEW_WORDS = ("review", "reviewed", "reviewing", "check", "checked", "checking", "proposed", "accepted",
                "approved", "approval", "draft", "status", "scholar", "scholars", "board", "verified",
                "unverified", "authenticity", "pending")
AR_REVIEW_STEMS = ("مراجع", "مسود", "حالة", "مقترح", "مقبول", "علماء", "تحقق", "اعتماد")

# Background (design §5).
BACKGROUND_MARKER: str | None = None   # slice 11b's background property, once 11b names it
BACKGROUND_BEFORE = "0570-01-01"       # every extent ends before this: background
AFTER_FALLBACK = "0632-12-31"          # the after bound when the record gives none
DEATH_OF_THE_PROPHET = ("death", "of", "the", "prophet")   # whole token sequence (tokens() drops ﷺ)
NOT_PLACED = {"coarser_than": "day", "contains": "after_bound"}


class RuleError(ValueError):
    """A journey file that does not follow the rule language."""


# --------------------------------------------------------------------------- canonical form and hashes
def nfc(obj):
    """Every string NFC-normalised, dictionary keys included."""
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {nfc(k): nfc(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [nfc(v) for v in obj]
    return obj


def canonical(obj) -> bytes:
    """The one byte form every hash in learn uses (design §3.5)."""
    return json.dumps(nfc(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha12(obj) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()[:12]


def review_words(text: str) -> list[str]:
    """The REVIEW_WORDS that occur as whole words in the text (folded, lower case)."""
    toks = set(re.findall(r"[a-z]+", display.fold(text or "").lower()))
    return [w for w in REVIEW_WORDS if w in toks]


def ar_review_stems(text: str) -> list[str]:
    return [s for s in AR_REVIEW_STEMS if s in (text or "")]


# --------------------------------------------------------------------------- the rule file
def _keys(d: dict, allowed: set, required: set, where: str):
    if not isinstance(d, dict):
        raise RuleError(f"{where}: expected an object")
    extra, missing = set(d) - allowed, required - set(d)
    if extra:
        raise RuleError(f"{where}: unknown key(s) {sorted(extra)}")
    if missing:
        raise RuleError(f"{where}: missing key(s) {sorted(missing)}")


def refuse_reserved(obj, where: str):
    """'last_if' and 'last' are reserved anywhere in a rule or list file (design §3.9)."""
    if isinstance(obj, dict):
        for k in sorted(obj, key=str):
            if k in RESERVED_LAST:
                raise RuleError(f"{where}: '{k}' {ROUND4_Q2}")
            refuse_reserved(obj[k], f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            refuse_reserved(v, f"{where}[{i}]")


def _words(v, where: str, what: str = "words") -> list[str]:
    if not isinstance(v, list) or not v or not all(isinstance(w, str) and WORD.match(w) for w in v):
        raise RuleError(f"{where}: '{what}' must be a non-empty list of plain words (a letter, then letters "
                        "or digits), since a name is matched word by word")
    return v


def _named(d: dict, where: str):
    _keys(d, {"kinds", "words", "phrase", "not_words"}, {"kinds"}, where)
    kinds = d["kinds"]
    if (not isinstance(kinds, list) or not kinds or not all(isinstance(k, str) and k in EVENT_KINDS for k in kinds)
            or len(set(kinds)) != len(kinds)):
        raise RuleError(f"{where}: kinds must be distinct values from {EVENT_KINDS}")
    if "words" not in d and "phrase" not in d:
        raise RuleError(f"{where}: give 'words' (any of them) or a 'phrase' (in this order)")
    for k in ("words", "phrase", "not_words"):
        if k in d:
            _words(d[k], where, k)


def _event_rule(d: dict, where: str):
    _keys(d, {"named", "follow", "max_links"}, {"named", "follow", "max_links"}, where)
    _named(d["named"], f"{where}.named")
    follow = d["follow"]
    if (not isinstance(follow, list) or not all(isinstance(f, str) and f in FOLLOW for f in follow)
            or len(set(follow)) != len(follow)):
        raise RuleError(f"{where}: follow must be a list of distinct directions from {FOLLOW}")
    if not isinstance(d["max_links"], int) or isinstance(d["max_links"], bool) or not 0 <= d["max_links"] <= 3:
        raise RuleError(f"{where}: max_links must be an integer from 0 to 3")
    if bool(follow) != bool(d["max_links"]):
        raise RuleError(f"{where}: give both directions to follow and max_links above 0, or neither")


def term(curie: str, where: str) -> URIRef:
    """'mrs:rel_led' -> the IRI. Only ontology and vocabulary terms; never an entity."""
    if not isinstance(curie, str):
        raise RuleError(f"{where}: {curie!r} is not an ontology term like 'mrs:rel_led'")
    m = re.fullmatch(r"(mrs|mrsv):([A-Za-z_][A-Za-z0-9_]*)", curie)
    if not m:
        raise RuleError(f"{where}: {curie!r} is not an ontology term like 'mrs:rel_led'")
    return URIRef(PREFIXES[m.group(1)] + m.group(2))


def _date(v, where: str):
    if not isinstance(v, str) or not DATE.fullmatch(v):
        raise RuleError(f"{where}: date must be written YYYY-MM-DD")
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        raise RuleError(f"{where}: {v!r} is not a date in the calendar") from None


def approvals(v, where: str, *, sha_key: str = "spec", sha_required: bool = False) -> list[dict]:
    """Check approval entries (who, date, the hash under sha_key, an optional note): each
    approver once, a real date, the 12 hex digits of what was approved, a short note."""
    if not isinstance(v, list):
        raise RuleError(f"{where}: must be a list")
    seen = set()
    for i, a in enumerate(v):
        at = f"{where}[{i}]"
        _keys(a, {"who", "date", sha_key, "note"}, {"who", "date"} | ({sha_key} if sha_required else set()), at)
        if not isinstance(a["who"], str) or a["who"] not in APPROVERS:
            raise RuleError(f"{at}: who must be one of {APPROVERS}")
        if a["who"] in seen:
            raise RuleError(f"{at}: {a['who']} is recorded twice")
        seen.add(a["who"])
        _date(a["date"], at)
        if sha_key in a and (not isinstance(a[sha_key], str) or not HEX12.fullmatch(a[sha_key])):
            raise RuleError(f"{at}: {sha_key} must be the 12 hex digits that build_learn prints")
        if "note" in a and (not isinstance(a["note"], str) or len(a["note"]) > NOTE_MAX):
            raise RuleError(f"{at}: note must be a text of at most {NOTE_MAX} characters")
    return v


def _kind(kind, where: str):
    if kind == "method":
        raise RuleError(f"{where}: method journeys go in learn/journeys/method/ (deferred), not here")
    if kind == "teacher":
        raise RuleError(f"{where}: a teacher's lesson is never a file in this repository (design §4.3)")
    if kind not in JOURNEY_KINDS:
        raise RuleError(f"{where}: kind must be one of {JOURNEY_KINDS}")


TOP_REQUIRED = {"slug", "status", "approved_by", "title", "lead", "door", "select", "order"}
TOP_OPTIONAL = {"kind", "lead_study", "story_mode", "lists", "hold_study"}


def validate(spec: dict, stem: str | None = None) -> dict:
    """Check a journey file against the rule language (v1 keys plus the optional v2
    keys). Checks shape only: a missing list file is a problem for build(), never here.
    Returns the spec."""
    if not isinstance(spec, dict):
        raise RuleError("journey: expected an object")
    refuse_reserved(spec, "journey")
    if "kind" in spec:
        _kind(spec["kind"], "journey")
    _keys(spec, TOP_REQUIRED | TOP_OPTIONAL, TOP_REQUIRED, "journey")
    slug = spec["slug"]
    if not isinstance(slug, str) or not SLUG.match(slug) or slug in RESERVED_SLUGS:
        raise RuleError(f"slug {slug!r} must be lower-case words joined by hyphens, and not {RESERVED_SLUGS}")
    if stem is not None and stem != slug:
        raise RuleError(f"{slug}: the file must be named {slug}.json")
    for k in TEXT_ROLES:
        if k in spec and (not isinstance(spec[k], str) or not KEY.match(spec[k])):
            raise RuleError(f"{slug}: {k} must be an i18n key")
    if spec["door"] not in DOORS:
        raise RuleError(f"{slug}: door must be one of {DOORS}")
    approved = approvals(spec["approved_by"], f"{slug}.approved_by")
    if spec["status"] not in ("draft", "approved"):
        raise RuleError(f"{slug}: status must be draft or approved")
    if spec["status"] == "approved" and {a["who"] for a in approved} != set(APPROVERS):
        raise RuleError(f"{slug}: approved needs a recorded approval from both {APPROVERS}")
    if "story_mode" in spec:
        sm = spec["story_mode"]
        _keys(sm, {"open", "approved_by"}, {"open", "approved_by"}, f"{slug}.story_mode")
        if not isinstance(sm["open"], bool):
            raise RuleError(f"{slug}.story_mode: open must be true or false")
        approvals(sm["approved_by"], f"{slug}.story_mode.approved_by")
        if sm["open"] and not any(a["who"] == "review_board" for a in sm["approved_by"]):
            raise RuleError(f"{slug}.story_mode: open needs a review_board approval")
    if "hold_study" in spec and not isinstance(spec["hold_study"], bool):
        raise RuleError(f"{slug}: hold_study must be true or false")
    sel = spec["select"]
    if not isinstance(sel, dict) or sel.get("type") not in STEP_TYPES:
        raise RuleError(f"{slug}: select.type must be one of {STEP_TYPES}")
    t = sel["type"]
    if t == "events":
        rest = {k: v for k, v in sel.items() if k != "type"}
        _event_rule(rest, f"{slug}.select")
    elif t == "people":
        _keys(sel, {"type", "events", "participation", "also_show", "set_apart", "group_by"},
              {"type", "events", "participation", "also_show", "set_apart"}, f"{slug}.select")
        _event_rule(sel["events"], f"{slug}.select.events")
        p = sel["participation"]
        _keys(p, {"records", "claims"}, {"records", "claims"}, f"{slug}.select.participation")
        if not isinstance(p["records"], bool) or not all(isinstance(x, list) for x in
                                                        (p["claims"], sel["also_show"], sel["set_apart"])):
            raise RuleError(f"{slug}.select: records is true/false; claims, also_show and set_apart are lists")
        for c in p["claims"] + sel["also_show"] + sel["set_apart"]:
            term(c, f"{slug}.select")
        if not p["records"] and not p["claims"]:
            raise RuleError(f"{slug}.select.participation: nothing would choose a person")
        if "group_by" in sel and (not isinstance(sel["group_by"], str) or sel["group_by"] not in GROUP_BY):
            raise RuleError(f"{slug}.select: group_by must be one of {GROUP_BY}")
    else:
        _keys(sel, {"type", "part"}, {"type", "part"}, f"{slug}.select")
        _keys(sel["part"], {"words"}, {"words"}, f"{slug}.select.part")
        _words(sel["part"]["words"], f"{slug}.select.part")
    if not isinstance(spec["order"], str) or spec["order"] not in ORDERS[t]:
        raise RuleError(f"{slug}: order for {t} must be one of {ORDERS[t]}")
    if (spec["order"] == "e3") != ("lists" in spec):
        raise RuleError(f"{slug}: 'lists' names the list file of order e3; give it exactly when order is e3")
    if "lists" in spec:
        p = spec["lists"]
        if not isinstance(p, str) or not LISTS_PATH.fullmatch(p) or ".." in p:
            raise RuleError(f"{slug}: lists must be a repository-relative path to a .json file, like "
                            "learn/lists/people.json")
    return spec


# --------------------------------------------------------------------------- approvals bound to the rule
def lists_file(spec: dict, lists_root: Path | str | None = None) -> Path | None:
    """The list file a rule names, resolved against the repository root (or lists_root)."""
    if not spec.get("lists"):
        return None
    return Path(lists_root if lists_root is not None else REPO_ROOT) / spec["lists"]


def lists_sha(spec: dict, *, lists_root: Path | str | None = None) -> str | None:
    """sha12 of the list file's "lists" array; "missing" or "unreadable" when it cannot
    be had; None when the rule names no list file. Never raises."""
    path = lists_file(spec, lists_root)
    if path is None:
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "missing"
    except (OSError, UnicodeDecodeError):
        return "unreadable"
    try:
        data = json.loads(raw)
    except ValueError:
        return "unreadable"
    if not isinstance(data, dict) or not isinstance(data.get("lists"), list):
        return "unreadable"
    return sha12(data["lists"])


def load_i18n(folder: Path | str = I18N_DIR) -> dict:
    """{"en": {...}, "ar": {...}}: the learn strings; a missing or broken file reads as empty."""
    out = {}
    for lang in ("en", "ar"):
        try:
            table = json.loads((Path(folder) / f"{lang}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            table = {}
        out[lang] = table if isinstance(table, dict) else {}
    return out


def check_i18n(i18n) -> dict:
    """`i18n` as load_i18n() gives it, {"en": {...}, "ar": {...}}, or a TypeError. A flat key
    table (the en table the Atlas reads, and that atlas_projection takes) has no "en" or
    "ar" key, so it would give rule_sha, the hash approvals are bound to, without its
    wording, and with no error."""
    if not (isinstance(i18n, dict) and set(i18n) == {"en", "ar"}
            and all(isinstance(i18n[lang], dict) for lang in ("en", "ar"))):
        got = sorted(map(str, i18n))[:3] if isinstance(i18n, dict) else type(i18n).__name__
        raise TypeError(f"i18n must be {{'en': {{...}}, 'ar': {{...}}}} as journeys.load_i18n() gives it, "
                        f"not a flat key table (got {got!r})")
    return i18n


def rule_sha(spec: dict, *, lists_root: Path | str | None = None, i18n: dict | None = None) -> str:
    """The hash an approval is bound to: the rule without its approval layer, the en and
    ar wording of its title and leads, and the content of its list file (design §3.5).
    `i18n` is {"en": {...}, "ar": {...}} (load_i18n()); any other shape raises TypeError."""
    i18n = load_i18n() if i18n is None else check_i18n(i18n)
    en, ar = i18n.get("en") or {}, i18n.get("ar") or {}
    rule = {k: v for k, v in spec.items() if k not in LAYER_KEYS}
    strings = {"en": {r: en.get(spec[r]) for r in TEXT_ROLES if r in spec},
               "ar": {r: ar[spec[r]] for r in TEXT_ROLES if r in spec and spec[r] in ar}}
    return sha12({"spec": rule, "strings": strings, "lists": lists_sha(spec, lists_root=lists_root)})


def _approved_on(entries, sha: str) -> set[str]:
    return {a.get("who") for a in entries or [] if isinstance(a, dict) and a.get("spec") == sha}


def _state(spec: dict, sha: str) -> str:
    ok = spec.get("status") == "approved" and set(APPROVERS) <= _approved_on(spec.get("approved_by"), sha)
    return "approved" if ok else "draft"


def _story_mode(spec: dict, sha: str) -> dict:
    sm = spec.get("story_mode") or {}
    declared = sm.get("open") is True
    opened = declared and any(isinstance(a, dict) and a.get("who") == "review_board" and a.get("spec") == sha
                              for a in sm.get("approved_by") or [])
    return {"open": opened, "stale": declared and not opened, "approved_by": copy.deepcopy(sm.get("approved_by") or [])}


def state(spec: dict, *, lists_root: Path | str | None = None, i18n: dict | None = None) -> str:
    """"approved" only when the file says so and both roles approved the current rule_sha."""
    return _state(spec, rule_sha(spec, lists_root=lists_root, i18n=i18n))


def stale_approval(spec: dict, *, lists_root: Path | str | None = None, i18n: dict | None = None) -> bool:
    """True when an approval is recorded for something other than the current rule."""
    sha = rule_sha(spec, lists_root=lists_root, i18n=i18n)
    return any(not isinstance(a, dict) or a.get("spec") != sha for a in spec.get("approved_by") or [])


def story_mode(spec: dict, *, lists_root: Path | str | None = None, i18n: dict | None = None) -> dict:
    """{open, stale, approved_by}: open only with a review_board record on the current rule_sha."""
    return _story_mode(spec, rule_sha(spec, lists_root=lists_root, i18n=i18n))


def load_specs(folder: Path, *, lists_root: Path | str | None = None) -> list[dict]:
    """Every official journey file directly in `folder` (never a subfolder), validated.
    Returns copies whose "status" is the computed state and whose "story_mode" is the
    computed {open, stale, approved_by}. A missing or broken list file makes a journey
    a draft here; build() is where it raises."""
    i18n = load_i18n()
    specs = []
    for path in sorted(Path(folder).glob("*.json")):
        if not path.is_file():
            continue
        spec = validate(json.loads(path.read_text(encoding="utf-8")), path.stem)
        sha = rule_sha(spec, lists_root=lists_root, i18n=i18n)
        out = copy.deepcopy(spec)
        out["status"] = _state(spec, sha)
        out["story_mode"] = _story_mode(spec, sha)
        specs.append(out)
    slugs = [s["slug"] for s in specs]
    if len(slugs) != len(set(slugs)):
        raise RuleError("two journeys share a slug")
    return specs


# --------------------------------------------------------------------------- results
@dataclass
class Reason:
    """Why a step is in the journey: a matched word, or a link to another step."""
    kind: str   # named | part_of | has_part | date_after | date_before | date_related | dated_after_this |
                # dated_before_this | dated_related_this | event_claim | part
    other: str | None = None       # IRI of the linked entity
    word: str | None = None        # the matched word or phrase (named) or part title (part)
    label: str | None = None       # relation label for event_claim (data string)
    claims: list[Claim] = field(default_factory=list)   # the claims behind the link, with status


@dataclass
class Step:
    entity: Entity
    reasons: list[Reason] = field(default_factory=list)  # why it was chosen
    links: list[Reason] = field(default_factory=list)    # its other recorded links to steps of the journey
    records: list[Claim] = field(default_factory=list)   # people: records that choose them; stories: people named
    contrary: list[Claim] = field(default_factory=list)  # shown beside, never used to choose
    order_note: str | None = None  # None (first) | part | recorded | unrecorded
    order_ref: str | None = None   # IRI of the step the note refers to
    hop: int = 0
    # v2, people steps only; defaults elsewhere
    side: list[Claim] = field(default_factory=list)      # cited side claims at the anchors, this person as subject
    group: str = "main"            # main | against (group_by "side")
    side_conflict: bool = False    # recorded on both sides at the anchors; kept in main
    e3: dict | None = None         # order e3: {tier, pos, links, accepted_islam}

    @property
    def iri(self) -> str:
        return self.entity.iri


@dataclass
class Group:
    """A run of steps under one heading: steps[start:end]."""
    key: str                       # main | against
    start: int
    end: int
    t: str | None = None           # i18n key of the heading
    lead: str | None = None        # i18n key of the lead


@dataclass
class Journey:
    spec: dict
    steps: list[Step]
    set_apart: list[Step] = field(default_factory=list)
    anchors: list[str] = field(default_factory=list)     # IRIs of the events a people journey hangs on
    part_labels: list[str] = field(default_factory=list)  # stories journey: the matching part titles
    universe: int = 0              # how many entities of the step kind(s) the record holds
    mixes_stories_and_events: bool = False
    order_conflict: bool = False   # the record's order links contradicted each other
    # v2
    excluded: list[tuple[str, str]] = field(default_factory=list)  # (IRI, background reason) a rule would have chosen
    groups: list[Group] = field(default_factory=list)  # group_by: the groups, in order; else empty
    order_applied: str | None = None   # the order used: spec order, or e3_pending while the list is not reviewed
    lists: dict | None = None      # order e3: the list file's state, sha, sources and members

    @property
    def slug(self) -> str:
        return self.spec["slug"]

    @property
    def is_draft(self) -> bool:
        return self.spec["status"] != "approved"


# --------------------------------------------------------------------------- helpers
def token_seq(label: str) -> list[str]:
    """The folded, lower-cased words of a label, in order (signs such as ﷺ are not words)."""
    return re.findall(r"[a-z0-9]+", display.fold(label).lower())


def tokens(label: str) -> set[str]:
    return set(token_seq(label))


def labels_of(site: Site, iri: str) -> list[str]:
    return sorted(str(lab) for lab in site.g.objects(URIRef(iri), RDFS.label))


def _has_run(seq: list[str], run: list[str]) -> bool:
    n = len(run)
    return any(seq[i:i + n] == run for i in range(len(seq) - n + 1))


def name_matches(site: Site, iri: str, words: list[str] | None, phrase: list[str] | None = None,
                 not_words: list[str] | None = None) -> str | None:
    """The first rule word found as a whole word in any recorded label of the entity, or
    the phrase (joined by spaces) found as a run of words in one label. None when no
    label matches, or when any label holds one of the not_words."""
    seqs = [token_seq(lab) for lab in labels_of(site, iri)]
    toks = set().union(*seqs) if seqs else set()
    if not_words and any(w.lower() in toks for w in not_words):
        return None
    for w in words or ():
        if w.lower() in toks:
            return w
    if phrase:
        run = [w.lower() for w in phrase]
        if any(_has_run(s, run) for s in seqs):
            return " ".join(phrase)
    return None


def claim_node(site: Site, c: Claim, prop):
    return site.g.value(URIRef(c.node), prop) if c.node else None


def claim_qualifiers(site: Site, c: Claim) -> set[URIRef]:
    return set(site.g.objects(URIRef(c.node), MRS.qualifier)) if c.node else set()


def claim_statuses(site: Site, c: Claim) -> set[str]:
    """Every status recorded on an assertion (a claim can carry more than one)."""
    if not c.node:
        return set()
    return {site.vkey(s, "as_") for s in site.g.objects(URIRef(c.node), MRS.assertionStatus)}


def side_of(site: Site, c: Claim) -> str | None:
    """"alongside" or "against" for a side claim, else None."""
    return SIDE.get(claim_node(site, c, MRS.predicate))


def _bounds(ent: Entity) -> tuple[str | None, str | None]:
    """Earliest recorded start and latest recorded end over all the entity's dates."""
    lo = hi = None
    for x in ent.data.get("dates") or []:
        e, l = x.get("earliest"), x.get("latest")
        if not e or not l:
            continue
        lo = e if lo is None or e < lo else lo
        hi = l if hi is None or l > hi else hi
    return lo, hi


def _iso_key(s: str) -> tuple:
    """Sort key for xsd:dateTime text, with negative years before positive ones."""
    m = re.match(r"^(-?)(\d+)-(\d\d)-(\d\d)(.*)$", s)
    if not m:
        return (0, s)
    year = int(m.group(2)) * (-1 if m.group(1) else 1)
    return (year, m.group(3), m.group(4), m.group(5))


def _day(s: str | None) -> tuple[int, int, int] | None:
    """(year, month, day) of an xsd:date or dateTime text; None when it is not one."""
    m = re.match(r"^(-?)(\d+)-(\d\d)-(\d\d)", s or "")
    if not m:
        return None
    return (int(m.group(2)) * (-1 if m.group(1) else 1), int(m.group(3)), int(m.group(4)))


def _day_text(d: tuple[int, int, int]) -> str:
    return f"{'-' if d[0] < 0 else ''}{abs(d[0]):04d}-{d[1]:02d}-{d[2]:02d}"


# --------------------------------------------------------------------------- background (F11)
_BACKGROUND: "weakref.WeakKeyDictionary[Site, dict]" = weakref.WeakKeyDictionary()


def _after_bound(site: Site) -> tuple[tuple[int, int, int], str]:
    """The day after which an event is background, and where it comes from: the one dated
    event the Prophet ﷺ is recorded as dying during (any status); else the one dated event
    whose whole token sequence is 'death of the prophet'; else AFTER_FALLBACK."""
    died = set()
    for p in site.by_kind["person"]:
        if not p.prophet:
            continue
        for c in site.claims.get(p.iri, []):
            if (c.kind == "assertion" and c.subject == p.iri
                    and claim_node(site, c, MRS.predicate) == MRS.rel_died_during):
                e = site.entity(c.object)
                if e is not None and e.kind in EVENT_KINDS and _day(_bounds(e)[1]):
                    died.add(e.iri)
    if len(died) == 1:
        return _day(_bounds(site.entity(next(iter(died))))[1]), "recorded_death"
    named = [e for e in site.by_kind["event"] if _day(_bounds(e)[1])
             and any(token_seq(lab) == list(DEATH_OF_THE_PROPHET) for lab in labels_of(site, e.iri))]
    if len(named) == 1:
        return _day(_bounds(named[0])[1]), "named_event"
    return _day(AFTER_FALLBACK), "fallback"


def _background_reason(e: Entity, bound: tuple[int, int, int]) -> str | None:
    exts = [x for x in e.data.get("dates") or []]
    if not exts:
        return None
    starts = [_day(x.get("earliest")) for x in exts]
    ends = [_day(x.get("latest")) for x in exts]
    if all(s is not None and s > bound for s in starts):
        return "after_prophet"
    if e.kind == "event" and all(x.get("precision") != NOT_PLACED["coarser_than"] and s is not None
                                 and en is not None and s <= bound <= en for x, s, en in zip(exts, starts, ends)):
        return "not_placed"
    if all(en is not None and en < _day(BACKGROUND_BEFORE) for en in ends):
        return "before"
    return None


def _background(site: Site) -> dict:
    cache = _BACKGROUND.setdefault(site, {})
    if BACKGROUND_MARKER not in cache:
        bound, source = _after_bound(site)
        flags: dict[str, str] = {}
        marker = URIRef(BACKGROUND_MARKER) if BACKGROUND_MARKER else None
        for kind in sorted(site.by_kind):
            for e in site.by_kind[kind]:
                if marker is not None and site.g.value(URIRef(e.iri), marker) is not None:
                    flags[e.iri] = "marker"
                elif kind in EVENT_KINDS:
                    r = _background_reason(e, bound)
                    if r:
                        flags[e.iri] = r
        cache[BACKGROUND_MARKER] = {"flags": flags, "info": {
            "marker": BACKGROUND_MARKER, "after_source": source, "after_bound": _day_text(bound),
            "before": BACKGROUND_BEFORE, "not_placed": dict(NOT_PLACED)}}
    return cache[BACKGROUND_MARKER]


def background(site: Site) -> dict[str, str]:
    """{IRI: reason} for every background entity: marker | after_prophet | not_placed | before.
    Computed once per Site. People are background only by the marker."""
    return _background(site)["flags"]


def background_info(site: Site) -> dict:
    """The background rule as applied to this graph: marker, after_source
    (recorded_death | named_event | fallback), after_bound, before, not_placed."""
    return copy.deepcopy(_background(site)["info"])


def _excluded_list(site: Site, excluded: dict[str, str]) -> list[tuple[str, str]]:
    def key(iri):
        e = site.entity(iri)
        return (display.sort_key(e.name) if e else iri, e.pid if e else iri)
    return [(iri, excluded[iri]) for iri in sorted(excluded, key=key)]


# --------------------------------------------------------------------------- event links
class Links:
    """Every recorded link between two event or story entities.

    Each link can be walked in a named direction, and a rule says which directions to
    follow (FOLLOW): from a whole to its "parts", from a part to its "wholes", from an
    event to the events its own recorded date is placed against ("date_anchors"), and
    either way along any other event-to-event claim ("event_claims"). A date anchor is
    never walked backwards: that a later event is dated "after the Hijra" does not make
    it a step of the Hijra. Background entities (background(site)) are kept here as
    `background` and are never walked to or through.
    """

    def __init__(self, site: Site):
        self.site = site
        g = site.g
        self.background = background(site)
        self.events = {e.iri for k in EVENT_KINDS for e in site.by_kind[k]}
        self.adj: dict[str, list[tuple[str, str, Reason]]] = {}     # iri -> [(other, direction, reason shown on other)]
        self.about: dict[str, list[tuple[str, Reason]]] = {}        # iri -> [(other, reason shown on iri)]
        self.order: list[tuple[str, str, str]] = []                  # (before, after, kind)
        self.whole_of: dict[str, set[str]] = {}                      # part -> wholes
        # part-of claims and other event-to-event claims
        self.by_node: dict[str, Claim] = {}
        for cs in site.claims.values():
            for c in cs:
                if c.kind == "assertion" and c.node:
                    self.by_node[c.node] = c
        for node in sorted(self.by_node):
            c = self.by_node[node]
            if c.subject not in self.events or c.object not in self.events or c.subject == c.object:
                continue
            pred = g.value(URIRef(node), MRS.predicate)
            if pred == MRS.rel_part_of:
                self._part(c.subject, c.object, [c])
            else:
                self._add(c.subject, c.object, "event_claims", "event_claims",
                          Reason("event_claim", other=c.subject, label=c.predicate, claims=[c]),
                          Reason("event_claim", other=c.object, label=c.predicate, claims=[c]))
                if pred in CLAIM_BEFORE:
                    self.order.append((c.subject, c.object, "claim"))
                elif pred in CLAIM_AFTER:
                    self.order.append((c.object, c.subject, "claim"))
        # plain part-of triples (no status of their own)
        for s, o in sorted(g.subject_objects(CRM.P9i_forms_part_of), key=lambda t: (str(t[0]), str(t[1]))):
            s, o = str(s), str(o)
            if s in self.events and o in self.events and s != o and o not in self.whole_of.get(s, set()):
                self._part(s, o, [])
        # relative date anchors recorded on an event's date
        for ev in sorted(self.events):
            for te in sorted(g.objects(URIRef(ev), MRS.eventTemporalExtent), key=str):
                anchors = sorted(g.objects(te, MRS.relativeAnchor),
                                 key=lambda n: (str(g.value(n, MRS.anchorTarget)), str(g.value(n, MRS.allenRelation))))
                for ra in anchors:
                    target = g.value(ra, MRS.anchorTarget)
                    rel = g.value(ra, MRS.allenRelation)
                    if target is None or str(target) not in self.events or str(target) == ev:
                        continue
                    claims = self.claims_for(g.objects(ra, MRS.attestedBy))
                    t = str(target)
                    if rel in AFTER:
                        self.order.append((t, ev, "anchor"))
                        kind_ev, kind_t = "date_after", "dated_after_this"
                    elif rel in BEFORE:
                        self.order.append((ev, t, "anchor"))
                        kind_ev, kind_t = "date_before", "dated_before_this"
                    else:
                        kind_ev, kind_t = "date_related", "dated_related_this"
                    # walked only from ev (whose date it is) to t, never back
                    self._add(ev, t, "date_anchors", None,
                              Reason(kind_t, other=ev, claims=claims),
                              Reason(kind_ev, other=t, claims=claims))

    def claims_for(self, nodes) -> list[Claim]:
        """The site's Claim objects for the given assertion nodes, in a stable order."""
        return [self.by_node[n] for n in sorted({str(x) for x in nodes}) if n in self.by_node]

    def _add(self, a: str, b: str, a_to_b: str | None, b_to_a: str | None,
             reason_on_b: Reason, reason_on_a: Reason):
        """Record a link. adj[a] lets a rule walk from a to b in direction a_to_b (and
        adj[b] back, if b_to_a is set); about[x] lists every link of x, for display."""
        if a_to_b:
            self.adj.setdefault(a, []).append((b, a_to_b, reason_on_b))
        if b_to_a:
            self.adj.setdefault(b, []).append((a, b_to_a, reason_on_a))
        self.about.setdefault(b, []).append((a, reason_on_b))
        self.about.setdefault(a, []).append((b, reason_on_a))

    def _part(self, part: str, whole: str, claims: list[Claim]):
        self.whole_of.setdefault(part, set()).add(whole)
        self._add(part, whole, "wholes", "parts",
                  Reason("has_part", other=part, claims=claims),     # shown on the whole: it has this part
                  Reason("part_of", other=whole, claims=claims))     # shown on the part: it is part of the whole


def select_events(site: Site, links: Links, rule: dict,
                  excluded: dict[str, str] | None = None) -> tuple[dict[str, int], dict[str, list[Reason]]]:
    """BFS from the named events. Returns (hop per IRI, reasons per IRI). A background
    entity is never a seed and never walked through; it goes to `excluded` instead."""
    named = rule["named"]
    bg = links.background
    excluded = {} if excluded is None else excluded
    hop: dict[str, int] = {}
    reasons: dict[str, list[Reason]] = {}
    for kind in named["kinds"]:
        for e in site.by_kind[kind]:
            w = name_matches(site, e.iri, named.get("words"), named.get("phrase"), named.get("not_words"))
            if w:
                if e.iri in bg:
                    excluded.setdefault(e.iri, bg[e.iri])
                    continue
                hop[e.iri] = 0
                reasons[e.iri] = [Reason("named", word=w)]
    frontier = sorted(hop)
    for depth in range(1, rule["max_links"] + 1):
        nxt = []
        for iri in frontier:
            for other, direction, reason in links.adj.get(iri, []):
                if direction not in rule["follow"] or other == iri:
                    continue
                if other in bg:
                    if other not in hop:
                        excluded.setdefault(other, bg[other])
                    continue
                if other not in hop:
                    hop[other] = depth
                    reasons[other] = []
                    nxt.append(other)
                # the reason shown on `other` names `iri`, the step it was reached from
                if hop[other] == depth and reason not in reasons[other]:
                    reasons[other].append(reason)
        frontier = sorted(set(nxt))
    return hop, reasons


# --------------------------------------------------------------------------- ordering
def _order_events(site: Site, links: Links, chosen: list[str]) -> tuple[list[str], dict, bool]:
    """Topological order from recorded dates, before/after links and part-of (a part
    follows its whole). Ties: dated before undated, then date, then story number, then
    name. Returns (order, notes, conflict)."""
    ents = {i: site.entity(i) for i in chosen}
    sel = set(chosen)
    recorded: set[tuple[str, str]] = set()
    for a, b, _kind in links.order:
        if a in sel and b in sel:
            recorded.add((a, b))
    bounds = {i: _bounds(ents[i]) for i in chosen}
    dated: set[tuple[str, str]] = set()
    for a in chosen:
        for b in chosen:
            (alo, ahi), (blo, bhi) = bounds[a], bounds[b]
            if a != b and ahi and blo and _iso_key(ahi) < _iso_key(blo):
                dated.add((a, b))
    parts: set[tuple[str, str]] = set()
    whole_in_sel = {p: sorted(w for w in links.whole_of.get(p, ()) if w in sel) for p in chosen}
    for p, ws in whole_in_sel.items():
        for w in ws:
            parts.add((w, p))

    def key(i: str):
        e = ents[i]
        lo, _ = bounds[i]
        n = e.data.get("number") if e.kind == "story" else None
        return (lo is None, _iso_key(lo) if lo else (), n is None, n or 0, display.sort_key(e.name), e.pid)

    conflict = False
    order: list[str] = []
    used: set = set()
    for edges in (recorded | dated | parts, recorded | dated, recorded, set()):
        found = _kahn(chosen, edges, whole_in_sel, key)
        if found is not None:
            order, used = found, edges
            break
        conflict = True
    # notes: how each step's place relates to the step before it. A recorded order
    # (dates, before/after links) is named first; a part follows its whole; otherwise
    # the record gives no order and the tie-break rule placed it.
    closure = _closure(chosen, used & (recorded | dated))
    notes: dict[str, tuple[str | None, str | None]] = {}
    for idx, i in enumerate(order):
        if idx == 0:
            notes[i] = (None, None)
            continue
        prev = order[idx - 1]
        ws = [w for w in whole_in_sel[i] if order.index(w) < idx]
        if (prev, i) in closure:
            notes[i] = ("recorded", prev)
        elif ws and (ws[0], i) in used:
            notes[i] = ("part", ws[0])
        else:
            notes[i] = ("unrecorded", prev)
    return order, notes, conflict


def _kahn(nodes: list[str], edges: set, whole_in_sel: dict, key) -> list[str] | None:
    succ: dict[str, set[str]] = {n: set() for n in nodes}
    indeg: dict[str, int] = {n: 0 for n in nodes}
    for a, b in edges:
        if b not in succ[a]:
            succ[a].add(b)
            indeg[b] += 1
    ready = {n for n in nodes if indeg[n] == 0}
    out: list[str] = []
    open_wholes: list[str] = []
    while ready:
        pick = None
        for w in reversed(open_wholes):          # keep parts right after their whole
            cands = [n for n in ready if w in whole_in_sel.get(n, ())]
            if cands:
                pick = min(cands, key=key)
                break
        if pick is None:
            pick = min(ready, key=key)
        ready.discard(pick)
        out.append(pick)
        if any(pick in whole_in_sel.get(n, ()) for n in nodes):
            open_wholes.append(pick)
        for b in sorted(succ[pick]):
            indeg[b] -= 1
            if indeg[b] == 0:
                ready.add(b)
    return out if len(out) == len(nodes) else None


def _closure(nodes: list[str], edges: set) -> set[tuple[str, str]]:
    succ: dict[str, set[str]] = {n: set() for n in nodes}
    for a, b in edges:
        succ[a].add(b)
    out = set()
    for n in nodes:
        stack, seen = list(succ[n]), set()
        while stack:
            m = stack.pop()
            if m in seen:
                continue
            seen.add(m)
            out.add((n, m))
            stack.extend(succ[m])
    return out


# --------------------------------------------------------------------------- the three step types
def build_events(site: Site, links: Links, spec: dict) -> Journey:
    rule = spec["select"]
    excluded: dict[str, str] = {}
    hop, reasons = select_events(site, links, rule, excluded)
    chosen = sorted(hop)
    order, notes, conflict = _order_events(site, links, chosen)
    sel = set(chosen)
    pos = {x: n for n, x in enumerate(order)}
    steps = []
    for i in order:
        st = Step(entity=site.entity(i), reasons=reasons[i], hop=hop[i])
        st.order_note, st.order_ref = notes[i]
        for other, r in links.about.get(i, []):
            if other in sel and r not in st.reasons and r not in st.links:
                st.links.append(r)
        st.links.sort(key=lambda r: (pos.get(r.other, 10**6), r.kind))
        steps.append(st)
    kinds = {s.entity.kind for s in steps}
    universe = sum(len(site.by_kind[k]) for k in EVENT_KINDS)
    return Journey(spec, steps, universe=universe, order_conflict=conflict,
                   mixes_stories_and_events=kinds == {"event", "story"},
                   excluded=_excluded_list(site, excluded), order_applied=spec["order"])


def side_claims(site: Site, iri: str, anchors: list[str]) -> list[Claim]:
    """The claims that record this person's side at the anchors (design §6.4): the person
    is the subject of a rel_fought_alongside or rel_fought_against claim whose mrs:atEvent
    is an anchor and whose object is the Prophet ﷺ, with a citation and no rejected or
    superseded status. Claims where the person is only the object are never taken."""
    pos = {a: n for n, a in enumerate(anchors)}
    out = []
    for c in site.claims.get(iri, []):
        if c.kind != "assertion" or c.subject != iri or not c.node or side_of(site, c) is None:
            continue
        at = claim_node(site, c, MRS.atEvent)
        other = site.entity(c.object)
        if at is None or str(at) not in pos or other is None or not other.prophet:
            continue
        if not c.citation or claim_statuses(site, c) & set(NOT_SHOWN):
            continue
        out.append(c)
    return sorted(out, key=lambda c: (pos[str(claim_node(site, c, MRS.atEvent))], side_of(site, c), c.node))


def build_people(site: Site, links: Links, spec: dict, lists_root: Path | str | None = None) -> Journey:
    rule = spec["select"]
    excluded: dict[str, str] = {}
    hop, _reasons = select_events(site, links, rule["events"], excluded)
    anchors = sorted(hop, key=lambda i: (site.entity(i).kind == "story", site.entity(i).data.get("number") or 0,
                                         display.sort_key(site.entity(i).name), i))
    want = {term(c, "claims") for c in rule["participation"]["claims"]}
    also = {term(c, "also_show") for c in rule["also_show"]}
    apart = {term(q, "set_apart") for q in rule["set_apart"]}
    records: dict[str, list[Claim]] = {}
    contrary: dict[str, list[Claim]] = {}
    for ev in anchors:
        for c in site.claims.get(ev, []):
            if c.object != ev:
                continue
            who = site.entity(c.subject)
            if who is None or who.kind != "person":
                continue
            if who.iri in links.background:
                excluded.setdefault(who.iri, links.background[who.iri])
                continue
            if c.kind == "participation":
                if rule["participation"]["records"]:
                    records.setdefault(who.iri, []).append(c)
            elif c.kind == "assertion":
                pred = claim_node(site, c, MRS.predicate)
                if pred in want:
                    records.setdefault(who.iri, []).append(c)
                elif pred in also:
                    contrary.setdefault(who.iri, []).append(c)
    anchor_pos = {a: n for n, a in enumerate(anchors)}

    def rec_key(c: Claim):
        return (anchor_pos.get(c.object, 10**6), c.kind != "participation", c.predicate,
                c.role.text if c.role else "", c.node or "")

    steps, set_apart = [], []
    for iri in sorted(records):
        recs = records[iri]
        st = Step(entity=site.entity(iri), records=sorted(recs, key=rec_key),
                  contrary=sorted(contrary.get(iri, []), key=rec_key))
        st.side = side_claims(site, iri, anchors)
        sides = {side_of(site, c) for c in st.side}
        st.side_conflict = sides == {"alongside", "against"}
        if rule.get("group_by") == "side" and sides == {"against"} and not st.entity.prophet:
            st.group = "against"
        if apart and all(claim_qualifiers(site, c) & apart for c in recs if c.kind == "assertion") \
                and not any(c.kind == "participation" for c in recs):
            st.group = "main"
            set_apart.append(st)
        else:
            steps.append(st)

    order_applied, lists_info = spec["order"], None
    if spec["order"] == "e3":
        jl = _lists_module()
        info = jl.load_lists(lists_file(spec, lists_root), where=spec["lists"])
        members = {ls["key"]: jl.match_members(site, ls["members"]) for ls in info["lists"]}
        reviewed = info["state"] == "reviewed"
        tiers = members if reviewed else None
        accept = jl.acceptance_events(site)
        for st in steps + set_apart:
            st.e3 = jl.e3_data(site, st, tiers, accept)
        order_applied = "e3" if reviewed else "e3_pending"
        lists_info = {"file": spec["lists"], "state": info["state"], "sha": info["sha"], "applied": reviewed,
                      "sources_complete": info["sources_complete"], "stale_approval": info["stale_approval"],
                      "sources": [{"key": ls["key"], "text": ls["source"]} for ls in info["lists"]],
                      "members": members}

        def person_key(st: Step):
            return jl.e3_key(site, st, tiers)
    else:
        def person_key(st: Step):
            first = spec["order"] == "prophet_first_then_name" and st.entity.prophet
            return (not first, display.sort_key(st.entity.name), st.entity.pid)

    groups: list[Group] = []
    if rule.get("group_by") == "side":
        main = sorted((st for st in steps if st.group == "main"), key=person_key)
        against = sorted((st for st in steps if st.group == "against"), key=person_key)
        steps = main + against
        if main:
            groups.append(Group("main", 0, len(main)))
        if against:
            groups.append(Group("against", len(main), len(steps), "learn.group.against", "learn.group.against_lead"))
    else:
        steps.sort(key=person_key)
    set_apart.sort(key=person_key)
    kinds = {site.entity(a).kind for a in anchors}
    return Journey(spec, steps, set_apart=set_apart, anchors=anchors, universe=len(site.by_kind["person"]),
                   mixes_stories_and_events=kinds == {"event", "story"}, excluded=_excluded_list(site, excluded),
                   groups=groups, order_applied=order_applied, lists=lists_info)


def build_stories(site: Site, spec: dict, links: Links | None = None) -> Journey:
    words = spec["select"]["part"]["words"]
    bg = links.background if links is not None else background(site)
    parts: set[str] = set()
    chosen = []
    excluded: dict[str, str] = {}
    for e in site.stories_in_order():
        label = e.data.get("part_label")
        if label and any(w.lower() in tokens(label) for w in words):
            if e.iri in bg:
                excluded[e.iri] = bg[e.iri]
                continue
            parts.add(label)
            chosen.append(e)
    steps = []
    for e in chosen:
        named = [c for c in site.claims.get(e.iri, []) if c.kind == "assertion" and c.object == e.iri
                 and site.entity(c.subject) is not None]
        named.sort(key=lambda c: (display.sort_key(site.entity(c.subject).name), c.node or ""))
        steps.append(Step(entity=e, records=named,
                          reasons=[Reason("part", word=e.data.get("part_label"))]))
    return Journey(spec, steps, part_labels=sorted(parts), universe=len(site.by_kind["story"]),
                   excluded=_excluded_list(site, excluded), order_applied=spec["order"])


def _lists_module():
    """learn/journey_lists.py, imported only when a journey's order is e3 (design §6)."""
    import journey_lists
    return journey_lists


def build(site: Site, spec: dict, links: Links | None = None, *, lists_root: Path | str | None = None) -> Journey:
    """Apply one rule to the graph. Every list-file problem of an e3 journey (missing,
    unreadable, invalid, or a member matching no person or several) is a RuleError."""
    links = links or Links(site)
    t = spec["select"]["type"]
    if t == "events":
        j = build_events(site, links, spec)
    elif t == "people":
        j = build_people(site, links, spec, lists_root)
    else:
        j = build_stories(site, spec, links)
    if not j.steps:
        raise RuleError(f"{spec['slug']}: the rule chose no step in this graph")
    return j


def build_all(site: Site, specs: list[dict], *, lists_root: Path | str | None = None) -> list[Journey]:
    links = Links(site)
    return [build(site, s, links, lists_root=lists_root) for s in specs]
