"""Name rules in one place: how a name is shown, and how it is found.

Display, the popular transliteration (maintainer answers round 1; slice-2 brief):
    popular("Abū Bakr al-Ṣiddīq") == "Abu Bakr as-Siddiq"
Search, lookup that tolerates spelling (slice-2 brief, part 2b; docs/05 section 3):
    normalise("Abū Bakr al-Ṣiddīq") == "abu bakr siddiq"   the search form
    skeleton("abu bakr siddiq") == "bkrsdk"                its sound key
    search(items, query)                                   ranked matches, see TIERS

The sound key keeps only consonants, in classes (s for s, th, ص, ث ...). It lets a
query in Arabic script find a name the graph records only in Latin letters, and lets
"Usman" find "Uthman". It is a search aid: it is never shown, and a match on it is
listed as a similar spelling, not as a recorded name.

The browser port is site/static/search.js. It repeats the steps below but holds no
table: every table it uses is RULES, which site/build.py writes into search.json.
Display and search share the tables (ayn and hamza marks, sun letters, the article,
b. for ibn), so a change here changes both. site/tests/test_search.py runs the
Python and the JavaScript on the same cases (site/tests/search_cases.json) and fails
on any difference. Nothing here reads the graph.
"""
from __future__ import annotations

import re
import unicodedata

# --------------------------------------------------------------------------
# Shared tables
# --------------------------------------------------------------------------
AYN_HAMZA = "\u02bf\u02be\u02bb\u02bc"     # ʿ ʾ ʻ ʼ: the marks of a scholarly spelling
APOSTROPHES = "\u2018\u2019`"              # ‘ ’ and the backtick
# The article al- assimilates before these (written th sh dh t d r z s n; ṣ ḍ ṭ ẓ fold
# to s d t z). Before l it is unchanged (al-Layth), as before a moon letter (al-Madina).
SUN_LETTERS = ("th", "sh", "dh", "t", "d", "r", "z", "s", "n")
IBN = "ibn"                                # what "b." stands for in a nasab

# --------------------------------------------------------------------------
# Display: popular transliteration
# --------------------------------------------------------------------------
# The maintainer: use the popular form when the recorded name is already in it,
# otherwise derive it mechanically from the scholarly form. A label with no scholarly
# mark (no diacritic, no ʿ ʾ) counts as popular. Rules, in order (tests/test_display.py):
#   a. A leading ayn or hamza mark at the start of a word is dropped (scholarly labels):
#      ʿUmar -> Umar, ʿAbd al-Raḥmān -> Abd ar-Rahman.
#   b. Every other ayn / hamza / curly apostrophe becomes a plain apostrophe
#      (scholarly labels): Saʿd -> Sa'd, Āʾisha -> A'isha.
#   c. Diacritics are stripped (scholarly labels): Ṣiddīq -> Siddiq.
#   d. Every label, popular ones included: the article al- is assimilated before a sun
#      letter: al-Ṣiddīq -> as-Siddiq, Anas ibn al-Nadr -> Anas ibn an-Nadr.
#   e. Only if expand_b (display.EXPAND_B_TO_IBN, off until the maintainer rules):
#      b. -> ibn.
_LEADING_MARKS = re.compile(f"(?<![^\\W_])[{AYN_HAMZA}]+")
_SCHOLARLY_MARKS = re.compile(f"[{AYN_HAMZA}]")
_FOLD_TO_APOSTROPHE = AYN_HAMZA + APOSTROPHES
_SUN_ARTICLE = re.compile(r"\b([Aa])l-(" + "|".join(SUN_LETTERS) + ")", re.IGNORECASE)
_B_ABBREV = re.compile(r"\bb\.(?=\s)")


def fold_with_map(text: str) -> tuple[str, list[int]]:
    """Strip diacritics and unify apostrophes. Returns (folded, index_map) where
    index_map[i] is the index in `text` of folded[i]. Used to find terms in text
    that carries diacritics and wrap the original characters."""
    text = unicodedata.normalize("NFC", text)
    out: list[str] = []
    idx: list[int] = []
    for i, ch in enumerate(text):
        if ch in _FOLD_TO_APOSTROPHE:
            out.append("'")
            idx.append(i)
            continue
        base = "".join(c for c in unicodedata.normalize("NFD", ch) if not unicodedata.combining(c))
        for c in base:
            out.append(c)
            idx.append(i)
    return "".join(out), idx


