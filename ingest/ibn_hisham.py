#!/usr/bin/env python3
"""
Slice 4: AI-assisted ingestion of Ibn Hisham's al-Sira al-Nabawiyya (OpenITI) into the graph.

    .venv/bin/python ingest/ibn_hisham.py fetch     # download the pinned OpenITI text into ingest/cache/ and check its SHA-256
    .venv/bin/python ingest/ibn_hisham.py build     # write ontology/corpus/ibn-hisham.ttl (needs the cached text)
    .venv/bin/python ingest/ibn_hisham.py check     # exit 1 if the committed Turtle differs from what build would write
    .venv/bin/python ingest/ibn_hisham.py review    # write ingest/cache/review.html: every claim beside its Arabic span
    .venv/bin/python ingest/ibn_hisham.py locate PASSAGE "Arabic words"   # offsets of a phrase in a passage

THE TEXT IS NEVER COMMITTED. The OpenITI corpus is released under CC BY-NC-SA 4.0
(NonCommercial), which this corpus (CC BY-SA 4.0) cannot carry. `fetch` keeps the
file in ingest/cache/ (gitignored) and checks it against the SHA-256 recorded in
ingest/claims/ibn-hisham-source.json. The repository holds only pointers into it
and the claims:

  ingest/claims/ibn-hisham-source.json      the witness (OpenITI URI, version, commit, checksum),
                                            the edition it names (PROVISIONAL), the IDs of the
                                            work, recension, edition, witness, agent and activity
  ingest/claims/ibn-hisham-passages.jsonl   one report per line: character offsets of its passage
                                            in the file, the offsets of its ascription formula, its
                                            chain of transmission where every narrator is named
  ingest/claims/ibn-hisham-entities.jsonl   the people, places and events this text adds to the
                                            graph (their IDs are in ontology/corpus/identity.csv)
  ingest/claims/ibn-hisham.jsonl            the extraction output: one claim per line, with the
                                            offsets of its exact Arabic span inside its passage

Offsets count Unicode code points of the UTF-8-decoded file (LF line ends, no
normalisation), as the W3C Web Annotation TextPositionSelector does: a passage is
[start, end) in the file; a span is [start, end) in its passage.

Entities are resolved through ontology/corpus/identity.csv BY NAME (kind +
preferred_name_en), never by an ID written in this code, so a re-run after IDs are
re-minted on main follows the new IDs. A name that is missing or ambiguous stops
the build. This script mints nothing; IDs were minted once with
ontology/tools/mint_id.py and are kept in the JSONL files and identity.csv.

What is written into the Turtle from the text itself, exactly as written, is
limited to: names (people, places), ascription formulas and chains of transmission,
and the short age and date expressions a claim rests on (mrs:ageAsWritten,
mrs:dateAsWritten, the object of mrs:rel_dated). Running text is never written:
each Report's mrs:matnText says where the text is instead.

"As written" strings are the span with the OpenITI markup removed and nothing else
changed: page markers (PageV01P158), milestones (ms087), footnote markers ([1]),
editorial headings (lines starting ###) and the paragraph and line-continuation
marks (# , ~~) are dropped and runs of white space become one space.
"""

import argparse
import csv
import hashlib
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "ingest"
CACHE = INGEST / "cache"
CLAIMS_DIR = INGEST / "claims"
SOURCE = CLAIMS_DIR / "ibn-hisham-source.json"
PASSAGES = CLAIMS_DIR / "ibn-hisham-passages.jsonl"
ENTITIES = CLAIMS_DIR / "ibn-hisham-entities.jsonl"
CLAIMS = CLAIMS_DIR / "ibn-hisham.jsonl"
# the full-book pass (ingest/sira_full.py): read beside the files above, written into the same Turtle
FULL_PASSAGES = CLAIMS_DIR / "ibn-hisham-full-passages.jsonl"
FULL_ENTITIES = CLAIMS_DIR / "ibn-hisham-full-entities.jsonl"
FULL_CLAIMS = CLAIMS_DIR / "ibn-hisham-full.jsonl"
IDENTITY = ROOT / "ontology" / "corpus" / "identity.csv"
RENAMES = ROOT / "ontology" / "corpus" / "id-renames.csv"
RELATIONS = ROOT / "ontology" / "relations.ttl"
OUT = ROOT / "ontology" / "corpus" / "ibn-hisham.ttl"
REVIEW = CACHE / "review.html"
USER_AGENT = "al-marsad-ingest/0.1 (slice 4; https://github.com/thajudeenUrbane/al-marsad)"
RECORDED = "2026-10-15T00:00:00Z"
ID_RE = re.compile(r"^[a-z]{2,5}:[0-9A-Za-z]{22}$")

PREFIXES = [
    ("mrs", "https://w3id.org/marsad/core#"),
    ("mrsv", "https://w3id.org/marsad/vocab/"),
    ("crm", "http://www.cidoc-crm.org/cidoc-crm/"),
    ("lrmoo", "http://iflastandards.info/ns/lrm/lrmoo/"),
    ("prov", "http://www.w3.org/ns/prov#"),
    ("oa", "http://www.w3.org/ns/oa#"),
    ("spdx", "http://spdx.org/rdf/terms#"),
    ("skos", "http://www.w3.org/2004/02/skos/core#"),
    ("dct", "http://purl.org/dc/terms/"),
    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
    ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
]
ID_PREFIXES = [  # instance prefixes used in the output, with their IRI path segment
    ("per", "person"), ("plc", "place"), ("ev", "event"), ("wrk", "work"), ("rcn", "recension"),
    ("edn", "edition"), ("wit", "witness"), ("psg", "passage"), ("rpt", "report"), ("chn", "chain"),
    ("ast", "assertion"), ("tmp", "temporal"), ("agt", "agent"), ("act", "activity"),
]
KIND_PREFIX = {"person": "per", "place": "plc", "event": "ev"}
PLACE_TYPES = {"settlement", "quarter", "well", "mountain", "cave", "valley", "oasis", "route_node",
               "region", "structure", "battlefield", "cemetery"}
