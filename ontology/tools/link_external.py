#!/usr/bin/env python3
"""
Propose external-identifier candidates for the people, places and works in the graph (slice 5).

    .venv/bin/python ontology/tools/link_external.py             # fetch what is not cached yet, write the CSVs
    .venv/bin/python ontology/tools/link_external.py --offline   # cache only: a cache miss is an error
    .venv/bin/python ontology/tools/link_external.py --check     # cache only: exit 1 if a CSV on disk differs
    .venv/bin/python ontology/tools/link_external.py --report    # also list ties, contradictions, uncovered

Reads ontology/corpus/identity.csv and the Turtle files build_graph.py loads. Writes, in ontology/corpus/:
  external-ids.csv          one row per candidate (CC0, like every table mapping our IDs to external IDs)
  external-ids-althurayya.csv  the al-Thurayya candidates, kept apart under al-Thurayya's CC BY 4.0
  external-coordinates.csv  the coordinates each place candidate carries, for the map, with their source
  external-dates.csv        birth and death statements of every person candidate on Wikidata, for the
                            lifelines view: value exactly as given, precision, calendar model, rank, qualifiers
                            (age at event P3629, refine date P4241, circa P1480, earliest/latest date ...).
                            Deprecated statements are left out. The query service gives day-precise Julian
                            dates converted to the proleptic Gregorian calendar; for those rows the value is
                            the one Wikidata stores (Special:EntityData) and the note says so, so that value
                            and calendar_model always agree. A value at year precision, e.g.
                            0610-01-01T00:00:00Z, means the year 610, not 1 January.
Every response is cached under build/cache/link_external/ (gitignored), keyed by the exact query or URL,
so a re-run is deterministic and needs no network.

Every row is a PROPOSAL for scholars: status is always `proposed`. Nothing here merges, splits or
edits an entity, and nothing is written into the corpus (docs/02 §5.2 rule 4 and §8.2). Every
external_id is copied from a response received from the source; none is constructed.

Sources
  wikidata    query.wikidata.org/sparql only. Per entity: search queries through the MWAPI service (entity
              search in English and Arabic, full-text search; each batched with VALUES), then one query for
              the candidates' labels, aliases, description, P31, P21, P569/P570, P625, P13870 (OpenITI
              author ID) and family links (P22 P25 P26 P40 P3373), then one for the person candidates'
              dates. At most one request starts per second; up to five run at once (the WDQS limit).
  althurayya  al-Thurayya gazetteer, master/places.geojson (data CC BY 4.0, al-Thurayya Gazetteer Project).
  openiti     OpenITI author metadata (kitab-metadata-automation output; it records wikidata@Q links),
              Wikidata P13870, and for works the OpenITI light metadata (titles).

Names are compared after one normalisation (diacritics, ʿ ʾ and apostrophes, al-/as-/..., ibn/bin/b./bint,
Abdullah = ʿAbd Allāh, final -ah): equal; one extends the other (3+ shared leading words); loosely equal
(doubled letters, a leading bilad); in part (the first name agrees and one name's words are all in the
other, words compared by consonants, e.g. Tayyihan/Tayyahan, Warqa/Verka). The last level can never give
more than needs-review.

Left out before ranking: for people, an item that is not human, whose dated life falls outside 500-950 CE,
whose gender contradicts our name form (bint, Umm, -iyya), or whose description is plainly modern; and, for
anyone the corpus places at an event (all of the Prophet's lifetime) or records as a ṣaḥābī, an item born
after 640 or dead after 740 CE. For places: an item with no coordinates, an event, (unless our place is a
structure) a building or infrastructure, and an item more than 100 km from the corpus's own point (listed by
--report, not in the CSV).

Confidence (at most one `exact` per entity and system; when the best candidates are equally supported on
every count, all of them are needs-review)
  person/wikidata
    exact         one of our full name forms (3+ words, or fewer with a family link or our death date) equals
                  a label or alias, no rival is as well supported, nothing contradicts (our death date), and
                  something besides the name agrees: our death date, a family link (our spouse, parent, child
                  or sibling matched to an item this one names as family), or a dated life in 500-950 CE
                  together with a description of the period (companion, Muhammad, Islam, Quraysh, ...).
    probable      the name equals or extends ours (or loosely equals it, for 3+ words), uniquely; nothing
                  contradicts; the period, the description, a family link or our date agrees.
    needs-review  every other plausible candidate: ties, partial names, homonyms of the best match.
  place/wikidata, place/althurayya
    exact         the English or Arabic name equals, uniquely, and the candidate lies within 15 km of the
                  corpus's own (proposed) point.
    probable      the name equals, uniquely, and the candidate lies within 50 km of our point; or, without a
                  point of ours, al-Thurayya (a gazetteer of the classical Islamic world) has exactly one entry
                  with the name and a Wikidata candidate of that name lies within 30 km of it (300 km for
                  regions): then both are probable. A modern administrative unit is never more than probable.
    needs-review  name equality without location agreement, several same-name entries, or an equal core
                  name (Ghar Hira / Cave of Hira) of the same kind (cave, mountain, valley ...).
  person/openiti  through the person's exact or probable Wikidata candidate (its P13870, or OpenITI's own
                  wikidata@ link), or an OpenITI author name equal to ours (2+ words) within the person's
                  possible lifetime. Never more confident than the Wikidata candidate it comes through; exact
                  needs both directions to agree. A direct name match alone is needs-review (probable when
                  our death year agrees with OpenITI's).
  work/openiti    a title equal after normalisation, or a book of the work's author with shared title words.

Exit codes:  0 = done   1 = --check found a difference   2 = could not run (e.g. cache miss offline)
"""

import argparse
import concurrent.futures
import csv
import hashlib
import io
import json
import math
import re
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from rdflib import RDF, RDFS, BNode, Graph, Namespace, URIRef
except ImportError:
    sys.exit("Requires rdflib:  pip install rdflib")

ONT = Path(__file__).resolve().parent.parent
ROOT = ONT.parent
IDENTITY = ONT / "corpus" / "identity.csv"
DATA = sorted((ONT / "corpus").glob("*.ttl")) + sorted((ONT / "examples").glob("*.ttl"))
OUT_IDS = ONT / "corpus" / "external-ids.csv"
# al-Thurayya's rows keep its licence (CC BY 4.0), so they live in their own credited file (maintainer S6)
OUT_IDS_TH = ONT / "corpus" / "external-ids-althurayya.csv"
OUT_COORDS = ONT / "corpus" / "external-coordinates.csv"
CACHE = ROOT / "build" / "cache" / "link_external"

MRS = Namespace("https://w3id.org/marsad/core#")
DCT = Namespace("http://purl.org/dc/terms/")
PROV = Namespace("http://www.w3.org/ns/prov#")
GEO_WKT = URIRef("http://www.opengis.net/ont/geosparql#asWKT")
BASE = "https://w3id.org/marsad/id/"
TOKEN_PREFIX = {"person": "per", "place": "plc", "work": "wrk"}
KINDS = ("person", "place", "work")
SYSTEMS = ("wikidata", "althurayya", "openiti")
CONF_RANK = {"exact": 0, "probable": 1, "needs-review": 2}

UA = ("al-Marsad-link-external/1.0 (https://github.com/thajudeenUrbane/al-marsad; "
      "proposes external-ID candidates for a Seerah knowledge graph; one request per second)")
WDQS = "https://query.wikidata.org/sparql"
THURAYYA_URL = "https://raw.githubusercontent.com/althurayya/althurayya.github.io/master/master/places.geojson"
OPENITI_AUTHORS_URL = ("https://raw.githubusercontent.com/OpenITI/kitab-metadata-automation/master/output/"
                       "OpenITI_Github_clone_all_author_meta.json")
OPENITI_BOOKS_URL = ("https://raw.githubusercontent.com/OpenITI/kitab-metadata-automation/master/output/"
                     "OpenITI_Github_clone_metadata_light.csv")
THURAYYA_SOURCE = "al-Thurayya Gazetteer Project, places.geojson (CC BY 4.0)"

PERIOD = (500, 950)          # CE: a dated life inside this window "fits the period"
SEERAH_LIFE = (640, 570, 740)  # CE: someone the corpus places at events of the Prophet's lifetime (or a ṣaḥābī)
                               # was born by 640 and died between 570 and 740; a candidate outside is left out
SEERAH_PREDICATES = {"rel_participated_in", "rel_led", "rel_witnessed", "rel_present_at", "rel_absent_from",
                     "rel_pledged_allegiance_to", "rel_party_to_treaty_with"}
LABEL_LANGS = ("en", "mul", "de", "fr", "es", "it", "id", "ms", "tr", "nl")   # Latin-script label languages compared
MALE, FEMALE = "Q6581097", "Q6581072"
NOT_A_PLACE = {"Q5", "Q4167410", "Q13406463", "Q4167836", "Q11266439", "Q202444", "Q101352", "Q178561",
               "Q831663", "Q645883", "Q180684", "Q1656682", "Q13418847", "Q41710", "Q482994", "Q7725634"}
PERIOD_CUE = re.compile(r"compan|sahab|muhammad|prophet|islam|muslim|caliph|hadith|narrat|muhaddith|traditionist|"
                        r"quraysh|qurash|ansar|muhajir|mecca|makkah|medina|madina|badr|uhud|abyssinia|aksum|negus|"
                        r"hijaz|arab|rashidun|umayyad|abbasid|tabi|faqih|imam|sira|seerah|ummah", re.I)