def fold(text: str) -> str:
    return fold_with_map(text)[0]


def has_scholarly_marks(text: str) -> bool:
    """True if the text is written in a scholarly scheme (a diacritic or an ayn/hamza mark)."""
    if _SCHOLARLY_MARKS.search(text):
        return True
    return any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", text))


def _assimilate(m: re.Match) -> str:
    letters = m.group(2)
    return f"{m.group(1)}{letters.lower()}-{letters}"


def popular(text: str, expand_b: bool = False) -> str:
    """Popular transliteration of a name (rules a-e above)."""
    text = unicodedata.normalize("NFC", text)
    if has_scholarly_marks(text):
        text = _LEADING_MARKS.sub("", text)
        text = fold(text)
    text = _SUN_ARTICLE.sub(_assimilate, text)
    if expand_b:
        text = _B_ABBREV.sub(IBN, text)
    return text.strip()


# --------------------------------------------------------------------------
# Search: normal form and sound key
# --------------------------------------------------------------------------
# normalise(text), in order:
#   1. Remove the honorific signs (ﷺ ﷻ: not part of a name) and every ayn, hamza and
#      apostrophe mark: Saʿd, Sa'd and Sad meet.
#   2. Unicode compatibility decomposition, drop every combining mark, lower case.
#      This strips Latin diacritics and Arabic tashkil, and turns أ إ آ into ا and
#      ؤ ئ into و ي (their hamza is a combining mark after decomposition).
#   3. Replace characters by `chars`: ٱ -> ا, ة -> ه, ى -> ي, tatweel removed, the
#      Persian and Urdu letter forms to Arabic ones, Arabic-Indic digits to 0-9.
#   4. Anything that is not a-z, 0-9, an Arabic letter or a hyphen becomes a space.
#   5. Split into words; split each word at hyphens. A part that is a written form of
#      the article (al, el, ul, l, or assimilated: as, ash, ar, an ...) is dropped when
#      another part follows it: al-Ṣiddīq, as-Siddiq and Siddiq meet.
#   6. A word "al" or "el" followed by another word is dropped (al Siddiq).
#      An Arabic word starting with ال and at least four letters long loses the ال.
#   7. A particle followed by another word is unified: b, bin, bn, ben -> ibn;
#      bt, binti -> bint; abi, aba, abou, abul -> abu; um -> umm; ابن -> بن;
#      ابي, ابا -> ابو; abdul, abdur, abdel ... -> abd. The last word of a query is
#      left as typed, because it may be the start of a longer word.
# skeleton(normal), per word: the digraphs kh gh sh th dh dj become one class letter;
# vowels, w and y are dropped, q and c become k; each Arabic letter becomes the class
# of its usual Latin spelling (ا و ي ى ء ع are dropped); a run of the same class
# letter becomes one; a final h is dropped (ة, Fatimah = Fatima). The words are then
# joined and runs collapsed again, so "abu bakr" and "abubakr" give the same key.
SEARCH_ARTICLES = sorted({"al", "el", "ul", "l"} | {v + s for v in "ae" for s in SUN_LETTERS})
RULES = {
    # ﷺ ﷻ, the ayn and hamza marks, ʽ, the apostrophes, ' ´ ′
    "drop": "\ufdfa\ufdfb" + AYN_HAMZA + "\u02bd" + APOSTROPHES + "'\u00b4\u2032",
    "chars": {
        "ٱ": "ا", "ة": "ه", "ى": "ي", "\u0640": "",       # alif wasla, ta marbuta, alif maqsura, tatweel
        "ک": "ك", "ی": "ي", "ے": "ي",                      # Persian and Urdu kaf and ya
        "ہ": "ه", "ۃ": "ه", "ھ": "ه",                      # Urdu ha forms
        "ı": "i", "ł": "l", "ø": "o", "đ": "d", "ß": "ss", "æ": "ae", "œ": "oe",
        **{chr(0x0660 + d): str(d) for d in range(10)},    # Arabic-Indic digits
        **{chr(0x06F0 + d): str(d) for d in range(10)},    # Persian digits
    },
    # keep a-z, 0-9, the Arabic letters (U+0620-064A, 066E-066F, 0671-06D3, 06D5), hyphen
    "nonword": "[^a-z0-9\u0620-\u064a\u066e\u066f\u0671-\u06d3\u06d5-]+",
    "articles": SEARCH_ARTICLES,
    "lone_articles": ["al", "el"],
    "ar_article": "ال",
    "particles": {
        "b": IBN, "bin": IBN, "bn": IBN, "ben": IBN,
        "bt": "bint", "binti": "bint",
        "abi": "abu", "aba": "abu", "abou": "abu", "abul": "abu",
        "um": "umm",
        "ابن": "بن",
        "ابي": "ابو", "ابا": "ابو",
    },
    "abd": "^abd[aeiu](?:l|r|s|t|d|z|n|sh|th|dh)$",
    "sk_digraphs": {"kh": "x", "gh": "g", "sh": "c", "th": "s", "dh": "z", "dj": "j"},
    "sk_chars": {
        "a": "", "e": "", "i": "", "o": "", "u": "", "w": "", "y": "", "q": "k", "c": "k",
        "ب": "b", "ت": "t", "ث": "s", "ج": "j", "ح": "h", "خ": "x",
        "د": "d", "ذ": "z", "ر": "r", "ز": "z", "س": "s", "ش": "c",
        "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "غ": "g", "ف": "f",
        "ق": "k", "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h",
        "پ": "b", "چ": "j", "ژ": "z", "گ": "g", "ڤ": "f",
    },
    # every other character: a-z stand for themselves; digits and anything else are dropped
    "sk_keep": "^[a-z]$",
    "min_inside": 3,      # tiers 3 and 8 need at least this many letters / consonants
    "min_sound_start": 2, # tiers 5 and 7 need at least this many consonants
    "min_near": 4,        # tier 6 needs at least this many letters
    "similar_from": 4,    # tiers from this one on are listed as similar spellings (TIERS)
}