ASCRIPTIONS = {"marfu", "mawquf", "maqtu", "other", "none"}
MODES = {"sama", "qiraa", "ijaza", "munawala", "wijada", "anana", "unspecified"}
QUALIFIERS = {
    "hedged": ("hedged in the text",
               "The narrator hedges the statement the claim rests on, in words such as \u201cفيما بلغني\u201d "
               "(so I have heard), \u201cفيما يذكرون\u201d (as they relate) or \u201cزعموا\u201d (they claim)."),
    "text_alternative": ("alternative report in the text",
                         "The text gives this as an alternative to another report, introduced by words such as "
                         "\u201cويقال\u201d (it is said) or \u201cويقول قائل\u201d (someone says). The other "
                         "report is a separate claim; neither is preferred here."),
    "share_not_present": ("counted at Badr without being present",
                          "The text lists the person among the people of Badr but says he was not there and "
                          "that the Prophet \ufdfa allotted him his share."),
    "editorial_brackets": ("rests on words in round brackets",
                           "The words the claim rests on are in round brackets in the edition, which marks "
                           "words the editors supplied. Check them against the edition and its manuscripts."),
}

# ---------------------------------------------------------------- the text


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def cache_file(src: dict) -> Path:
    return CACHE / src["witness"]["file_name"]