REGION_CUE = re.compile(r"region|country|kingdom|empire|peninsula|province", re.I)
ADMIN_CUE = re.compile(r"governorate|province of|district|municipality|county|prefecture|administrative|"
                       r"neighbou?rhood|region of saudi arabia|\bislah\b|\buzlah\b|muhafaz", re.I)
BUILDING_CUE = re.compile(r"\b(?:mosque|masjid|church|airport|airfield|railway|station|hotel|mall|stadium|university|"
                          r"college|school|academy|hospital|company|museum|bridge|dam|tower|street|road|highway|mint|"
                          r"fort|fortress|castle|caravanserai|palace|arms deal)\b", re.I)
GEO_GENERIC = {"ghar", "jabal", "jebel", "wadi", "bilad", "shib", "ard", "mount", "mountain", "cave", "plain", "valley",
               "oasis", "city", "of", "the", "b"}
GEO_KIND = {"ghar": "cave", "cave": "cave", "jabal": "mountain", "jebel": "mountain", "mount": "mountain",
            "mountain": "mountain", "wadi": "valley", "valley": "valley", "bilad": "region", "ard": "region",
            "plain": "plain", "oasis": "oasis"}
GEO_SEARCH = {"ghar": "cave of", "jabal": "mount", "jebel": "mount", "wadi": "wadi"}   # search spellings only


def kinds(text):
    return {GEO_KIND[w] for w in re.findall(r"[a-z]+", fold(text)) if w in GEO_KIND}
MODERN_CUE = re.compile(r"orcid|ph\.?d|researcher|football|cricket|basketball|athlete|player|actor|actress|singer|rapper|"
                        r"musician|politician|journalist|businessman|businesswoman|engineer|scientist|physician|"
                        r"professor|academic|film|television|youtuber|model|wikimedian|\b(?:1[6-9]|20)\d\d\b", re.I)
EVENT_CUE = re.compile(r"\b(battle|campaign|expedition|siege|war|treaty|raid|conquest)\b", re.I)


class CacheMiss(Exception):
    pass


# ---------------------------------------------------------------- normalisation

SPECIAL = {"ḫ": "kh", "ǧ": "j", "š": "sh", "ṯ": "th", "ḏ": "dh", "ġ": "gh", "ŧ": "a", "ẗ": "a", "ı": "i",
           "ʿ": "", "ʾ": "", "'": "", "’": "", "‘": "", "`": "", "´": "", "ʻ": "", "ʼ": "", "ʹ": "", "′": "",
           "ﷺ": " "}
ARTICLE = re.compile(r"(?<![a-z])(?:al|el|ul|il|l|an|ar|as|ash|at|ath|az|ad|adh|ag)-(?=[a-z])")
CONNECT = {"ibn": "b", "bin": "b", "b": "b", "ben": "b", "bint": "b", "bt": "b", "binti": "b", "bte": "b",
           "ibnu": "b", "ibnat": "b"}
COMMON = {"mohammed": "muhammad", "mohammad": "muhammad", "muhammed": "muhammad", "mohamed": "muhammad",
          "mohamad": "muhammad", "muhamad": "muhammad", "ahmed": "ahmad", "omar": "umar", "othman": "uthman",
          "osman": "uthman", "usman": "uthman", "hussein": "husayn", "husain": "husayn", "hussain": "husayn",
          "hossein": "husayn", "husein": "husayn", "aishah": "aisha", "ayesha": "aisha", "aysha": "aisha"}
GENERIC = {"b", "abu", "abi", "aba", "umm", "al", "the", "of", "and"}
HONORIFIC = re.compile(r"\((?:peace|may allah|pbuh|saw|s\.a\.w|r\.a|radi)[^)]*\)|\bpbuh\b", re.I)
TITLE = re.compile(r"^(?:the\s+)?(?:prophet|caliph|imam|sayyidina|sayyiduna|hazrat)\s+", re.I)


def fold(s):
    s = "".join(SPECIAL.get(ch, ch) for ch in s)
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower()


def _token(t):
    t = COMMON.get(t, t)
    if t.startswith("abd") and len(t) > 5:                       # abdullah, abdulrahman, abdurrahman, abdelaziz
        rest = t[3:]
        if rest in ("ullah", "allah", "illah", "ulla", "alla", "ulah", "alah", "ollah"):
            rest = "allah"
        else:
            for pre in ("ul", "ur", "us", "ud", "un", "el", "er", "al", "ar", "u", "e", "a", "i"):
                if rest.startswith(pre) and len(rest) - len(pre) >= 3:
                    rest = rest[len(pre):]
                    break
        t = "abd" + rest
    elif len(t) > 6 and (t.endswith("ullah") or t.endswith("illah")):   # ubaydullah
        t = t[:-5] + "allah"
    t = re.sub(r"^dsch", "j", t)
    t = t.replace("dj", "j").replace("sch", "sh").replace("ou", "u").replace("oo", "u").replace("ee", "i")
    t = t.replace("ai", "ay").replace("au", "aw")
    if t.startswith("o") and len(t) >= 4:
        t = "u" + t[1:]
    if len(t) > 3 and t.endswith("ah") and not t.endswith("allah"):
        t = t[:-1]
    t = re.sub(r"([aiu])\1+", r"\1", t)
    return t


def name_key(s):
    """Strict comparison key: diacritics, apostrophes, articles and ibn/bint/b. spellings unified."""
    s = ARTICLE.sub("", fold(s))
    toks = [t for t in re.split(r"[^a-z0-9]+", s) if t]
    out = []
    i = 0
    while i < len(toks):
        t = CONNECT.get(toks[i], toks[i])
        if t in ("al", "el"):
            i += 1
            continue
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if t in ("abd", "abdul", "abdel", "abdu", "abdur", "abdus", "abdal") and nxt and nxt not in CONNECT:
            nxt2 = toks[i + 2] if nxt in ("al", "el") and i + 2 < len(toks) else None
            t, i = ("abd" + nxt2, i + 2) if nxt2 else ("abd" + nxt, i + 1)
        elif nxt == "allah" and t not in CONNECT:
            t, i = t + "allah", i + 1
        out.append(_token(t) if t != "b" else t)
        i += 1
    return " ".join(out)


def loose_key(k):
    """Looser key: doubled letters collapsed, a leading 'bilad' (land of) dropped."""
    toks = [re.sub(r"(.)\1+", r"\1", t) for t in k.split()]
    if len(toks) > 1 and toks[0] == "bilad":
        toks = toks[1:]
    return " ".join(toks)


AR_MARKS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")
AR_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي", "ء": ""})


def ar_key(s):
    s = AR_MARKS.sub("", s).translate(AR_MAP)
    s = re.sub(r"[^ء-ي\s]", " ", s)
    return " ".join(s.split())


def ar_loose(k):
    toks = [t[2:] if t.startswith("ال") and len(t) > 3 else t for t in k.split()]
    if len(toks) > 1 and toks[0] in ("بلاد", "ارض"):
        toks = toks[1:]
    return " ".join(toks)


def is_arabic(s):
    return bool(re.search(r"[؀-ۿ]", s))


def specific(tokens):
    return [t for t in tokens if t not in GENERIC]


def name_level(ok, ck):
    """How well our key ok matches candidate key ck: 5 equal, 4 one extends the other (3+ tokens),
    3 loose-equal, 2 loose extension or 2-token extension, 1 containment, 0 two shared words, -1 none."""
    if not ok or not ck:
        return -1
    if ok == ck:
        return 5
    a, b = ok.split(), ck.split()
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if long_[:len(short)] == short and len(short) >= 3:
        return 4
    la, lb = loose_key(ok), loose_key(ck)
    if la == lb:
        return 3
    sa, sb = la.split(), lb.split()
    ls, ll = (sa, sb) if len(sa) <= len(sb) else (sb, sa)
    if ll[:len(ls)] == ls and (len(ls) >= 3 or (len(ls) == 2 and specific(ls))):
        return 2
    spa, spb = specific(sa), specific(sb)
    if not spa or not spb:
        return -1

    def covered(xs, ys):
        return all(any(same_word(x, y) for y in ys) for x in xs)
    if same_word(spa[0], spb[0]) and (covered(spa, spb) or covered(spb, spa)):
        return 1                      # the first name agrees and one name's words are all in the other
    if sum(1 for t in set(spa) if any(same_word(t, u) for u in spb)) >= 2:
        return 0
    return -1


def skeleton(t):
    """Consonants only (y and w kept), th/dh as s/z, and the Turkish spellings common on Wikidata (v for w,
    k for q, c for j): 'tayyihan' and 'tayyahan' agree, so do 'haytham' and 'heysam', 'warqa' and 'verka'.
    Used only for the weak levels (at most needs-review)."""
    s = t.replace("th", "s").replace("dh", "z").replace("v", "w").replace("q", "k").replace("c", "j")
    s = re.sub(r"[aeiou]", "", s)
    return re.sub(r"(.)\1+", r"\1", s).rstrip("h")


def same_word(a, b):
    if a == b:
        return True
    ka, kb = skeleton(a), skeleton(b)
    return len(ka) >= 3 and ka == kb


def haversine(p, q):
    """Great-circle distance in km between (lat, lon, ...) tuples."""
    la1, lo1, la2, lo2 = p[0], p[1], q[0], q[1]
    r = math.pi / 180
    h = math.sin((la2 - la1) * r / 2) ** 2 + math.cos(la1 * r) * math.cos(la2 * r) * math.sin((lo2 - lo1) * r / 2) ** 2
    return 2 * 6371.0 * math.asin(min(1.0, math.sqrt(h)))


def ah_to_ce(ah):
    return round(622 + ah * 0.970224)


# ---------------------------------------------------------------- fetching and cache

