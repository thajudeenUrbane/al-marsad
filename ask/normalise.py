"""Name keys for spelling-tolerant lookup, and the match score between two keys.

The first step is the site's own normaliser, `display.fold` from site/display.py
(diacritics stripped, the ayn/hamza marks and curly apostrophes made one plain
apostrophe). It is imported, not copied; the browser port folds the same characters
because build_ask.py embeds display's mark list and the combining-character table in
the index. Everything after fold is ask-specific and table-driven from ask/rules.json
(section "normalise"), so ask/static/ask.js applies the very same tables:

  text_key(s)    fold, lower case, Arabic letter forms unified (alif forms, ta marbuta,
                 alif maqsura), tatweel and the honorific ligatures dropped, "(pbuh)"-style
                 honorifics removed, spaces collapsed. Used to match question shapes.
  name_tokens(s) text_key, then: possessive 's and apostrophes dropped, the article
                 (al-, as-, ash- ... and a free-standing "al"/"the") dropped, ibn/bin/b. ->
                 b, abi/aba -> abu, Abd Allah / Abdallah -> abdullah, the Arabic article
                 dropped, and a light phonetic key per Latin token (double letters
                 collapsed, ee->i, oo/ou->u, ay->ai, aw->au, e->a, o->u, c/q->k, final
                 -ah -> -a). "Mecca" and "Makkah" both become "maka".

score(M, N) compares a mention's tokens with one name's tokens:
  5 same tokens; 4 the mention starts the name; 3 the mention is a run inside the
  name, or both are equal with spaces removed; 2 every token close (edit distance 1
  from 4 letters, 2 from 8) as a prefix, or the name starts with the squashed
  mention; 1 every mention token appears somewhere in the name, or the squashed
  mention is inside the squashed name; 0 no match.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ASK = Path(__file__).resolve().parent
ROOT = ASK.parent
SITE = ROOT / "site"
if str(SITE) not in sys.path:
    sys.path.insert(0, str(SITE))

import display  # noqa: E402  (site/display.py: the site's display rules and normaliser)

RULES = json.loads((ASK / "rules.json").read_text(encoding="utf-8"))
_N = RULES["normalise"]
_L = RULES["linking"]

fold = display.fold                      # the site's normaliser, imported
MARK_CHARS = display._MARK_CHARS        # what fold turns into an apostrophe (embedded for the JS port)

_SPACES = re.compile(_N["spaces"])
_HON = re.compile(_N["honorific_paren"])
_POSS = re.compile(_N["possessive"])
_ART = re.compile(_N["article"])
_NONWORD = re.compile(_N["nonword"])
_DOUBLE = re.compile(r"([a-z])\1+")
_LATIN = re.compile(r"^[a-z0-9]+$")
_ARABIC_TOKEN = re.compile("^[؀-ۿ]")
_TOKEN_MAP = _N["token_map"]
_HEADS = _N["allah_heads"]
_TAILS = _N["allah_tails"]
_ALLAH_ONE = re.compile("^(" + "|".join(_HEADS) + ")(" + "|".join(_TAILS) + ")$")


def text_key(text: str) -> str:
    s = fold(text or "").lower()
    for a, b in _N["arabic_map"]:
        s = s.replace(a, b)
    for ch in _N["drop_chars"]:
        s = s.replace(ch, "")
    for a, b in _N["punct_map"]:
        s = s.replace(a, b)
    s = _HON.sub(" ", s)
    s = _SPACES.sub(" ", s).strip(" ")
    return s


def phonetic(tok: str) -> str:
    if not _LATIN.match(tok):
        return tok
    tok = _DOUBLE.sub(r"\1", tok)
    for a, b in _N["phonetic_multi"]:
        tok = tok.replace(a, b)
    for a, b in _N["phonetic_single"]:
        tok = tok.replace(a, b)
    tok = _DOUBLE.sub(r"\1", tok)
    if len(tok) > 3 and tok.endswith("ah"):
        tok = tok[:-1]
    return tok


def name_tokens(text: str) -> list[str]:
    s = text_key(text)
    s = _POSS.sub("", s)
    s = s.replace("'", "")
    s = _ART.sub(lambda m: m.group(1), s)
    s = _NONWORD.sub(" ", s)
    toks: list[str] = []
    for tok in s.split(" "):
        if not tok:
            continue
        tok = _TOKEN_MAP.get(tok, tok)
        if not tok:
            continue
        art = _N["arabic_article"]
        if _ARABIC_TOKEN.match(tok) and tok.startswith(art) and len(tok) >= 4:
            tok = tok[len(art):]
        toks.append(tok)
    merged: list[str] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in _HEADS and i + 1 < len(toks) and toks[i + 1] in _TAILS:
            merged.append(t + "ullah")
            i += 2
            continue
        m = _ALLAH_ONE.match(t)
        merged.append(m.group(1) + "ullah" if m else t)
        i += 1
    return [phonetic(t) for t in merged]


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[len(b)]


def close(a: str, b: str) -> bool:
    if a == b:
        return True
    shortest = min(len(a), len(b))
    if shortest >= _L["fuzzy_two_min_len"]:
        limit = 2
    elif shortest >= _L["fuzzy_one_min_len"]:
        limit = 1
    else:
        return False
    if abs(len(a) - len(b)) > limit:
        return False
    return levenshtein(a, b) <= limit


def _run_inside(m: list[str], n: list[str]) -> bool:
    k = len(m)
    for i in range(1, len(n) - k + 1):
        if n[i:i + k] == m:
            return True
    return False


def score(m: list[str], n: list[str]) -> int:
    if not m or not n:
        return 0
    if m == n:
        return 5
    k = len(m)
    if k <= len(n) and n[:k] == m:
        return 4
    if _run_inside(m, n):
        return 3
    ms, ns = "".join(m), "".join(n)
    if ms == ns:
        return 3
    if k <= len(n) and all(close(m[i], n[i]) for i in range(k)):
        return 2
    if len(ms) >= _L["squash_prefix_min_len"] and ns.startswith(ms):
        return 2
    if all(t in n for t in m):
        return 1
    if len(ms) >= _L["squash_contains_min_len"] and ms in ns:
        return 1
    return 0


def combining_ranges() -> list[list[int]]:
    """Code point ranges (BMP and beyond) that fold drops: canonical combining class
    not 0, per this Python's unicodedata. Embedded in the index for the JS port."""
    out: list[list[int]] = []
    start = None
    for cp in range(0x110000):
        on = unicodedata.combining(chr(cp)) != 0
        if on and start is None:
            start = cp
        elif not on and start is not None:
            out.append([start, cp - 1])
            start = None
    if start is not None:
        out.append([start, 0x10FFFF])
    return out
