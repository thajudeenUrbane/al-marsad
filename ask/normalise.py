"""Name keys for spelling-tolerant lookup, and the match score between two keys.

Built on the site's own name rules, site/names.py (slice 2b), imported and not copied:
  names.fold          diacritics stripped, the ayn/hamza marks and curly apostrophes
                      made one plain apostrophe (display.fold is the same function)
  names.normalise     the search form of a name: marks and apostrophes dropped, lower
                      case, Arabic letter forms unified, the article (al-, as-, ash- ...,
                      Arabic al-) left out, b./bin/ibn and abi/aba/abu made one
  names.skeleton_words  the sound key of each word: consonant classes, so that Mecca and
                      Makkah, Uthman and Usman, Badr and Bedr meet
The browser port (ask/static/ask.js) repeats those steps with names.RULES, which
build_ask.py writes into the index, so it holds no table of its own; the parity test
compares the two on every name in the graph.

Ask adds, in ask/rules.json "normalise":
  text_key(s)    for matching question shapes: fold, lower case, Arabic letter forms,
                 tatweel and honorific signs out, "(pbuh)"-style honorifics out, spaces
                 collapsed. Punctuation and apostrophes are kept (the shapes need "'s").
  name_tokens(s) the words of names.normalise, after "(pbuh)"-style honorifics and a
                 possessive 's are taken off; "the" is left out; Abd Allah, Abdallah and
                 Abdullah become one word.

score(M, N) compares a mention's words with one name's words:
  6 the same words
  5 the same number of words, each the same name spelled differently: one letter off
    (from 4 letters; two from 8), or the same sound key of 3 consonants or more and
    no more than sound_max_edits letters apart (Hudaybiyah / al-Hudaybiyya, Medina /
    al-Madina, Usman / Uthman; not Siffin / ʿUsfān, which share s-f-n only)
  4 the mention's words start the name
  3 the mention's words start the name, each spelled differently or with the same
    sound key of any length (Mecca / Makkah, Ayesha / A'isha); a key of 3 or more is
    bounded as in 5
  2 the mention is a run of words inside the name, or both are equal with spaces
    removed (abubakr / Abu Bakr)
  1 the name starts with the squashed mention, or every mention word is somewhere in
    the name, or the squashed mention is inside the squashed name
  0 no match
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

import display  # noqa: E402,F401  (site/display.py: the site's display rules)
import names  # noqa: E402  (site/names.py: the site's name rules, shared by display and search)

RULES = json.loads((ASK / "rules.json").read_text(encoding="utf-8"))
_N = RULES["normalise"]
_L = RULES["linking"]

fold = names.fold                                   # the site's fold, imported
MARK_CHARS = names.AYN_HAMZA + names.APOSTROPHES    # what fold turns into an apostrophe

_SPACES = re.compile(_N["spaces"])
_HON = re.compile(_N["honorific_paren"])
_POSS = re.compile(_N["possessive"])
_STOP = set(_N["stop_words"])
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


def name_tokens(text: str) -> list[str]:
    s = _HON.sub(" ", fold(text or "").lower())
    s = _POSS.sub("", s)
    words = [w for w in names.normalise(s).split(" ") if w and w not in _STOP]
    merged: list[str] = []
    i = 0
    while i < len(words):
        w = words[i]
        if w in _HEADS and i + 1 < len(words) and words[i + 1] in _TAILS:
            merged.append(w + "ullah")
            i += 2
            continue
        m = _ALLAH_ONE.match(w)
        merged.append(m.group(1) + "ullah" if m else w)
        i += 1
    return merged


def sound(word: str) -> str:
    """The site's sound key of one word ("" when it has no consonant)."""
    keys = names.skeleton_words(word)
    return keys[0] if keys else ""


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[len(b)]


def close(a: str, b: str, loose: bool = False) -> bool:
    """The same word spelled differently. loose also accepts a short shared sound key.
    A sound key of three consonants or more is shared by many different names (Siffin,
    ʿUsfān, Ṣafwān are all s-f-n), so it counts only when the spellings are also within
    sound_max_edits letters; a shorter key is the documented spelling-variant class
    (Mecca / Makkah, Ayesha / A'isha) and is not bounded."""
    if a == b:
        return True
    sa = sound(a)
    if sa and sa == sound(b) and (loose or len(sa) >= _L["sound_exact_min_len"]):
        if len(sa) < _L["sound_exact_min_len"] or levenshtein(a, b) <= _L["sound_max_edits"]:
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


def spelling_distance(m: list[str], n: list[str]) -> int:
    """How many letters apart a mention's words are from the name's first words."""
    return sum(levenshtein(m[i], n[i]) for i in range(min(len(m), len(n))))


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
        return 6
    k = len(m)
    if k == len(n) and all(close(m[i], n[i]) for i in range(k)):
        return 5
    if k <= len(n) and n[:k] == m:
        return 4
    if k <= len(n) and all(close(m[i], n[i], True) for i in range(k)):
        return 3
    if _run_inside(m, n):
        return 2
    ms, ns = "".join(m), "".join(n)
    if ms == ns:
        return 2
    if len(ms) >= _L["squash_prefix_min_len"] and ns.startswith(ms):
        return 1
    if all(t in n for t in m):
        return 1
    if len(ms) >= _L["squash_contains_min_len"] and ms in ns:
        return 1
    return 0


def combining_ranges() -> list[list[int]]:
    """Code point ranges that fold drops: canonical combining class not 0, per this
    Python's unicodedata. Embedded in the index for the JS port of fold."""
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