class Fetcher:
    """Cached HTTP. At most one request starts per second (shared by the prefetch threads)."""

    def __init__(self, offline):
        self.offline = offline
        self.last = 0.0
        self.fetched = 0
        self.hits = 0
        self.pace = threading.Lock()

    def _path(self, ns, key):
        return CACHE / ns / (hashlib.sha256(key.encode("utf-8")).hexdigest()[:32] + ".json")

    def _cached(self, ns, key, fetch):
        path = self._path(ns, key)
        if path.exists():
            self.hits += 1
            return json.loads(path.read_text(encoding="utf-8"))["response"]
        if self.offline:
            raise CacheMiss(f"{ns}: {key[:100]!r}")
        resp = fetch()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps({"key": key, "response": resp}, ensure_ascii=False, sort_keys=True),
                       encoding="utf-8")
        tmp.replace(path)
        self.fetched += 1
        return resp

    def prefetch(self, queries, label):
        """Fetch uncached SPARQL queries with five threads (the WDQS limit of parallel queries per client),
        still starting at most one request per second. Results land in the cache only."""
        todo = sorted({q for q in queries if not self._path("wikidata", q).exists()})
        if not todo or self.offline:
            return
        print(f"  {label}: fetching {len(todo)} queries", file=sys.stderr)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            for i, _ in enumerate(pool.map(self.sparql, todo), 1):
                if i % 50 == 0:
                    print(f"    {i}/{len(todo)}", file=sys.stderr)

    def _http(self, url, data=None, accept=None):
        headers = {"User-Agent": UA}
        if accept:
            headers["Accept"] = accept
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        for attempt in range(8):
            with self.pace:                                    # about one request per second
                wait = 1.0 - (time.monotonic() - self.last)
                if wait > 0:
                    time.sleep(wait)
                self.last = time.monotonic()
            try:
                with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers),
                                            timeout=75) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace") if e.code == 500 else ""
                transient = e.code in (429, 502, 503, 504) or (e.code == 500 and "Timeout" in body)
                if not transient or attempt == 7:
                    cause = re.findall(r"(\w+(?:Exception|Error): [^\n]{0,160})", body)
                    raise RuntimeError(f"HTTP {e.code} from {url}: {cause[-1] if cause else e.reason}") from None
                ra = e.headers.get("Retry-After", "")
                delay = float(ra) if ra.isdigit() else min(120, 2 ** (attempt + 1))
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt == 7:
                    raise
                delay = min(120, 2 ** (attempt + 1))
            print(f"  retry in {delay:.0f}s", file=sys.stderr)
            time.sleep(delay)

    def sparql(self, query):
        def go():
            body = self._http(WDQS, data=urllib.parse.urlencode({"query": query}).encode(),
                              accept="application/sparql-results+json")
            res = json.loads(body)
            return [{k: v["value"] for k, v in b.items()} for b in res["results"]["bindings"]]
        return self._cached("wikidata", query, go)

    def text(self, ns, url):
        return self._cached(ns, url, lambda: self._http(url).decode("utf-8"))


# ---------------------------------------------------------------- entities

def curie(iri):
    s = str(iri)
    for kind, pre in TOKEN_PREFIX.items():
        b = f"{BASE}{kind}/"
        if s.startswith(b):
            return f"{pre}:{s[len(b):]}"
    return None


def split_list(v):
    return [x.strip() for x in (v or "").split(";") if x.strip()]


def display_forms(label):
    """A label's usable name forms: honorifics dropped; 'A (B), C' gives A and B (B only when it is a name);
    a leading title gives a second form without it."""
    s = HONORIFIC.sub(" ", label)
    main, _, _tail = s.partition(",")
    forms = [re.sub(r"\([^)]*\)", " ", main)]
    for alt in re.findall(r"\(([^)]*)\)", main):
        alt = re.sub(r"^(?:formerly|now|later|modern|also)\s+", "", alt.strip(), flags=re.I)
        if alt[:1].isupper() or alt[:1] in "ʿʾ'‘":
            forms.append(alt)
    out = []
    for f in forms:
        f = " ".join(f.split())
        if f:
            out.append(f)
            t = TITLE.sub("", f)
            if t != f and t:
                out.append(t)
    return out


def years(te, g):
    ys = []
    for p in (MRS.earliestStart, MRS.latestEnd, MRS.latestStart, MRS.earliestEnd):
        for v in g.objects(te, p):
            m = re.match(r"(-?\d{1,4})-", str(v))
            if m:
                ys.append(int(m.group(1)))
    return (min(ys), max(ys)) if ys else None


def rdf_list(g, node):
    out = []
    while node is not None and node != RDF.nil:
        first = g.value(node, RDF.first)
        if first is not None:
            out.append(str(first))
        node = g.value(node, RDF.rest)
    return out


def load_entities():
    ents = {}
    variant = {}

    def ent(cid, kind):
        return ents.setdefault(cid, {"id": cid, "kind": kind, "names": [], "names_ar": [], "death": None,
                                     "points": [], "ptype": None, "tabaqa": None, "kin": {}, "creators": [],
                                     "placeholder": False, "at_event": False})

    def add(e, text, src):
        for f in display_forms(text):
            (e["names_ar"] if is_arabic(f) else e["names"]).append((f, src))

    rows = list(csv.DictReader(IDENTITY.open(encoding="utf-8")))
    for r in rows:
        for v in split_list(r.get("variant_ids", "")):
            variant[v] = r["canonical_id"]
    for r in rows:
        if r["kind"] not in KINDS:
            continue
        e = ent(r["canonical_id"], r["kind"])
        add(e, r["preferred_name_en"], "identity.csv")
        for n in split_list(r.get("name_ar", "")):
            e["names_ar"].append((n, "identity.csv"))
        for n in split_list(r.get("stories50_names", "")):
            add(e, n, "stories-50")
        if "placeholder label" in r.get("note", "") or r["preferred_name_en"].lower().startswith("route waypoint"):
            e["placeholder"] = True

    g = Graph()
    for f in DATA:
        g.parse(f, format="turtle")

    def cid_of(node):
        c = curie(node)
        return variant.get(c, c) if c else None

    for cls, kind in ((MRS.Person, "person"), (MRS.Place, "place"), (MRS.Work, "work")):
        for s in sorted(set(g.subjects(RDF.type, cls)), key=str):
            cid = cid_of(s)
            if not cid:
                continue
            e = ent(cid, kind)
            for lab in sorted(g.objects(s, RDFS.label), key=str):
                add(e, str(lab), "graph label")
            # name forms, phases and geometry are blank nodes, whose IDs change on every parse:
            # order them by content so that search terms (and so cache keys) are the same every run
            def content(node):
                return sorted((str(p), str(o)) for p, o in g.predicate_objects(node) if not isinstance(o, BNode)) + \
                    [("nasab", "|".join(rdf_list(g, g.value(node, MRS.nasab))))]
            for nf in sorted(g.objects(s, MRS.nameForm), key=content):
                for lab in sorted(g.objects(nf, RDFS.label), key=str):
                    add(e, str(lab), "graph name form")
                ism = g.value(nf, MRS.ism)
                kunya = g.value(nf, MRS.kunya)
                nasab = rdf_list(g, g.value(nf, MRS.nasab))
                laqab = sorted(str(x) for x in g.objects(nf, MRS.laqab))
                head = str(ism) if ism is not None else (str(kunya) if kunya is not None else None)
                if head:
                    for i in range(1, len(nasab) + 1):
                        e["names"].append((head + "".join(f" b. {n}" for n in nasab[:i]), "graph name parts"))
                if kunya is not None and ism is None:
                    e["names"].append((str(kunya), "graph name parts"))
                    for lq in laqab:
                        e["names"].append((f"{kunya} {lq}", "graph name parts"))
            spans = sorted(years(te, g) for d in g.objects(s, MRS.death) for te in g.objects(d, MRS.eventTemporalExtent)
                           if years(te, g))
            if spans:
                e["death"] = (min(a for a, _ in spans), max(b for _, b in spans))
            t = g.value(s, MRS.tabaqa)
            e["tabaqa"] = str(t).split("#")[-1] if t is not None else e["tabaqa"]
            for n in sorted({str(n) for ph in g.objects(s, MRS.namePhase) for n in g.objects(ph, MRS.phaseName)}):
                if is_arabic(n):
                    e["names_ar"].append((n, "graph name phase"))
                else:
                    add(e, n, "graph name phase")
            pt = g.value(s, MRS.placeType)
            e["ptype"] = str(pt).split("#")[-1] if pt is not None else e["ptype"]
            for w in sorted({str(w) for gs in g.objects(s, MRS.geometryState) for geom in g.objects(gs, MRS.geometry)
                             for w in g.objects(geom, GEO_WKT)}):
                m = re.match(r"\s*POINT\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s*\)", w)
                if m and (float(m.group(2)), float(m.group(1))) not in e["points"]:
                    e["points"].append((float(m.group(2)), float(m.group(1))))
            for p in (DCT.creator, PROV.wasAttributedTo):
                for c in g.objects(s, p):
                    cc = cid_of(c)
                    if cc and cc not in e["creators"]:
                        e["creators"].append(cc)

    # people the corpus places at events (participations, or assertions that they took part in, led,
    # witnessed, were present at or absent from an event): all events in the graph are of the Prophet's lifetime
    at_event = {cid_of(p) for p in g.objects(None, MRS.participant)}
    for a in g.subjects(RDF.type, MRS.Assertion):
        obj, subj = g.value(a, MRS.assertionObject), g.value(a, MRS.assertionSubject)
        if str(g.value(a, MRS.predicate) or "").split("#")[-1] in SEERAH_PREDICATES and obj is not None and \
                subj is not None and (obj, RDF.type, MRS.Event) in g:
            at_event.add(cid_of(subj))
    for cid in at_event:
        if cid in ents:
            ents[cid]["at_event"] = True

    # family links between persons, from the corpus's (proposed) assertions
    rel = {"rel_spouse_of": ("spouse", "spouse"), "rel_father_of": ("father of", "child of"),
           "rel_mother_of": ("mother of", "child of"), "rel_child_of": ("child of", "parent of"),
           "rel_sibling_of": ("sibling", "sibling")}
    for a in sorted(set(g.subjects(RDF.type, MRS.Assertion)), key=str):
        p = str(g.value(a, MRS.predicate) or "").split("#")[-1]
        if p not in rel:
            continue
        s, o = cid_of(g.value(a, MRS.assertionSubject)), cid_of(g.value(a, MRS.assertionObject))
        if s in ents and o in ents and ents[s]["kind"] == ents[o]["kind"] == "person":
            ents[s]["kin"].setdefault(o, rel[p][0])
            ents[o]["kin"].setdefault(s, rel[p][1])

    for e in ents.values():
        seen, forms = set(), []
        for text, src in e["names"]:
            k = name_key(text)
            if k and k not in seen:
                seen.add(k)
                forms.append({"text": text, "key": k, "src": src, "n": len(k.split())})
        e["forms"] = forms
        seen_ar, forms_ar = set(), []
        for text, src in e["names_ar"]:
            k = ar_key(text)
            if k and k not in seen_ar:
                seen_ar.add(k)
                forms_ar.append({"text": text, "key": k, "src": src})
        e["forms_ar"] = forms_ar
        e["gender"] = gender_cue(e)
    return ents