_DROP = set(RULES["drop"])
_NONWORD = re.compile(RULES["nonword"])
_ARTICLES = set(RULES["articles"])
_LONE = set(RULES["lone_articles"])
_ABD = re.compile(RULES["abd"])
_SK_KEEP = re.compile(RULES["sk_keep"])


def normalise(text: str) -> str:
    """The search form of a name or a query (steps 1-7 above)."""
    s = "".join(ch for ch in text if ch not in _DROP)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.category(ch).startswith("M")).lower()
    s = "".join(RULES["chars"].get(ch, ch) for ch in s)
    s = _NONWORD.sub(" ", s)
    words: list[str] = []
    for raw in s.split(" "):
        parts = [p for p in raw.split("-") if p]
        words.extend(p for i, p in enumerate(parts) if not (i < len(parts) - 1 and p in _ARTICLES))
    out: list[str] = []
    for i, w in enumerate(words):
        more = i < len(words) - 1
        if more and w in _LONE:
            continue
        if w.startswith(RULES["ar_article"]) and len(w) >= 4:
            w = w[2:]
        if more:
            if w in RULES["particles"]:
                w = RULES["particles"][w]
            elif _ABD.match(w):
                w = "abd"
        out.append(w)
    return " ".join(out)


def _collapse(s: str) -> str:
    return "".join(ch for i, ch in enumerate(s) if i == 0 or ch != s[i - 1])


def skeleton_words(normal: str) -> list[str]:
    """The sound key of each word of a normal form (empty keys left out)."""
    out = []
    for w in normal.split(" "):
        k, i = [], 0
        while i < len(w):
            two = w[i:i + 2]
            if two in RULES["sk_digraphs"]:
                k.append(RULES["sk_digraphs"][two])
                i += 2
                continue
            ch = w[i]
            if ch in RULES["sk_chars"]:
                k.append(RULES["sk_chars"][ch])
            elif _SK_KEEP.match(ch):
                k.append(ch)
            i += 1
        key = _collapse("".join(k))
        if len(key) > 1 and key.endswith("h"):
            key = key[:-1]
        if key:
            out.append(key)
    return out


def skeleton(normal: str) -> str:
    """The sound key of a normal form: its word keys joined, runs collapsed."""
    return _collapse("".join(skeleton_words(normal)))