def fetch(src: dict) -> Path:
    """Download the pinned file (raw.githubusercontent.com, exact commit) and check its SHA-256."""
    w = src["witness"]
    dest = cache_file(src)
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == w["sha256"]:
        print(f"{dest.relative_to(ROOT)} is present and matches sha256 {w['sha256'][:16]}...")
        return dest
    CACHE.mkdir(parents=True, exist_ok=True)
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(w["raw_url"], headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            got = hashlib.sha256(data).hexdigest()
            if got != w["sha256"]:
                sys.exit(f"downloaded file has sha256 {got}, expected {w['sha256']}: refusing to use it")
            dest.write_bytes(data)
            print(f"wrote {dest.relative_to(ROOT)} ({len(data)} bytes, sha256 matches)")
            return dest
        except Exception as e:  # noqa: BLE001  (network: retry with backoff)
            last = e
            wait = 2 ** attempt
            print(f"fetch failed ({e}); retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    sys.exit(f"could not fetch {w['raw_url']}: {last}")


def load_text(src: dict) -> str:
    f = cache_file(src)
    if not f.exists():
        sys.exit(f"missing {f.relative_to(ROOT)}: run `ingest/ibn_hisham.py fetch` first")
    data = f.read_bytes()
    got = hashlib.sha256(data).hexdigest()
    if got != src["witness"]["sha256"]:
        sys.exit(f"{f.relative_to(ROOT)} has sha256 {got}, expected {src['witness']['sha256']}")
    return data.decode("utf-8")


MARKUP = re.compile(r"PageV\d+P\d+|\bms\d+|\[\d+\]")
PAGE = re.compile(r"PageV(\d+)P(\d+)")
MILESTONE = re.compile(r"\bms(\d+)")


def clean_with_map(raw: str):
    """The text with OpenITI markup removed, and for each kept character its index in `raw`."""
    keep = [True] * len(raw)
    space = [False] * len(raw)
    for m in MARKUP.finditer(raw):  # markers become a space
        for i in range(m.start(), m.end()):
            keep[i] = False
        space[m.start()] = True
    i = 0
    while i < len(raw):  # editorial headings, and the paragraph / continuation marks at line starts
        if raw[i] == "\n" or i == 0:
            j = i + 1 if raw[i] == "\n" else i
            if raw.startswith("###", j):
                end = raw.find("\n", j)
                end = len(raw) if end < 0 else end
                for k in range(i, end):
                    keep[k] = False
                space[i] = True
                i = end
                continue
            if raw[i] == "\n":
                keep[i] = False
                space[i] = True
            for mark in ("~~", "# "):
                if raw.startswith(mark, j):
                    for k in range(j, j + len(mark)):
                        keep[k] = False
                    break
        i += 1
    out, idx = [], []
    for i, ch in enumerate(raw):
        if keep[i] and not ch.isspace():
            out.append(ch)
            idx.append(i)
        elif keep[i] or space[i]:
            if out and out[-1] != " ":
                out.append(" ")
                idx.append(i)
    while out and out[-1] == " ":
        out.pop()
        idx.pop()
    return "".join(out), idx


def clean(raw: str) -> str:
    return clean_with_map(raw)[0]


class Text:
    """The cached file, with its page markers, milestones and line starts indexed."""

    def __init__(self, s: str):
        self.s = s
        self.pages = [(m.start(), int(m.group(1)), int(m.group(2))) for m in PAGE.finditer(s)]
        self.miles = [(m.start(), int(m.group(1))) for m in MILESTONE.finditer(s)]
        self.line_starts = [0] + [i + 1 for i, ch in enumerate(s) if ch == "\n"]

    def line(self, pos: int) -> int:
        lo, hi = 0, len(self.line_starts)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if self.line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid
        return lo + 1

    def page(self, pos: int):
        """OpenITI puts a page's marker at the END of the page, so a position is on the page of the next marker."""
        for p, vol, num in self.pages:
            if p >= pos:
                return vol, num
        return None

    def milestone(self, pos: int):
        """Milestones mark the end of each 300-word block, so a position is in the block of the next marker."""
        for p, n in self.miles:
            if p >= pos:
                return n
        return None


# ---------------------------------------------------------------- the data


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.exit(f"{path.relative_to(ROOT)} line {n}: {e}")
    return rows


def read_all(*paths: Path) -> list[dict]:
    """The slice 4 file and its full-book-pass counterpart (if present), in that order."""
    return [r for p in paths if p.exists() for r in read_jsonl(p)]


def load_identity():
    with IDENTITY.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    by_name = {}
    for r in rows:
        by_name.setdefault((r["kind"], r["preferred_name_en"]), []).append(r["canonical_id"])
    return rows, by_name


def relation_types() -> set[str]:
    return set(re.findall(r"^mrs:(rel_\w+) a mrs:RelationType", RELATIONS.read_text(encoding="utf-8"), re.M))


class Resolver:
    """Entity references are {kind, name}: resolved through identity.csv, by name."""

    def __init__(self):
        self.rows, self.by_name = load_identity()
        self.used = {}

    def __call__(self, ref: dict, where: str) -> str:
        kind, name = ref.get("kind"), ref.get("name")
        if kind not in KIND_PREFIX or not name:
            sys.exit(f"{where}: bad entity reference {ref}")
        ids = self.by_name.get((kind, name), [])
        if len(ids) != 1:
            sys.exit(f"{where}: {kind} {name!r} is in {len(ids)} identity.csv rows (need exactly 1)")
        cid = ids[0]
        if not cid.startswith(KIND_PREFIX[kind] + ":"):
            sys.exit(f"{where}: {name!r} resolves to {cid}, not a {kind} ID")
        self.used[cid] = (kind, name)
        return cid


def check_id(i: str, where: str):
    if not ID_RE.match(i or ""):
        sys.exit(f"{where}: malformed ID {i!r}")


def as_written(passage_raw: str, spans) -> str:
    parts = []
    for s, e in spans:
        if not (0 <= s < e <= len(passage_raw)):
            sys.exit(f"span {s}-{e} lies outside its passage (length {len(passage_raw)})")
        parts.append(clean(passage_raw[s:e]))
    return " \u2026 ".join(parts)


# ---------------------------------------------------------------- Turtle


def lit(s: str, lang: str | None = None, dt: str | None = None) -> str:
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    out = f'"{s}"'
    if lang:
        out += f"@{lang}"
    elif dt:
        out += f"^^{dt}"
    return out


def block(subject: str, types: list[str], props: list[tuple[str, str]], comment: str | None = None) -> str:
    """One subject: `a` types, then predicate-object pairs in the order given."""
    lines = []
    if comment:
        lines += [f"# {c}" if c else "#" for c in comment.split("\n")]
    lines.append(subject)
    body = [f"a {' , '.join(types)}"] + [f"{p} {o}" for p, o in props]
    for k, b in enumerate(body):
        lines.append(f"    {b} {'.' if k == len(body) - 1 else ';'}")
    return "\n".join(lines) + "\n"


def bnode(types: list[str], props: list[tuple[str, str]], indent: int = 8) -> str:
    pad = " " * indent
    inner = [f"a {' , '.join(types)}"] + [f"{p} {o}" for p, o in props]
    return "[ " + (" ;\n" + pad + "  ").join(inner) + " ]"


def audit(stamp=True) -> list[tuple[str, str]]:
    props = [("mrs:coverageState", "mrs:cs_stub"), ("mrs:createdBy", "{agent}"),
             ("mrs:recordedAt", lit(RECORDED, dt="xsd:dateTime"))]
    return props if stamp else []


HEADER = """#################################################################
#
#  IBN HISHAM, al-Sira al-Nabawiyya -- AI-assisted extraction (slice 4)
#
#  /!\\  AI-EXTRACTED. PROPOSED. NOT SCHOLAR-REVIEWED.
#
#  GENERATED by ingest/ibn_hisham.py from the cached OpenITI text and
#  ingest/claims/*.jsonl, resolving every person, place and event
#  through ontology/corpus/identity.csv by name. Do not edit by hand:
#  change the claims and re-run `ingest/ibn_hisham.py build`.
#
#  SOURCE. OpenITI version {version_uri} (OpenITI primary version;
#  file at commit {commit_short} of github.com/OpenITI/0225AH,
#  sha256 {sha_short}...). Its metadata names its base edition:
#  ed. Mustafa al-Saqqa, Ibrahim al-Abyari, Abd al-Hafiz Shalabi,
#  2nd ed., 1375 AH / 1955 CE, Mustafa al-Babi al-Halabi, Cairo.
#  THAT EDITION IS PROVISIONAL: the scholars will choose the edition
#  of record (maintainer decision E33). Page numbers below are that
#  edition's, as the OpenITI file marks them, not checked in print.
#
#  LICENCE. The OpenITI corpus is released under CC BY-NC-SA 4.0
#  (NonCommercial), which this corpus (CC BY-SA 4.0) cannot carry.
#  So the Arabic text is NOT in this file or anywhere in the repo.
#  Each Report says where its text is (its Passage: character
#  offsets into the file, lines, milestone, page) instead of quoting
#  it; `ingest/ibn_hisham.py fetch` downloads the file locally and
#  `review` shows every claim beside its Arabic span. Taken from the
#  text verbatim here are only: names, ascription formulas and
#  chains, and the short age and date expressions claims rest on.
#
#  WHAT A CLAIM IS. One mrs:Assertion per claim, status proposed,
#  coverage stub, created by the software agent "AI extraction pass
#  (slice 4)" on 15 October 2026, with NO adjudicator. Each one has
#  mrs:fromReport (the report it comes from), prov:wasDerivedFrom
#  (its passage) and oa:hasTarget: a W3C Web Annotation
#  TextPositionSelector giving the exact span inside the passage
#  ([start, end) in Unicode code points). rdfs:comment holds an
#  English gloss written by the AI pass: proposed, unreviewed, never
#  a translation of record (maintainer decision E34).
#
#  ASCRIPTIONS AND CHAINS. A report's ascription formula ("qala Ibn
#  Ishaq") is kept exactly as written in crm:P3_has_note and is never
#  completed: a bare "qala" stays bare, and the implied link from Ibn
#  Ishaq to Ibn Hisham is not added where the text does not write it.
#  A chain (mrs:TransmissionChain) is modelled only where the text
#  names every narrator; its label is the chain as written. The
#  transmission mode is read off the term the text uses (haddathani,
#  haddathana, sami'tu -> sama; 'an -> 'an'ana; anything else ->
#  unspecified), and each link keeps that term as its label.
#  mrs:continuity is never set: that is a scholar's determination.
#  mrs:terminalAscription is a proposed formal reading of the last
#  authority the text names (the compiler himself -> other; no
#  formula in the passage -> none; a Companion -> mawquf), for a
#  scholar to confirm. No grading of any kind is made.
#
#  LIFE DATES AND AGES (for the lifelines view). Ages are kept as
#  written (mrs:ageAsWritten) with the number the text gives
#  (mrs:ageYearsAsGiven, one value per alternative), never computed
#  and never converted: classical ages are usually lunar-year counts
#  and no passage here states its basis, so none is recorded. Dates
#  are kept as written (mrs:rel_dated, mrs:dateAsWritten); nothing is
#  converted to the Gregorian calendar.
#
#  ENTITIES. People, places and events already in identity.csv are
#  only referenced, never redeclared, with one exception: a person
#  already in the graph who is a narrator in a modelled chain (so
#  that this file validates on its own), or whose name form is listed
#  in the entities file, is typed here with the name form attested in
#  this text. New ones are declared below with the
#  name as written, and have identity.csv rows marked needs-review.
#  Nobody is merged or split.
#
#################################################################
"""


def build_ttl(src: dict, text: Text) -> tuple[str, dict]:
    rel_types = relation_types()
    resolve = Resolver()
    renamed = set()
    if RENAMES.exists():
        with RENAMES.open(encoding="utf-8", newline="") as fh:
            renamed = {r["old_id"] for r in csv.DictReader(fh)}
    ids = src["ids"]
    for k, v in ids.items():
        check_id(v, f"source ids.{k}")
    agent = ids["agent"]
    stamp = lambda: [(p, o.replace("{agent}", agent)) for p, o in audit()]  # noqa: E731

    passages = read_all(PASSAGES, FULL_PASSAGES)
    entities = read_all(ENTITIES, FULL_ENTITIES)
    claims = read_all(CLAIMS, FULL_CLAIMS)
    s = text.s

    # ---- passages: offsets, checksums, citations
    psg_by_id = {}
    for p in passages:
        for k in ("id", "report"):
            check_id(p[k], f"passage {p.get('id')}")
        if p["id"] in psg_by_id:
            sys.exit(f"passage {p['id']} appears twice")
        if not (0 <= p["start"] < p["end"] <= len(s)):
            sys.exit(f"passage {p['id']}: offsets outside the file")
        raw = s[p["start"]:p["end"]]
        if sha256_text(raw) != p["sha256"]:
            sys.exit(f"passage {p['id']}: the cached text at {p['start']}-{p['end']} does not match its sha256")
        if p["ascription_class"] not in ASCRIPTIONS:
            sys.exit(f"passage {p['id']}: unknown ascription class {p['ascription_class']}")
        psg_by_id[p["id"]] = p

    # ---- new entities
    new_ents = []
    existing_forms = {}  # IRI of a person already in the graph -> [(name as written, passage)]
    for e in entities:
        where = f"entity {e.get('name')!r}"
        cid = resolve({"kind": e["kind"], "name": e["name"]}, where)
        attested = e.get("attested")
        name_ar = None
        if attested:
            p = psg_by_id.get(attested["passage"])
            if p is None:
                sys.exit(f"{where}: unknown passage {attested['passage']}")
            name_ar = as_written(s[p["start"]:p["end"]], [attested["span"]])
        if e.get("existing"):
            if e["kind"] != "person" or not name_ar:
                sys.exit(f"{where}: an existing entity is listed only to record a person's name as written")
            existing_forms.setdefault(cid, []).append((name_ar, p["id"]))
            continue
        new_ents.append((e, cid, name_ar))

    # ---- claims
    seen_claims = set()
    by_passage = {}
    referred = {}  # event IRI -> passages that make claims about it
    for c in claims:
        where = f"claim {c.get('id')}"
        check_id(c["id"], where)
        if c["id"] in seen_claims:
            sys.exit(f"{where}: appears twice")
        seen_claims.add(c["id"])
        p = psg_by_id.get(c["passage"])
        if p is None:
            sys.exit(f"{where}: unknown passage {c['passage']}")
        raw = s[p["start"]:p["end"]]
        a, b = c["span"]
        if not (0 <= a < b <= len(raw)):
            sys.exit(f"{where}: span outside its passage")
        if sha256_text(raw[a:b]) != c["span_sha256"]:
            sys.exit(f"{where}: the span text does not match its sha256")
        if c["predicate"] not in rel_types:
            sys.exit(f"{where}: {c['predicate']} is not in ontology/relations.ttl")
        c["_subject"] = resolve(c["subject"], where)
        obj = c["object"]
        if "literal_spans" in obj:
            c["_object"] = lit(as_written(raw, obj["literal_spans"]), lang="ar")
        else:
            c["_object"] = resolve(obj, where)
        for q in c.get("qualifiers", []):
            if q not in QUALIFIERS:
                sys.exit(f"{where}: unknown qualifier {q}")
        if c["predicate"] == "rel_age_at" and "age" not in c:
            sys.exit(f"{where}: an age claim needs its age as written")
        if c["predicate"] == "rel_dated" and "literal_spans" not in obj:
            sys.exit(f"{where}: a dated claim's object is the time expression as written")
        for x in (c["_subject"], c["_object"]):
            if x.startswith("ev:"):
                referred.setdefault(x, set()).add(c["passage"])
        by_passage.setdefault(c["passage"], []).append(c)

    # ---- chains: narrators resolved by name
    chain_people = {}
    for p in passages:
        ch = p.get("chain")
        if not ch:
            continue
        check_id(ch["id"], f"chain of {p['id']}")
        for k in ("terminal", "collector"):
            if ch.get(k):
                ch["_" + k] = resolve(ch[k], f"chain {ch['id']}")
        for ln in ch["links"]:
            ln["_from"] = resolve(ln["from"], f"chain {ch['id']}")
            ln["_to"] = resolve(ln["to"], f"chain {ch['id']}")
            if ln["mode"] not in MODES:
                sys.exit(f"chain {ch['id']}: unknown mode {ln['mode']}")
            for x in (ln["_from"], ln["_to"]):
                chain_people.setdefault(x, p)

    emitted = set(ids.values()) | {p["id"] for p in passages} | {p["report"] for p in passages} | seen_claims
    emitted |= {p["chain"]["id"] for p in passages if p.get("chain")}
    emitted |= {cid for _, cid, _ in new_ents}
    stale = sorted(i for i in emitted if i in renamed)
    if stale:
        sys.exit(f"these IDs were retired (ontology/corpus/id-renames.csv): {stale}")

    w = src["witness"]
    out = [f"@prefix {p}: <{ns}> ." for p, ns in PREFIXES]
    out.append("")
    out += [f"@prefix {p}: <https://w3id.org/marsad/id/{seg}/> ." for p, seg in ID_PREFIXES]
    out.append("")
    out.append(HEADER.format(version_uri=w["version_uri"], commit_short=w["commit"][:8], sha_short=w["sha256"][:16]))

    # ---- agent and activity
    out.append(block(agent, ["prov:SoftwareAgent"], [
        ("rdfs:label", lit("AI extraction pass (slice 4)", "en")),
        ("rdfs:comment", lit(src["agent_comment"], "en"))]))
    out.append(block(ids["activity"], ["prov:Activity"], [
        ("rdfs:label", lit(src["activity_label"], "en")),
        ("prov:startedAtTime", lit(RECORDED, dt="xsd:dateTime")),
        ("prov:used", ids["witness"]),
        ("prov:qualifiedAssociation", bnode(["prov:Association"], [
            ("prov:agent", agent), ("prov:hadRole", "mrs:role_extractor")]))],
        comment="The extraction run. NO adjudicator association: nothing below has been reviewed."))

    # ---- work, recension, edition, witness
    ibn_ishaq = resolve(src["work"]["creator"], "work creator")
    ibn_hisham = resolve(src["recension"]["creator"], "recension creator")
    out.append(block(ids["work"], ["mrs:Work"], [
        ("rdfs:label", lit(src["work"]["label"], "en")),
        ("rdfs:comment", lit(src["work"]["comment"], "en")),
        ("dct:creator", ibn_ishaq),
        ("lrmoo:R3_is_realised_in", ids["recension"])] + stamp(),
        comment="THE SOURCE: Work -> Recension -> Edition -> Witness -> Passage (docs/02 §8.9)."))
    out.append(block(ids["recension"], ["mrs:Recension"], [
        ("rdfs:label", lit(src["recension"]["label"], "en")),
        ("rdfs:label", lit(src["recension"]["title_ar"], "ar")),
        ("dct:identifier", lit(src["recension"]["openiti_book_uri"])),
        ("dct:creator", ibn_hisham),
        ("rdfs:comment", lit(src["recension"]["comment"], "en"))] + stamp()))
    ed = src["edition"]
    out.append(block(ids["edition"], ["mrs:Edition"], [
        ("rdfs:label", lit(ed["label"], "en")),
        ("dct:bibliographicCitation", lit(ed["as_in_openiti_metadata"], "ar")),
        ("lrmoo:R4_embodies", ids["recension"]),
        ("rdfs:comment", lit(ed["comment"], "en"))] + stamp(),
        comment="PROVISIONAL EDITION (maintainer decision E33): the scholars will specify the edition of record."))
    out.append(block(ids["witness"], ["mrs:Witness"], [
        ("rdfs:label", lit(w["label"], "en")),
        ("dct:identifier", lit(w["version_uri"])),
        ("dct:source", ids["edition"]),
        ("mrs:externalIdentifier", lit(w["raw_url"], dt="xsd:anyURI")),
        ("dct:license", f"<{w['licence_url']}>"),
        ("dct:rights", lit(w["licence_note"], "en")),
        ("spdx:checksum", bnode(["spdx:Checksum"], [
            ("spdx:algorithm", "spdx:checksumAlgorithm_sha256"),
            ("spdx:checksumValue", lit(w["sha256"]))])),
        ("dct:extent", lit(w["extent"], "en")),
        ("rdfs:comment", lit(w["comment"], "en"))] + stamp()))
    sd = src["source_date"]
    out.append(block(ids["source_date"], ["mrs:TemporalExtent"], [
        ("rdfs:label", lit(sd["label"], "en")),
        ("mrs:calendar", "mrs:cal_hijri"),
        ("mrs:nativeValue", lit(sd["native_value"])),
        ("mrs:precision", "mrs:pr_period"),
        ("mrs:temporalBasis", "mrs:tbas_inferred"),
        ("mrs:latestEnd", lit(sd["latest_end"], dt="xsd:dateTime")),
        ("mrs:conversionMethod", lit(sd["conversion_method"])),
        ("mrs:conversionUncertaintyDays", str(int(sd["conversion_uncertainty_days"])))],
        comment="When the containing work was composed (D6): every Report below points here."))

    # ---- qualifiers used
    used_q = sorted({q for c in claims for q in c.get("qualifiers", [])})
    if used_q:
        out.append("# Qualifiers on claims (mrs:qualifier), defined by this file.\n")
        for q in used_q:
            label, comment = QUALIFIERS[q]
            out.append(block(f"mrsv:q_{q}", ["mrs:Qualifier"], [
                ("rdfs:label", lit(label, "en")), ("rdfs:comment", lit(comment, "en"))]))

    # ---- new entities
    out.append("#################################################################\n"
               "#  NEW PEOPLE, PLACES AND EVENTS (identity.csv: needs-review)\n"
               "#################################################################\n")
    kind_order = {"person": 0, "place": 1, "event": 2}
    for e, cid, name_ar in sorted(new_ents, key=lambda x: (kind_order[x[0]["kind"]], x[0]["name"])):
        props = [("rdfs:label", lit(e["name"], "en"))]
        if e.get("comment"):
            props.append(("rdfs:comment", lit(e["comment"], "en")))
        if e["kind"] == "person":
            forms = []
            if name_ar:
                forms.append(bnode(["mrs:ArabicNameForm"], [
                    ("mrs:fullFormAsAttested", lit(name_ar)), ("mrs:script", lit("arab")),
                    ("mrs:attestedIn", e["attested"]["passage"])]))
            forms.append(bnode(["mrs:ArabicNameForm"], [
                ("mrs:fullFormAsAttested", lit(e["name"])), ("mrs:script", lit("latn")),
                ("mrs:transliterationScheme", lit("IJMES-style, as written by the AI extraction pass"))]))
            props.append(("mrs:nameForm", " ,\n        ".join(forms)))
            types = ["mrs:Person"]
        elif e["kind"] == "place":
            if e.get("place_type") not in PLACE_TYPES:
                sys.exit(f"place {e['name']!r}: bad place_type {e.get('place_type')}")
            props.append(("mrs:placeType", f"mrs:pt_{e['place_type']}"))
            if not name_ar:
                sys.exit(f"place {e['name']!r}: a new place needs its name as written")
            props.append(("mrs:namePhase", bnode(["mrs:NamePhase"], [("mrs:phaseName", lit(name_ar, "ar"))])))
            types = ["mrs:Place"]
        else:
            types = ["mrs:Event"]
            if name_ar:
                props.append(("rdfs:label", lit(name_ar, "ar")))
            life = e.get("life_event")
            if life:
                person = resolve(life["person"], f"event {e['name']!r}")
                if life["type"] == "birth":
                    types.append("crm:E67_Birth")
                    props.append(("crm:P98_brought_into_life", person))
                elif life["type"] == "death":
                    types.append("crm:E69_Death")
                    props.append(("crm:P100_was_death_of", person))
                else:
                    sys.exit(f"event {e['name']!r}: bad life_event type")
            for psg in sorted(referred.get(cid, [])):
                props.append(("crm:P67i_is_referred_to_by", psg))
        out.append(block(cid, types, props + stamp()))

    # ---- people already in the graph who narrate in a modelled chain, or whose name form is listed
    new_ids = {cid for _, cid, _ in new_ents}
    forms_of = {}
    for x in sorted(chain_people):
        if x in new_ids:
            continue
        p = chain_people[x]
        ch = p["chain"]
        form = next(ln.get("from_name") if ln["_from"] == x else ln.get("to_name")
                    for ln in ch["links"] if x in (ln["_from"], ln["_to"]))
        if not form:
            sys.exit(f"chain {ch['id']}: no attested name span for {x}")
        forms_of[x] = [(as_written(s[p["start"]:p["end"]], [form]), p["id"])]
    for x, forms in existing_forms.items():
        forms_of.setdefault(x, [])
        forms_of[x] += [f for f in forms if f not in forms_of[x]]
    if forms_of:
        out.append("#################################################################\n"
                   "#  PEOPLE ALREADY IN THE GRAPH: typed here with the name form\n"
                   "#  attested in this text (chain narrators, so that this file\n"
                   "#  validates on its own, and the forms listed as existing in\n"
                   "#  ingest/claims/ibn-hisham-entities.jsonl).\n"
                   "#################################################################\n")
        for x in sorted(forms_of):
            out.append(block(x, ["mrs:Person"], [
                ("mrs:nameForm", " ,\n        ".join(bnode(["mrs:ArabicNameForm"], [
                    ("mrs:fullFormAsAttested", lit(name_ar)), ("mrs:script", lit("arab")),
                    ("mrs:attestedIn", pid)]) for name_ar, pid in forms_of[x]))],
                comment=f"{resolve.used[x][1]} (declared in another corpus file)"))

    # ---- passages, reports, chains, claims, in the order of the text
    out.append("#################################################################\n"
               "#  PASSAGES, REPORTS AND CLAIMS, in the order of the text\n"
               "#################################################################\n")
    counts = {}
    for p in sorted(passages, key=lambda x: x["start"]):
        raw = s[p["start"]:p["end"]]
        first_line, last_line = text.line(p["start"]), text.line(p["end"] - 1)
        pg1, pg2 = text.page(p["start"]), text.page(p["end"] - 1)
        ms1, ms2 = text.milestone(p["start"]), text.milestone(p["end"] - 1)
        if pg1 and pg2:
            pages = (f"vol. {pg1[0]}, p. {pg1[1]}" if pg1 == pg2 else
                     f"vol. {pg1[0]}, pp. {pg1[1]}\u2013{pg2[1]}" if pg1[0] == pg2[0] else
                     f"vol. {pg1[0]}, p. {pg1[1]} \u2013 vol. {pg2[0]}, p. {pg2[1]}")
        else:
            pages = "page not marked"
        miles = f"ms{ms1:03d}" if ms1 == ms2 else f"ms{ms1:03d}\u2013ms{ms2:03d}"
        lines = f"line {first_line}" if first_line == last_line else f"lines {first_line}\u2013{last_line}"
        # Short on purpose: the citation is shown beside every claim, and a page that carries hundreds
        # of them must stay inside its size budget. The full edition, the OpenITI version, the
        # checksum and the character offsets are on the Edition, Witness and selector of the passage.
        citation = (f"Ibn Hish\u0101m, al-S\u012bra al-Nabawiyya (al-Saqq\u0101 et al. ed., Cairo 1375/1955; "
                    f"provisional), {pages}; OpenITI {miles}, {lines}")
        out.append(block(p["id"], ["mrs:Passage", "oa:SpecificResource"], [
            ("rdfs:label", lit(p["label"], "en")),
            ("mrs:canonicalCitation", lit(citation)),
            ("mrs:inWitness", ids["witness"]),
            ("dct:isPartOf", ids["work"]),
            ("oa:hasSource", ids["witness"]),
            ("oa:hasSelector", bnode(["oa:TextPositionSelector"], [
                ("oa:start", str(p["start"])), ("oa:end", str(p["end"]))])),
            ("spdx:checksum", bnode(["spdx:Checksum"], [
                ("spdx:algorithm", "spdx:checksumAlgorithm_sha256"),
                ("spdx:checksumValue", lit(p["sha256"]))]))] + stamp()))

        cl = by_passage.get(p["id"], [])
        rprops = [("rdfs:label", lit(p["label"], "en")),
                  ("mrs:matnText", lit(src["matn_notice"], "en"))]
        if p.get("ascription"):
            rprops.append(("crm:P3_has_note", lit(as_written(raw, [p["ascription"]]), "ar")))
        rprops += [("mrs:terminalAscription", f"mrs:asc_{p['ascription_class']}"),
                   ("mrs:reportGenre", "mrs:rg_sira_maghazi"),
                   ("mrs:locatedIn", p["id"]),
                   ("mrs:sourceDate", ids["source_date"])]
        if p.get("chain"):
            rprops.append(("mrs:hasChain", p["chain"]["id"]))
        if p.get("note"):
            rprops.append(("rdfs:comment", lit(p["note"], "en")))
        if cl:
            rprops.append(("mrs:asserts", " , ".join(c["id"] for c in cl)))
        out.append(block(p["report"], ["mrs:Report"], rprops + stamp()))

        ch = p.get("chain")
        if ch:
            links = []
            for k, ln in enumerate(ch["links"], 1):
                lprops = [("mrs:linkOrder", str(k)), ("mrs:fromNarrator", ln["_from"]),
                          ("mrs:toNarrator", ln["_to"]), ("mrs:transmissionMode", f"mrs:tm_{ln['mode']}")]
                if ln.get("term"):
                    lprops.append(("rdfs:label", lit(as_written(raw, [ln["term"]]), "ar")))
                links.append(bnode(["mrs:TransmissionLink"], lprops))
            cprops = [("rdfs:label", lit(as_written(raw, [ch["as_written"]]), "ar"))]
            if ch.get("_terminal"):
                cprops.append(("mrs:terminalNarrator", ch["_terminal"]))
            if ch.get("_collector"):
                cprops.append(("mrs:collector", ch["_collector"]))
            cprops.append(("mrs:hasLink", " ,\n        ".join(links)))
            out.append(block(ch["id"], ["mrs:TransmissionChain"], cprops + stamp(),
                             comment="mrs:continuity deliberately absent: a scholar's determination."))

        for c in cl:
            props = [("mrs:predicate", f"mrs:{c['predicate']}"),
                     ("mrs:assertionSubject", c["_subject"]),
                     ("mrs:assertionObject", c["_object"])]
            if "age" in c:
                props.append(("mrs:ageAsWritten", lit(as_written(raw, c["age"]["spans"]), "ar")))
                for y in c["age"].get("years", []):
                    props.append(("mrs:ageYearsAsGiven", lit(str(y), dt="xsd:decimal")))
            if "date" in c:
                props.append(("mrs:dateAsWritten", lit(as_written(raw, c["date"]["spans"]), "ar")))
            props += [("mrs:assertionStatus", "mrs:as_proposed"),
                      ("mrs:fromReport", p["report"])]
            for q in c.get("qualifiers", []):
                props.append(("mrs:qualifier", f"mrsv:q_{q}"))
            props += [("rdfs:comment", lit("AI gloss (proposed; machine-written, not reviewed, not a translation): "
                                           + c["gloss"], "en")),
                      ("prov:wasDerivedFrom", p["id"]),
                      ("oa:hasTarget", bnode(["oa:SpecificResource"], [
                          ("oa:hasSource", p["id"]),
                          ("oa:hasSelector", bnode(["oa:TextPositionSelector"], [
                              ("oa:start", str(c["span"][0])), ("oa:end", str(c["span"][1]))], indent=12))])),
                      ("prov:wasGeneratedBy", ids["activity"])]
            out.append(block(c["id"], ["mrs:Assertion", "oa:Annotation"], props + stamp()))
            counts[c["predicate"]] = counts.get(c["predicate"], 0) + 1

    ttl = "\n".join(out)
    stats = {"passages": len(passages), "claims": len(claims), "by_predicate": counts,
             "new_entities": {k: sum(1 for e, _, _ in new_ents if e["kind"] == k) for k in KIND_PREFIX},
             "existing_entities": len({x for x in resolve.used if x not in new_ids})}
    return ttl, stats


# ---------------------------------------------------------------- review sheet (local only)


def review(src: dict, text: Text):
    """An HTML page, for local use only (it quotes the text): each claim beside its Arabic span."""
    resolve = Resolver()
    names = {}
    for r in resolve.rows:
        names[r["canonical_id"]] = r["preferred_name_en"]
    passages = {p["id"]: p for p in read_all(PASSAGES, FULL_PASSAGES)}
    rows = []
    for n, c in enumerate(read_all(CLAIMS, FULL_CLAIMS), 1):
        p = passages[c["passage"]]
        raw = text.s[p["start"]:p["end"]]
        a, b = c["span"]
        before, span, after = clean(raw[max(0, a - 300):a]), clean(raw[a:b]), clean(raw[b:b + 200])
        subj = names.get(resolve(c["subject"], c["id"]), "?")
        obj = c["object"]
        objtxt = as_written(raw, obj["literal_spans"]) if "literal_spans" in obj else names.get(resolve(obj, c["id"]), "?")
        extra = ""
        if "age" in c:
            extra += f" | age as written: {as_written(raw, c['age']['spans'])} {c['age'].get('years', '')}"
        if "date" in c:
            extra += f" | date as written: {as_written(raw, c['date']['spans'])}"
        rows.append(
            f"<tr><td>{n}</td><td>{html.escape(c['id'])}<br>{html.escape(p['label'])}<br>"
            f"<small>lines {text.line(p['start'])}\u2013{text.line(p['end'] - 1)}</small></td>"
            f"<td>{html.escape(subj)} <b>{html.escape(c['predicate'])}</b> {html.escape(objtxt)}"
            f"{html.escape(extra)}<br><small>{html.escape(c['gloss'])}</small>"
            f"<br><small>{html.escape(' '.join(c.get('qualifiers', [])))}</small></td>"
            f"<td dir=rtl lang=ar>\u2026{html.escape(before[-120:])} <mark>{html.escape(span)}</mark> "
            f"{html.escape(after[:80])}\u2026</td></tr>")
    REVIEW.write_text(
        "<!doctype html><meta charset=utf-8><title>Ibn Hisham claims (local review; contains CC BY-NC-SA text: "
        "do not publish)</title><style>body{font-family:sans-serif}td{vertical-align:top;border-bottom:1px solid #ccc;"
        "padding:4px}td[dir]{font-size:1.2em;max-width:40em}</style><p>Local review sheet. It quotes the OpenITI text "
        "(CC BY-NC-SA 4.0): never commit or publish it.</p><table>" + "\n".join(rows) + "</table>",
        encoding="utf-8")
    print(f"wrote {REVIEW.relative_to(ROOT)} ({len(rows)} claims)")


def locate(src: dict, text: Text, passage_id: str, phrase: str):
    p = {x["id"]: x for x in read_all(PASSAGES, FULL_PASSAGES)}.get(passage_id)
    if p is None:
        sys.exit(f"unknown passage {passage_id}")
    raw = text.s[p["start"]:p["end"]]
    cl, idx = clean_with_map(raw)
    target = re.sub(r"\s+", " ", phrase.strip())
    hits = [m.start() for m in re.finditer(re.escape(target), cl)]
    for h in hits:
        a, b = idx[h], idx[h + len(target) - 1] + 1
        print(json.dumps({"span": [a, b], "span_sha256": sha256_text(raw[a:b])}))
    if not hits:
        sys.exit("not found")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("command", nargs="?", default="build", choices=["fetch", "build", "check", "review", "locate"])
    ap.add_argument("args", nargs="*")
    a = ap.parse_args()
    src = json.loads(SOURCE.read_text(encoding="utf-8"))
    if a.command == "fetch":
        fetch(src)
        return 0
    text = Text(load_text(src))
    if a.command == "review":
        review(src, text)
        return 0
    if a.command == "locate":
        locate(src, text, *a.args)
        return 0
    ttl, stats = build_ttl(src, text)
    if a.command == "check":
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != ttl:
            print(f"{OUT.relative_to(ROOT)} is out of date: run `ingest/ibn_hisham.py build`")
            return 1
        print(f"{OUT.relative_to(ROOT)} is up to date ({stats['claims']} claims)")
        return 0
    OUT.write_text(ttl, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {stats['passages']} reports, {stats['claims']} claims, "
          f"{sum(stats['new_entities'].values())} new entities {stats['new_entities']}, "
          f"{stats['existing_entities']} existing entities referenced")
    for k, v in sorted(stats["by_predicate"].items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {v:4d}  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