def gender_cue(e):
    f = m = False
    for form in e["forms"]:
        t = " " + fold(form["text"]) + " "
        if t.startswith(" umm ") or " bint " in t or " bt. " in t or re.search(r" (?:al|as|ar|an|at|az)-\w+iyya[h]? ", t):
            f = True
        elif " ibn " in t or " b. " in t or t.startswith(" abu "):
            m = True
    return "F" if f and not m else ("M" if m and not f else None)


# ---------------------------------------------------------------- Wikidata

def lit(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def fold_keep_apostrophe(s):
    s = "".join("'" if ch in "ʿʾ‘’`´ʻʼ'" else SPECIAL.get(ch, ch) for ch in s)
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower()


def spellings(text):
    """Further search spellings of one name form: apostrophes kept, final -ah/-a swapped, articles dropped,
    and the short 'X ibn Y' for long names (entity search matches prefixes only)."""
    base = re.sub(r"\bb\.\s+", "ibn ", fold_keep_apostrophe(text))
    base = " ".join(re.sub(r"[()\[\],;:]", " ", base).split())
    plain = base.replace("'", "")
    swap = lambda s: " ".join(w[:-1] if len(w) > 3 and w.endswith("ah") and not w.endswith("llah") else w  # noqa: E731
                              for w in s.split())
    out = [base, swap(base), swap(plain), " ".join(ARTICLE.sub("", swap(plain)).split())]
    words = plain.split()
    if words and words[-1].endswith("a") and not words[-1].endswith("ah"):
        out.append(" ".join(words[:-1] + [words[-1] + "h"]))
    if len(words) >= 4 and words[1] in ("ibn", "bint", "bin"):
        out.append(" ".join(words[:3]))
    if len(words) >= 3 and words[0] in ("umm", "abu"):
        out.append(" ".join(words[:2]))         # the kunya alone: Umm Salama
    return out


def search_terms(e):
    en, en2, text = [], [], []
    for form in e["forms"][:5]:
        a = re.sub(r"\bb\.\s+", "ibn ", fold(form["text"]))
        a = " ".join(re.sub(r"[()\[\],;:]", " ", a).split())
        for v in (a, " ".join(ARTICLE.sub("", a).split())):
            if v and v not in en:
                en.append(v)
        words = [w for w in re.split(r"[\s\-]+", ARTICLE.sub("", a)) if w and w not in CONNECT and w not in ("al", "the")]
        t = " ".join(words)
        if t and t not in text:
            text.append(t)
    for form in e["forms"][:4]:
        extra = spellings(form["text"])
        if e["kind"] == "place" and core(form["key"]) not in ("", form["key"]):
            extra.append(core(form["key"]))          # "hira" for Ghar Hira'
            first = form["key"].split()[0]
            if first in GEO_SEARCH:                  # "cave of hira": the generic noun in English, for search only
                extra.append(f"{GEO_SEARCH[first]} {core(form['key'])}")
        for v in extra:
            if v and v not in en[:6] and v not in en2:
                en2.append(v)
    ar = []
    for form in e["forms_ar"][:4]:
        for v in (form["text"], AR_MARKS.sub("", form["text"])):
            if v not in ar:
                ar.append(v)
    flt = " haswbstatement:P31=Q5" if e["kind"] == "person" else " haswbstatement:P625"
    return en[:6], ar[:4], [t + flt for t in text[:3]], en2[:8]


def search_queries(en, ar, text, en2=()):
    """One query per search service (MWAPI needs its input bound by a top-level VALUES). The further
    spellings (en2) go in a query of their own, so that adding them left the earlier queries' cache valid."""
    def q(api, terms, lang=None):
        if api == "EntitySearch":
            params = (f'wikibase:api "EntitySearch" ; mwapi:search ?term ; mwapi:language "{lang}" ; '
                      'mwapi:limit "10" .\n    ?item wikibase:apiOutputItem mwapi:item .')
        else:
            params = ('wikibase:api "Search" ; mwapi:srsearch ?term ; mwapi:srlimit "10" .\n'
                      '    ?item wikibase:apiOutputItem mwapi:title .')
        return (f'SELECT ?term ?item ?ord WHERE {{\n  VALUES ?term {{ {" ".join(lit(t) for t in terms)} }}\n'
                f'  SERVICE wikibase:mwapi {{\n    bd:serviceParam wikibase:endpoint "www.wikidata.org" ; '
                f'wikibase:limit "once" ; {params}\n    ?ord wikibase:apiOrdinal true .\n  }}\n}}')
    out = []
    if en:
        out.append(("en", q("EntitySearch", en, "en")))
    if ar:
        out.append(("ar", q("EntitySearch", ar, "ar")))
    if text:
        out.append(("text", q("Search", text)))
    if en2:
        out.append(("en", q("EntitySearch", list(en2), "en")))
    return out


def details_query(qids):
    langs = ", ".join(lit(x) for x in LABEL_LANGS + ("ar",))
    return f"""SELECT ?item ?f ?v ?lang ?prec WHERE {{
  VALUES ?item {{ {" ".join("wd:" + q for q in qids)} }}
  {{ ?item rdfs:label ?v . BIND("label" AS ?f) BIND(LANG(?v) AS ?lang) FILTER(LANG(?v) IN ({langs})) }}
  UNION {{ ?item skos:altLabel ?v . BIND("alias" AS ?f) BIND(LANG(?v) AS ?lang) FILTER(LANG(?v) IN ({langs})) }}
  UNION {{ ?item schema:description ?v . BIND("desc" AS ?f) BIND(LANG(?v) AS ?lang) FILTER(LANG(?v) IN ("en", "ar")) }}
  UNION {{ ?item wdt:P31 ?v . BIND("P31" AS ?f) }}
  UNION {{ ?item wdt:P21 ?v . BIND("P21" AS ?f) }}
  UNION {{ ?item p:P569 ?st . ?st psv:P569 ?n ; wikibase:rank ?r . FILTER(?r != wikibase:DeprecatedRank)
          ?n wikibase:timeValue ?v ; wikibase:timePrecision ?prec . BIND("P569" AS ?f) }}
  UNION {{ ?item p:P570 ?st . ?st psv:P570 ?n ; wikibase:rank ?r . FILTER(?r != wikibase:DeprecatedRank)
          ?n wikibase:timeValue ?v ; wikibase:timePrecision ?prec . BIND("P570" AS ?f) }}
  UNION {{ ?item p:P625 ?st . ?st psv:P625 ?n ; wikibase:rank ?r . FILTER(?r != wikibase:DeprecatedRank)
          ?n wikibase:geoLatitude ?lat ; wikibase:geoLongitude ?lon .
          BIND(CONCAT(STR(?lat), " ", STR(?lon)) AS ?v) BIND("P625" AS ?f) }}
  UNION {{ ?item wdt:P13870 ?v . BIND("P13870" AS ?f) }}
  UNION {{ VALUES ?kp {{ wdt:P22 wdt:P25 wdt:P26 wdt:P40 wdt:P3373 }} ?item ?kp ?v . BIND("kin" AS ?f) }}
}}"""


def qid(v):
    m = re.search(r"/entity/(Q\d+)$", v or "")
    return m.group(1) if m else None


def year_of(iso):
    m = re.match(r"([+-]?)(\d+)-", iso)
    if not m:
        return None
    y = int(m.group(2))
    return -y if m.group(1) == "-" else y


def parse_details(rows):
    out = {}
    for r in rows:
        q = qid(r.get("item"))
        if not q:
            continue
        d = out.setdefault(q, {"labels": [], "desc": {}, "P31": set(), "P21": set(), "birth": [], "death": [],
                               "coords": [], "openiti": set(), "kin": set()})
        f, v = r.get("f"), r.get("v", "")
        if f in ("label", "alias"):
            d["labels"].append((f, r.get("lang", ""), v))
        elif f == "desc":
            d["desc"][r.get("lang", "")] = v
        elif f in ("P31", "P21", "kin"):
            if qid(v):
                d[f].add(qid(v))
        elif f in ("P569", "P570"):
            y = year_of(v)
            if y is not None:
                d["birth" if f == "P569" else "death"].append((y, int(r.get("prec") or 0)))
        elif f == "P625":
            try:
                raw_lat, raw_lon = v.split()
                d["coords"].append((float(raw_lat), float(raw_lon), raw_lat, raw_lon))   # raw strings are kept as given
            except ValueError:
                pass
        elif f == "P13870":
            d["openiti"].add(v)
    for d in out.values():
        d["labels"] = sorted(set(d["labels"]))
        for k in ("birth", "death", "coords"):
            d[k] = sorted(set(d[k]))
    return out


def wd_label(d):
    by = {}
    for f, lang, v in d["labels"]:
        if f == "label":
            by.setdefault(lang, v)
    en = by.get("en") or by.get("mul") or next((by[x] for x in LABEL_LANGS if x in by), "")
    ar = by.get("ar", "")
    return " / ".join(x for x in (en, ar) if x)


def life_window(years_prec):
    """(earliest, latest) a dated value can mean, from its precision."""
    out = []
    for y, prec in years_prec:
        span = {11: 0, 10: 0, 9: 1, 8: 10, 7: 100, 6: 1000}.get(prec, 1000)
        out.append((y - span, y + span))
    return out


def dates_query(qids):
    return f"""SELECT ?item ?st ?prop ?v ?prec ?cal ?rank ?qp ?qpLabel ?qv ?qvLabel ?qt ?qprec ?qcal ?qamt ?qunitLabel WHERE {{
  VALUES ?item {{ {" ".join("wd:" + q for q in qids)} }}
  VALUES (?prop ?p ?psv) {{ ("birth" p:P569 psv:P569) ("death" p:P570 psv:P570) }}
  ?item ?p ?st . ?st ?psv ?n ; wikibase:rank ?rank . FILTER(?rank != wikibase:DeprecatedRank)
  ?n wikibase:timeValue ?v ; wikibase:timePrecision ?prec ; wikibase:timeCalendarModel ?cal .
  OPTIONAL {{
    ?qprop wikibase:qualifier ?pq ; wikibase:qualifierValue ?pqv .
    ?st ?pq ?qv .
    BIND(STRAFTER(STR(?qprop), "/entity/") AS ?qp)
    OPTIONAL {{ ?qprop rdfs:label ?qpLabel FILTER(LANG(?qpLabel) = "en") }}
    OPTIONAL {{ ?qv rdfs:label ?qvLabel FILTER(LANG(?qvLabel) = "en") }}
    OPTIONAL {{ ?st ?pqv ?qn . ?qn wikibase:timeValue ?qt ; wikibase:timePrecision ?qprec ; wikibase:timeCalendarModel ?qcal . }}
    OPTIONAL {{ ?st ?pqv ?qn2 . ?qn2 wikibase:quantityAmount ?qamt ; wikibase:quantityUnit ?qunit .
               OPTIONAL {{ ?qunit rdfs:label ?qunitLabel FILTER(LANG(?qunitLabel) = "en") }} }}
  }}
}}"""


PRECISION = {11: "day", 10: "month", 9: "year", 8: "decade", 7: "century", 6: "millennium"}
CALENDAR = {"Q1985727": "Gregorian", "Q1985786": "Julian"}


def entity_json(fx, q):
    """Wikidata's own record of an item (Special:EntityData), used only where the query service converts."""
    return json.loads(fx.text("wikidata-entity", f"https://www.wikidata.org/wiki/Special:EntityData/{q}.json?flavor=simple"))


def person_dates(fx, e, chosen):
    """Birth and death statements (not deprecated) of every Wikidata candidate of a person, exactly as given."""
    conf = {c["qid"]: cf for c, cf, _ in chosen}
    if not conf:
        return []
    stmts = {}
    for r in fx.sparql(dates_query(by_qid(conf))):
        q = qid(r.get("item"))
        st = r.get("st", "")
        if not q or not st:
            continue
        s = stmts.setdefault(st, {"qid": q, "prop": r["prop"], "v": r["v"], "prec": int(r.get("prec") or 0),
                                  "cal": qid(r.get("cal")) or r.get("cal", ""), "rank": r.get("rank", "").split("#")[-1],
                                  "quals": set()})
        if r.get("qp"):
            if r.get("qt"):
                val = (f"{r['qt']} ({PRECISION.get(int(r.get('qprec') or 0), r.get('qprec'))}, "
                       f"{CALENDAR.get(qid(r.get('qcal')) or '', r.get('qcal', ''))})")
            elif r.get("qamt"):
                val = f"{r['qamt']} {r.get('qunitLabel', '')}".strip()
            elif qid(r.get("qv")):
                val = f"{r.get('qvLabel', '')} ({qid(r['qv'])})".strip()
            else:
                val = r.get("qv", "")
            s["quals"].add(f"{r['qp']} {r.get('qpLabel', '')}: {val}")
    out = []
    for st in sorted(stmts, key=lambda k: (int(stmts[k]["qid"][1:]), stmts[k]["prop"], stmts[k]["v"], k)):
        # (the statement IRI, last in the key, carries Wikidata's statement GUID)
        s = stmts[st]
        value, note = s["v"], ""
        if s["cal"] == "Q1985786" and s["prec"] >= 10:
            # The query service gives day-precise Julian dates converted to the proleptic Gregorian calendar.
            # Take the value Wikidata itself stores, so that value and calendar model agree.
            guid = st.rsplit("/", 1)[-1]
            ent = entity_json(fx, s["qid"])["entities"]
            item = ent.get(s["qid"]) or next(iter(ent.values()))
            prop = "P569" if s["prop"] == "birth" else "P570"
            stored = next((c["mainsnak"].get("datavalue", {}).get("value", {}).get("time") for c in item["claims"].get(prop, [])
                           if c.get("id", "").replace("$", "-").lower() == guid.lower()), None)
            if stored and stored.lstrip("+")[:10] != value[:10]:
                note = (f"value as stored on Wikidata (Julian); the query service gives it converted to the "
                        f"proleptic Gregorian calendar as {value}")
                value = stored
        out.append([e["id"], s["qid"], s["prop"], value, PRECISION.get(s["prec"], str(s["prec"])),
                    CALENDAR.get(s["cal"], s["cal"]), conf[s["qid"]], "proposed", f"Wikidata {s['qid']}",
                    {"PreferredRank": "preferred", "NormalRank": "normal"}.get(s["rank"], s["rank"]),
                    " | ".join(sorted(s["quals"])), note])
    return out


def search_hits(fx, e):
    hits = {}
    for mode, query in search_queries(*search_terms(e)):
        for r in fx.sparql(query):
            q = qid(r.get("item"))
            if q:
                hits.setdefault(q, []).append((mode, int(float(r.get("ord") or 99))))
    return hits


def by_qid(qids):
    return sorted(qids, key=lambda q: int(q[1:]))


def wikidata_candidates(fx, e):
    hits = search_hits(fx, e)
    if not hits:
        return {}, {}
    return hits, parse_details(fx.sparql(details_query(by_qid(hits))))


# ---------------------------------------------------------------- scoring: people

def person_scores(e, hits, details):
    """Score every human candidate; returns a list of dicts sorted best first."""
    out = []
    for q in sorted(details, key=lambda x: int(x[1:])):
        d = details[q]
        if "Q5" not in d["P31"]:
            continue
        ev = []
        # name
        best = (-1, 0, None, None)
        for form in e["forms"]:
            for f, lang, v in d["labels"]:
                if lang not in LABEL_LANGS:
                    continue
                lvl = name_level(form["key"], name_key(v))
                cand = (lvl, form["n"] if lvl >= 4 else min(form["n"], len(name_key(v).split())), form, (f, lang, v))
                if cand[:2] > best[:2]:
                    best = cand
        lvl, spec, form, lab = best
        if lvl < 0:
            continue
        # how many of our distinct name forms this item matches (equal, extended or loosely equal)
        matched = [f["text"] for f in e["forms"]
                   if any(name_level(f["key"], name_key(v)) >= 3 for _, lang, v in d["labels"] if lang in LABEL_LANGS)]
        # period, contradictions
        births, deaths = life_window(d["birth"]), life_window(d["death"])
        windows = births + deaths
        if (births and all(lo > 850 for lo, _ in births)) or \
                (deaths and all(lo > PERIOD[1] or hi < PERIOD[0] for lo, hi in deaths)):
            continue
        if seerah_person(e) and not seerah_life(d):
            continue
        gender = "M" if MALE in d["P21"] else ("F" if FEMALE in d["P21"] else None)
        if e["gender"] and gender and e["gender"] != gender:
            continue
        in_period = any(PERIOD[0] <= lo and hi <= PERIOD[1] + 1 for lo, hi in windows if hi - lo <= 20)
        desc = d["desc"].get("en", "")
        cue = bool(PERIOD_CUE.search(desc))
        if not in_period and not cue and MODERN_CUE.search(desc):
            continue
        dates = None
        if e["death"] and d["death"]:
            lo, hi = e["death"]
            precise = [y for y, p in d["death"] if p >= 9]
            if precise:
                dates = "agree" if any(lo - 2 <= y <= hi + 2 for y in precise) else (
                    "disagree" if all(abs(y - lo) > 5 and abs(y - hi) > 5 for y in precise) else None)
        ev.append(f'name: ours "{form["text"]}" ({form["src"]}) {LEVEL_WORD[lvl]} {lab[1]} {lab[0]} "{lab[2]}"')
        others = [t for t in matched if t != form["text"]]
        if others:
            ev.append("also matches our name form" + ("s " if len(others) > 1 else " ") +
                      ", ".join(f'"{t}"' for t in others))
        if dates == "agree":
            ev.append(f"dates: died {fmt_years(d['death'])} (Wikidata) within our death date {e['death'][0]}-{e['death'][1]}")
        elif dates == "disagree":
            ev.append(f"dates DISAGREE: died {fmt_years(d['death'])} (Wikidata) vs ours {e['death'][0]}-{e['death'][1]}")
        elif in_period:
            ev.append("dates: " + "; ".join(x for x in (
                f"born {fmt_years(d['birth'])}" if d["birth"] else "", f"died {fmt_years(d['death'])}" if d["death"] else "")
                if x) + " (Wikidata), in the period")
        if desc:
            ev.append(f'description: "{desc}"' + (f" (our tabaqa: {e['tabaqa'].replace('tb_', '')})" if e["tabaqa"] and cue else ""))
        if gender and e["gender"]:
            ev.append(f"gender: {'female' if gender == 'F' else 'male'} as our name form implies")
        out.append({"qid": q, "level": lvl, "spec": spec, "nforms": len(matched), "in_period": in_period, "cue": cue,
                    "dates": dates,
                    "kin": None, "ev": ev, "label": wd_label(d), "ord": min(o for _, o in hits.get(q, [("", 99)])),
                    "details": d})
    return out


def seerah_person(e):
    return e["at_event"] or e["tabaqa"] == "tb_sahabi"


def seerah_life(d):
    """False when the item's dated life cannot include the Prophet's lifetime (see SEERAH_LIFE)."""
    born_by, died_from, died_by = SEERAH_LIFE
    births = [(lo, hi) for lo, hi in life_window(d["birth"]) if hi - lo <= 20]
    deaths = [(lo, hi) for lo, hi in life_window(d["death"]) if hi - lo <= 20]
    if births and all(lo > born_by for lo, _ in births):
        return False
    if deaths and all(lo > died_by or hi < died_from for lo, hi in deaths):
        return False
    return True


LEVEL_WORD = {5: "equals", 4: "extends/is extended by", 3: "loosely equals", 2: "loosely extends",
              1: "agrees in part with", 0: "shares words with"}


def fmt_years(yp):
    return "/".join(f"{y}" + ("" if p >= 9 else ("s" if p == 8 else " (century)")) for y, p in yp)


def classify_person(c):
    corroborated = c["dates"] == "agree" or c["kin"] or (c["in_period"] and c["cue"])
    if c["dates"] == "disagree":
        return "needs-review"
    if c["level"] == 5 and (c["spec"] >= 3 or c["dates"] == "agree" or c["kin"]) and corroborated:
        return "exact"
    if c["level"] >= 3 and (c["in_period"] or c["cue"] or c["kin"] or c["dates"] == "agree"):
        if c["level"] >= 4 or c["spec"] >= 3 or c["kin"] or c["dates"] == "agree":
            return "probable"
    return "needs-review"


def choose(cands, classify, key, tie_key, homonym, plausible, strong, cap=6):
    """Rank candidates. The best gets its own class unless another is equally supported on every count
    (tie_key): then all of them are needs-review. Homonyms of a strong best match, and plausible weaker
    candidates when the best is weak, are listed as needs-review. Returns [(candidate, confidence, note)]."""
    if not cands:
        return []
    cands = sorted(cands, key=key)
    top = cands[0]
    ties = [c for c in cands if tie_key(c) == tie_key(top)]
    if len(ties) > 1 and top["level"] >= strong:
        rows = [(c, "needs-review", f"tie: {len(ties)} candidates are equally supported") for c in ties]
    else:
        ties = [top]
        rows = [(top, classify(top), "")]
    taken = {id(c) for c in ties}
    for c in cands:
        if id(c) in taken or len(rows) >= cap:
            continue
        if homonym(c) or (top["level"] < strong and plausible(c)):
            rows.append((c, "needs-review", ""))
    return rows


def evidence(c, note):
    return "; ".join(c["ev"] + ([note] if note else []))


PERSON_KEY = lambda c: (-c["level"], -c["spec"], -c["nforms"], c["dates"] != "agree", not c["kin"],   # noqa: E731
                        not (c["in_period"] and c["cue"]), not c["in_period"], c["ord"], int(c["qid"][1:]))
PERSON_TIE = lambda c: (c["level"], c["spec"], c["nforms"], c["dates"] == "agree", bool(c["kin"]),    # noqa: E731
                        c["in_period"] and c["cue"], c["in_period"])
PERSON_HOMONYM = lambda c: c["level"] >= 3 and c["spec"] >= 2                                # noqa: E731
PERSON_PLAUSIBLE = lambda c: c["level"] >= 1 and (c["in_period"] or c["cue"] or c["kin"])    # noqa: E731


def choose_person(cands):
    return choose(cands, classify_person, PERSON_KEY, PERSON_TIE, PERSON_HOMONYM, PERSON_PLAUSIBLE, strong=3)


def choose_place(cands):
    return choose(cands, classify_place, place_key, lambda c: (c["level"], c["spec"], c.get("admin", False)),
                  lambda c: c["level"] >= 5, lambda c: c["level"] >= 1, strong=5)


# ---------------------------------------------------------------- scoring: places

def core(k):
    """A place key without generic geographic words (ghar, jabal, wadi, mount, cave of ...)."""
    return " ".join(t for t in k.split() if t not in GEO_GENERIC)


def place_level(ok, ck, cand_kinds=frozenset()):
    """name_level, plus: equal core names count as loosely equal (Ghar Thawr / Cave of Thawr) when the
    candidate is of the kind our generic word names (a cave for ghar, a mountain for jabal, ...)."""
    lvl = name_level(ok, ck)
    if lvl < 3 and core(ok) and core(ok) == core(ck) and kinds(ok) <= (kinds(ck) | set(cand_kinds)):
        return 3
    return lvl


def place_wd_scores(e, hits, details):
    out = []
    for q in sorted(details, key=lambda x: int(x[1:])):
        d = details[q]
        desc = d["desc"].get("en", "")
        # a place candidate needs coordinates; events, people, lists and (unless our place is a structure)
        # buildings and infrastructure are left out
        if d["P31"] & NOT_A_PLACE or EVENT_CUE.search(desc) or not d["coords"]:
            continue
        if BUILDING_CUE.search(desc) and e["ptype"] not in ("pt_structure", "pt_cemetery"):
            continue
        best = (-1, None, None)
        for form in e["forms"]:
            for f, lang, v in d["labels"]:
                if lang in LABEL_LANGS:
                    lvl = place_level(form["key"], name_key(v), kinds(desc))
                    if lvl > best[0]:
                        best = (lvl, form, (f, lang, v))
        ar_best = (-1, None, None)
        for form in e["forms_ar"]:
            for f, lang, v in d["labels"]:
                if lang == "ar":
                    k = ar_key(v)
                    lvl = 5 if k == form["key"] else (3 if ar_loose(k) == ar_loose(form["key"]) else -1)
                    if lvl > ar_best[0]:
                        ar_best = (lvl, form, (f, lang, v))
        lvl = max(best[0], ar_best[0])
        if lvl < 1:
            continue
        ev = []
        if best[0] >= 0:
            ev.append(f'name: ours "{best[1]["text"]}" {LEVEL_WORD[best[0]]} {best[2][1]} {best[2][0]} "{best[2][2]}"')
        if ar_best[0] >= 0:
            ev.append(f'Arabic name: ours "{ar_best[1]["text"]}" {LEVEL_WORD[ar_best[0]]} ar {ar_best[2][0]} "{ar_best[2][2]}"')
        if desc:
            ev.append(f'description: "{desc}"')
        dist = min((haversine(p, c) for p in e["points"] for c in d["coords"]), default=None)
        region = bool(REGION_CUE.search(desc))
        out.append({"qid": q, "level": lvl, "en_level": best[0], "ar_level": ar_best[0], "dist": dist,
                    "region": region, "admin": bool(ADMIN_CUE.search(desc)), "coords": d["coords"], "ev": ev,
                    "label": wd_label(d), "agree": None, "agree_ok": False,
                    "ord": min(o for _, o in hits.get(q, [("", 99)])), "spec": 0})
    return out


def classify_place(c):
    if c["level"] >= 5 and c["spec"] == 2:
        return "exact"
    if c["level"] >= 5 and c["spec"] == 1:
        return "probable"
    return "needs-review"


def place_spec(c, unique):
    """How strongly the location backs the name: 2 within 15 km of our point, 1 within 50 km, -1 more than
    100 km away. Without a point of ours: 1 when the cross-check counts (see cross_check), or when the name is
    unique in its gazetteer and both its English and Arabic names equal ours; else 0. A modern administrative
    unit named after the place is never more than 1."""
    if c["dist"] is not None:
        if c["dist"] > 100 and not c["region"]:
            return -1
        s = 2 if c["dist"] <= 15 else (1 if c["dist"] <= 50 else 0)
    else:
        s = 1 if c["agree_ok"] or (unique and c["en_level"] >= 5 and c["ar_level"] >= 5) else 0
    return min(s, 1) if c.get("admin") else s


def place_key(c):
    return (-c["level"], -c["spec"], c.get("admin", False), c["dist"] if c["dist"] is not None else 1e9, c["ord"],
            c.get("qid") or c.get("uri"))


def dist_note(c, ours):
    if c["dist"] is None:
        return
    word = "within" if c["dist"] <= 15 else "from"
    c["ev"].append(f"location: {c['dist']:.1f} km {word} the corpus's own point (proposed geometry{', ' + ours if ours else ''})")


# ---------------------------------------------------------------- al-Thurayya

def thurayya_index(fx):
    feats = json.loads(fx.text("althurayya", THURAYYA_URL))["features"]
    out = []
    for f in feats:
        c = f.get("properties", {}).get("cornuData", {})
        uri = c.get("cornu_URI")
        if not uri:
            continue
        ar = [c.get("toponym_arabic", "")] + re.split(r"[،,]", c.get("toponym_arabic_other", ""))
        la = [c.get("toponym_translit", ""), c.get("toponym_search", "")] + \
            re.split(r",", c.get("toponym_translit_other", "")) + re.split(r",", c.get("toponym_search", ""))
        try:
            pt = (float(c["coord_lat"]), float(c["coord_lon"]), c["coord_lat"], c["coord_lon"])
        except (KeyError, ValueError):
            pt = None
        out.append({"uri": uri, "ar": sorted({ar_key(x) for x in ar if ar_key(x)}),
                    "la": sorted({name_key(x) for x in la if name_key(x)}),
                    "label": " / ".join(x for x in (c.get("toponym_translit", ""), c.get("toponym_arabic", "")) if x),
                    "point": pt, "certainty": c.get("coord_certainty", ""), "type": c.get("top_type_hom", ""),
                    "region": c.get("top_type_hom") == "regions"})
    return sorted(out, key=lambda x: x["uri"])


def thurayya_scores(e, index):
    out = []
    for t in index:
        lvl_la = max((lv if (lv := place_level(f["key"], k)) in (5, 3) else -1
                      for f in e["forms"] for k in t["la"]), default=-1)
        lvl_ar = max(((5 if f["key"] == k else (3 if ar_loose(f["key"]) == ar_loose(k) else -1))
                      for f in e["forms_ar"] for k in t["ar"]), default=-1)
        lvl = max(lvl_la, lvl_ar)
        if lvl < 3:
            continue
        ev = []
        if lvl_ar >= 0:
            ev.append(f"Arabic name: {LEVEL_WORD[lvl_ar]} toponym_arabic ({', '.join(f['text'] for f in e['forms_ar'][:2])})")
        if lvl_la >= 0:
            ev.append(f"name: {LEVEL_WORD[lvl_la]} transliteration \"{t['label'].split(' / ')[0]}\"")
        ev.append(f"type: {t['type']}; coordinates {t['certainty'] or 'unrated'} in the gazetteer")
        dist = min((haversine(p, t["point"]) for p in e["points"]), default=None) if t["point"] else None
        out.append({"uri": t["uri"], "level": lvl, "en_level": lvl_la, "ar_level": lvl_ar, "dist": dist,
                    "region": t["region"], "admin": False, "coords": [t["point"]] if t["point"] else [], "ev": ev,
                    "label": t["label"], "agree": None, "agree_ok": False, "ord": 0, "spec": 0})
    return out


def cross_check(wd, th):
    """The gazetteers agree when same-name candidates from both lie close together (regions: 300 km). That
    shows the two records are one place, not that it is ours. It counts (agree_ok) only when al-Thurayya,
    a gazetteer of the classical Islamic world, has exactly one entry with the name: then that entry is the
    classical place of that name, and the Wikidata item beside it is the same place."""
    for a in wd:
        for b in th:
            if a["level"] >= 5 and b["level"] >= 5 and a["coords"] and b["coords"]:
                dist = min(haversine(p, q) for p in a["coords"] for q in b["coords"])
                limit = 300 if (a["region"] or b["region"]) else 30
                if dist <= limit:
                    a["agree"] = a["agree"] or (b["uri"], dist)
                    b["agree"] = b["agree"] or (a["qid"], dist)
    unique = sum(1 for c in th if c["level"] >= 5) == 1
    for c in wd + th:
        c["agree_ok"] = bool(c["agree"]) and unique
        if c["agree"]:
            other = "al-Thurayya" if "qid" in c else "Wikidata"
            c["ev"].append(f"cross-check: {other} {c['agree'][0]} (same name) lies {c['agree'][1]:.0f} km away" +
                           ("" if unique else " (al-Thurayya has several entries with this name, so this does not "
                                              "identify our place)"))


# ---------------------------------------------------------------- OpenITI

def openiti_authors(fx):
    meta = json.loads(fx.text("openiti", OPENITI_AUTHORS_URL))
    out = {}
    for uri in sorted(meta):
        m = meta[uri]
        # OpenITI URI-style names (plain ASCII, e.g. "Abu Talib Cabd Manaf") spell ʿayn as C/c
        uri_style = lambda n: n.replace("C", "").replace("c", "") if n.isascii() else n   # noqa: E731
        names = [uri_style(n) for n in (m.get("author_lat") or [])]
        if m.get("shuhra"):
            names.append(m["shuhra"])
        if m.get("full_name"):
            names.append(m["full_name"])
        names.append(uri_style(m.get("author_name_from_uri") or ""))
        la = (m.get("name_elements") or {}).get("LA") or {}
        if la.get("ism") and la.get("nasab"):
            names.append(f"{la['ism']} {la['nasab']}")
        wd = re.findall(r"wikidata@(Q\d+)", m.get("external_id") or "")
        try:
            date = int(m.get("date") or "")
        except ValueError:
            date = None
        ar_names = sorted(m.get("author_ar") or [], key=lambda n: (len(n), n))
        out[uri] = {"uri": uri, "keys": sorted({name_key(n) for n in names if name_key(n)}),
                    "label": " / ".join(x for x in ((m.get("author_lat") or [""])[0], (ar_names or [""])[0]) if x),
                    "wd": wd, "date": date, "books": sorted(m.get("books") or [])}
    return out


def openiti_for_person(e, wd_rows, authors, by_wd):
    """wd_rows: [(candidate, confidence)] for this person from Wikidata."""
    found = {}
    for c, conf, _ in wd_rows:
        if conf == "needs-review":          # a homonym or tie: following it would only add noise
            continue
        q = c["qid"]
        forward = sorted(c["details"]["openiti"])
        back = sorted(by_wd.get(q, []))
        for uri in sorted(set(forward) | set(back)):
            if uri not in authors:
                continue
            both = uri in forward and uri in back
            how = ("both directions: Wikidata P13870 and OpenITI's wikidata@ link" if both else
                   ("Wikidata P13870 only" if uri in forward else "OpenITI's wikidata@ link only"))
            level = conf if (both or conf != "exact") else "probable"
            ev = [f"via Wikidata {q} ({conf}): {how}"]
            prev = found.get(uri)
            if prev is None or CONF_RANK[level] < CONF_RANK[prev[0]]:
                found[uri] = (level, ev)
    for uri in sorted(authors):
        a = authors[uri]
        if a["date"] is None or a["date"] > 400 or (seerah_person(e) and ah_to_ce(a["date"]) > SEERAH_LIFE[2]):
            continue
        lvl = max((name_level(f["key"], k) for f in e["forms"] for k in a["keys"]), default=-1)
        if lvl < 5 or not any(f["n"] >= 2 for f in e["forms"] if f["key"] in a["keys"]):
            continue
        ev = [f"name: an OpenITI author name equals ours; died {a['date']} AH (~{ah_to_ce(a['date'])} CE)"]
        level = "needs-review"
        if e["death"]:
            ce = ah_to_ce(a["date"])
            if e["death"][0] - 3 <= ce <= e["death"][1] + 3:
                ev.append(f"dates: agree with our death date {e['death'][0]}-{e['death'][1]}")
                level = "probable"
        if uri in found:
            lv0, ev0 = found[uri]
            found[uri] = (lv0, ev0 + ev)
        else:
            found[uri] = (level, ev)
    exact = [u for u, (lv, _) in found.items() if lv == "exact"]
    if len(exact) > 1:
        for u in exact:
            found[u] = ("needs-review", found[u][1] + [f"tie: {len(exact)} OpenITI URIs qualify"])
    return [(uri, lv, ev, authors[uri]["label"]) for uri, (lv, ev) in sorted(found.items())]


def openiti_for_work(e, fx, authors, person_openiti):
    rows = list(csv.DictReader(io.StringIO(fx.text("openiti", OPENITI_BOOKS_URL)), delimiter="\t"))
    titles = {}
    for r in rows:
        book = r.get("book", "")
        for t in (r.get("title_lat", "").split("::") + [re.sub(r"(?<=[a-z])(?=[A-Z])", " ", book.split(".")[-1])]):
            k = name_key(t)
            if k:
                titles.setdefault(book, set()).add(k)
    found = {}
    creators = [u for p in e["creators"] for u, lv, _, _ in person_openiti.get(p, []) if lv != "needs-review"]
    for book in sorted(titles):
        lvl = max((name_level(f["key"], k) for f in e["forms"] for k in titles[book]), default=-1)
        author = book.split(".")[0]
        if lvl >= 5:
            found[book] = ("needs-review", [f"title: equals an OpenITI title of {book}"])
        elif author in creators and lvl >= 0:
            found[book] = ("needs-review", [f"author: {author} is the OpenITI candidate of the work's creator; title shares words"])
    if len(found) == 1:
        b = next(iter(found))
        if found[b][1][0].startswith("title"):
            found[b] = ("probable", found[b][1])
    return [(b, lv, ev, b) for b, (lv, ev) in sorted(found.items())]


# ---------------------------------------------------------------- main

def run(fx, report=False):
    ents = load_entities()
    rows, coords, dates, notes = [], [], [], {"ties": [], "contradictions": [], "uncovered": []}
    authors = openiti_authors(fx)
    by_wd = {}
    for uri, a in authors.items():
        for q in a["wd"]:
            by_wd.setdefault(q, []).append(uri)
    index = None
    person_wd = {}

    people = [e for e in sorted(ents.values(), key=lambda x: x["id"]) if e["kind"] == "person"]
    places = [e for e in sorted(ents.values(), key=lambda x: x["id"]) if e["kind"] == "place"]
    works = [e for e in sorted(ents.values(), key=lambda x: x["id"]) if e["kind"] == "work"]

    # Wikidata requests first, in parallel (results go to the cache); everything below then reads the cache
    live = people + [e for e in places if not e["placeholder"]]
    fx.prefetch([q for e in live for _, q in search_queries(*search_terms(e))], "search")
    if not fx.offline:
        fx.prefetch([details_query(by_qid(h)) for e in live for h in [search_hits(fx, e)] if h], "details")

    # people: Wikidata, two passes (the second adds family-link agreement)
    scored = {}
    for e in people:
        hits, details = wikidata_candidates(fx, e)
        scored[e["id"]] = person_scores(e, hits, details)
    first = {}
    for e in people:
        chosen = choose_person(scored[e["id"]])
        if chosen and chosen[0][1] in ("exact", "probable"):
            first[e["id"]] = chosen[0][0]["qid"]
    for e in people:
        for c in scored[e["id"]]:
            for kin_id, relname in sorted(e["kin"].items()):
                kq = first.get(kin_id)
                if kq and kq in c["details"]["kin"]:
                    c["kin"] = (kin_id, relname, kq)
                    c["ev"].append(f"family: our {relname} {kin_id} is matched to {kq}, which this item names as family")
                    break
        person_wd[e["id"]] = choose_person(scored[e["id"]])
    fx.prefetch([dates_query(by_qid({c["qid"] for c, _, _ in ch})) for ch in person_wd.values() if ch], "dates")
    for e in people:
        chosen = person_wd[e["id"]]
        ties = [c for c, conf, note in chosen if note]
        if ties:
            notes["ties"].append(f"{e['id']} {e['forms'][0]['text'] if e['forms'] else ''}: " +
                                 ", ".join(f"{c['qid']} {c['label']}" for c in ties))
        for c, conf, note in chosen:
            if c["dates"] == "disagree":
                notes["contradictions"].append(f"{e['id']} {c['qid']}: death dates disagree")
            rows.append([e["id"], "person", "wikidata", c["qid"], c["label"], evidence(c, note), conf, "proposed"])
        dates.extend(person_dates(fx, e, chosen))

    # people: OpenITI
    person_openiti = {}
    for e in people:
        found = openiti_for_person(e, person_wd[e["id"]], authors, by_wd)
        person_openiti[e["id"]] = found
        for uri, conf, ev, label in found:
            rows.append([e["id"], "person", "openiti", uri, label, "; ".join(ev), conf, "proposed"])

    # places: Wikidata and al-Thurayya
    for e in places:
        if e["placeholder"]:
            notes["uncovered"].append(f"{e['id']} {e['forms'][0]['text'] if e['forms'] else ''}: placeholder, not searched")
            continue
        if index is None:
            index = thurayya_index(fx)
        hits, details = wikidata_candidates(fx, e)
        wd = place_wd_scores(e, hits, details)
        th = thurayya_scores(e, index)
        cross_check(wd, th)
        ours = ", ".join(f"{la:.4f} {lo:.4f}" for la, lo in e["points"])
        for system, cands in (("wikidata", wd), ("althurayya", th)):
            unique = sum(1 for c in cands if c["level"] >= 5) == 1
            for c in cands:
                dist_note(c, ours)
                c["spec"] = place_spec(c, unique)
            for c in cands:                  # more than 100 km from our own point: ruled out, not ambiguous
                if c["spec"] < 0 and c["level"] >= 5:
                    notes["contradictions"].append(f"{e['id']} {system} {c.get('qid') or c.get('uri')} {c['label']}: "
                                                   f"{c['dist']:.0f} km from our point, left out")
            chosen = choose_place([c for c in cands if c["spec"] >= 0])
            ties = [c for c, conf, note in chosen if note]
            if ties:
                notes["ties"].append(f"{e['id']} {e['forms'][0]['text']} ({system}): " +
                                     ", ".join(f"{c.get('qid') or c.get('uri')} {c['label']}" for c in ties))
            for c, conf, note in chosen:
                ext = c.get("qid") or c.get("uri")
                rows.append([e["id"], "place", system, ext, c["label"], evidence(c, note), conf, "proposed"])
                src = f"Wikidata {ext} P625" if system == "wikidata" else f"{THURAYYA_SOURCE}, {ext}"
                for la, lo, raw_la, raw_lo in c["coords"]:
                    d = min((haversine(p, (la, lo)) for p in e["points"]), default=None)
                    coords.append([e["id"], system, ext, raw_la, raw_lo, src, "" if d is None else f"{d:.1f}",
                                   conf, "proposed"])

    # works: OpenITI
    for e in works:
        for book, conf, ev, label in openiti_for_work(e, fx, authors, person_openiti):
            rows.append([e["id"], "work", "openiti", book, label, "; ".join(ev), conf, "proposed"])

    kind_rank = {k: i for i, k in enumerate(KINDS)}
    sys_rank = {s: i for i, s in enumerate(SYSTEMS)}
    rows.sort(key=lambda r: (kind_rank[r[1]], r[0], sys_rank[r[2]], CONF_RANK[r[6]], r[3]))
    coords.sort(key=lambda r: (r[0], sys_rank[r[1]], r[2], r[3], r[4]))
    for e in people + places + works:
        if not any(r[0] == e["id"] for r in rows) and not e["placeholder"]:
            notes["uncovered"].append(f"{e['id']} {e['forms'][0]['text'] if e['forms'] else ''}")
    dates.sort(key=lambda r: (r[0], CONF_RANK[r[6]], int(r[1][1:]), r[2], r[3], r[10]))
    return ents, rows, coords, dates, notes


ID_HEADER = ["canonical_id", "kind", "system", "external_id", "external_label", "evidence", "confidence", "status"]
COORD_HEADER = ["canonical_id", "system", "external_id", "latitude", "longitude", "coordinate_source",
                "distance_km_to_corpus_point", "link_confidence", "status"]
DATE_HEADER = ["canonical_id", "external_id", "property", "value", "precision", "calendar_model", "match_confidence",
               "status", "source", "rank", "qualifiers", "note"]
OUT_DATES = ONT / "corpus" / "external-dates.csv"


def to_csv(header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def coverage(ents, rows):
    lines = []
    for kind in KINDS:
        es = [e for e in ents.values() if e["kind"] == kind]
        if not es:
            continue
        best = {}
        for r in rows:
            if r[1] == kind:
                best[r[0]] = min(best.get(r[0], 9), CONF_RANK[r[6]])
        n = len(es)
        got = len(best)
        dist = {c: sum(1 for v in best.values() if v == rank) for c, rank in CONF_RANK.items()}
        lines.append(f"{kind}s: {got}/{n} have a candidate ({100 * got / n:.1f}%); best confidence: " +
                     ", ".join(f"{c} {dist[c]}" for c in CONF_RANK))
        for s in SYSTEMS:
            per = {}
            for r in rows:
                if r[1] == kind and r[2] == s:
                    per[r[0]] = min(per.get(r[0], 9), CONF_RANK[r[6]])
            if per:
                d2 = {c: sum(1 for v in per.values() if v == rank) for c, rank in CONF_RANK.items()}
                lines.append(f"  {s}: {len(per)}/{n} entities, {sum(1 for r in rows if r[1] == kind and r[2] == s)} rows; "
                             "best: " + ", ".join(f"{c} {d2[c]}" for c in CONF_RANK))
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--offline", action="store_true", help="use the cache only; a cache miss is an error")
    ap.add_argument("--check", action="store_true", help="offline; exit 1 if the CSVs on disk differ from a fresh run")
    ap.add_argument("--report", action="store_true", help="also list ties, contradictions and entities without a candidate")
    args = ap.parse_args()
    fx = Fetcher(offline=args.offline or args.check)
    try:
        ents, rows, coords, dates, notes = run(fx, args.report)
    except CacheMiss as e:
        print(f"error: not in the cache (run without --offline/--check to fetch): {e}", file=sys.stderr)
        return 2
    outputs = [(OUT_IDS, to_csv(ID_HEADER, [r for r in rows if r[2] != "althurayya"])),
               (OUT_IDS_TH, to_csv(ID_HEADER, [r for r in rows if r[2] == "althurayya"])),
               (OUT_COORDS, to_csv(COORD_HEADER, coords)),
               (OUT_DATES, to_csv(DATE_HEADER, dates))]
    if args.check:
        stale = [p.name for p, text in outputs if not p.exists() or p.read_text(encoding="utf-8") != text]
        print("up to date" if not stale else f"differs: {', '.join(stale)}; re-run {Path(__file__).name} and commit")
        return 1 if stale else 0
    for p, text in outputs:
        p.write_text(text, encoding="utf-8")
    print(f"wrote external-ids.csv ({len(rows)} rows), external-coordinates.csv ({len(coords)}), "
          f"external-dates.csv ({len(dates)}); requests: {fx.fetched} fetched, {fx.hits} from cache")
    for line in coverage(ents, rows):
        print(line)
    if args.report:
        for k in ("ties", "contradictions", "uncovered"):
            print(f"\n{k} ({len(notes[k])}):")
            for n in notes[k]:
                print("  " + n)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"error: {e}", file=sys.stderr)
        raise