# --------------------------------------------------------------------------
# Search: matching and ranking
# --------------------------------------------------------------------------
# Each entity has a few keys: the normal forms of its names, the name as shown first.
# A query matches a key at the first tier that applies, and an entity at its best key.
# Results are ordered by tier; then by how well the name as shown matches (so that
# "Muhammad" lists the Prophet before people whose ism alone is Muhammad); then by the
# length of the matched key, shorter being closer; then by index order (type, A-Z).
# Tiers 0-3 are listed as "matching names", tiers 4-8 as "similar spellings".
TIERS = (
    "0 the whole name: abubakr, Abu Bakr",
    "1 the start of a name: abu ba",
    "2 the start of each word, in any order: bakr, siddiq abu",
    "3 inside a name, min_inside letters or more: akr",
    "4 the same sound key: ابو بكر, Usman for Uthman",
    "5 the sound key starts the name's sound key",
    "6 one letter off (wrong, missing, extra or swapped) at a word start, min_near letters or more",
    "7 the sound key starts at a word of the name",
    "8 the sound key is inside the name's sound key, min_inside consonants or more",
)
SIMILAR_FROM = RULES["similar_from"]
NO_MATCH = RULES["tiers"] = len(TIERS)  # "no match" sorts after every tier


class Key:
    __slots__ = ("c", "words", "csufs", "sk", "sufs")

    def __init__(self, normal: str):
        self.words = [w for w in normal.split(" ") if w]
        self.c = "".join(self.words)
        self.csufs = ["".join(self.words[i:]) for i in range(len(self.words))]
        sw = skeleton_words(normal)
        self.sk = _collapse("".join(sw))
        self.sufs = [_collapse("".join(sw[i:])) for i in range(len(sw))]


def prepare(items: list[dict]) -> list[dict]:
    """items as written to search.json ({u, n, k}); adds the parsed keys."""
    return [{"u": it["u"], "keys": [Key(k) for k in it["k"]]} for it in items]


def within_one(a: str, b: str) -> bool:
    """True if a and b differ by at most one edit: a letter changed, added or dropped,
    or two neighbouring letters swapped. Linear time."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    i = 0
    while i < min(la, lb) and a[i] == b[i]:
        i += 1
    if la == lb:
        return a[i + 1:] == b[i + 1:] or (
            i + 1 < la and a[i] == b[i + 1] and a[i + 1] == b[i] and a[i + 2:] == b[i + 2:])
    if la > lb:
        return a[i + 1:] == b[i:]
    return a[i:] == b[i + 1:]


def near(q: Key, k: Key) -> bool:
    """Tier 6: the query is one edit away from the start of a word of the key."""
    n = len(q.c)
    if n < RULES["min_near"]:
        return False
    return any(within_one(q.c, s[:m]) for s in k.csufs for m in (n - 1, n, n + 1))


def tier(q: Key, k: Key) -> int:
    """The tier at which query key q matches name key k (NO_MATCH if none)."""
    n_in, n_start = RULES["min_inside"], RULES["min_sound_start"]
    if q.c == k.c:
        return 0
    if k.c.startswith(q.c):
        return 1
    if all(any(kw.startswith(qw) for kw in k.words) for qw in q.words):
        return 2
    if len(q.c) >= n_in and q.c in k.c:
        return 3
    if q.sk and q.sk == k.sk:
        return 4
    if len(q.sk) >= n_start and k.sk.startswith(q.sk):
        return 5
    if near(q, k):
        return 6
    if len(q.sk) >= n_start and any(s.startswith(q.sk) for s in k.sufs):
        return 7
    if len(q.sk) >= n_in and q.sk in k.sk:
        return 8
    return NO_MATCH


def search(items: list[dict], query: str) -> list[tuple[str, int]]:
    """Ranked matches for a query over prepared items: [(u, tier), ...]."""
    q = Key(normalise(query))
    if not q.c:
        return []
    found = []
    for pos, it in enumerate(items):
        tiers = [(tier(q, k), len(k.c)) for k in it["keys"]]
        best = min(tiers)
        if best[0] < NO_MATCH:
            found.append((best[0], tiers[0][0], best[1], pos))  # tiers[0]: the name as shown
    found.sort()
    return [(items[pos]["u"], t) for t, _, _, pos in found]


def index_item(url: str, display_name: str, names: list[str]) -> dict:
    """One search.json entry: url path, the name as shown, and the distinct normal forms
    of every name given (the display name first)."""
    keys: list[str] = []
    for n in [display_name] + list(names):
        k = normalise(n)
        if k and k not in keys:
            keys.append(k)
    return {"u": url, "n": display_name, "k": keys}
