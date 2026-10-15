"""Display rules for the reader tier, each in one place so it can be changed later.

Source of every rule: docs/handover/maintainer-answers-1.md (15 October 2026) and
docs/handover/slice-2-brief.md, "Display decisions from the maintainer".

Nothing here reads the graph. The model hands plain values in; these functions
decide how they are shown. A rule that needs a field the graph does not have
(gender, Companion status, a modern place name) does nothing until the field exists.

Rules, in the order they appear below:
  1. Names: popular transliteration (the rules are in site/names.py, shared with search).
  2. The Prophet: the sallallahu 'alayhi wa sallam sign after every mention.
  3. Companions: the radiya Allahu 'anhu / 'anha formula, only when both Companion
     status and gender are recorded. Neither is recorded today, so it never shows.
  4. Dates: Gregorian first, Hijri in brackets, only as recorded, uncertainty in words.
  5. Sorting, Arabic-script markup and glossary linking of free text.
"""
from __future__ import annotations

import html
import re
import unicodedata

import names
from names import fold, fold_with_map, has_scholarly_marks  # noqa: F401  (re-exported)

# --------------------------------------------------------------------------
# 1. Names: popular transliteration
# --------------------------------------------------------------------------
# The rules live in site/names.py, next to the search rules that share their tables
# (marks, sun letters, the article, b. for ibn). Summary: a label with no scholarly
# mark is kept as written; a scholarly label loses its leading ayn/hamza marks and its
# diacritics; in every label al- assimilates before a sun letter (Abū Bakr al-Ṣiddīq
# -> Abu Bakr as-Siddiq, Anas ibn al-Nadr -> Anas ibn an-Nadr).
# The one switch: b. -> ibn, OFF by default. identity.csv itself writes "b." in some
# popular forms (Abdullah b. Mas'ud), so the maintainer has not ruled yet. Search
# treats b., bin and ibn as the same either way.
EXPAND_B_TO_IBN = False

_BLESSING_TAIL = re.compile(
    r"\s*\((?:may\s+)?peace(?:\s+and\s+blessings)?\s+(?:be\s+)?upon\s+him\)\s*$", re.IGNORECASE
)


def popularize(text: str) -> str:
    """Popular transliteration of a name (site/names.py, rules a-e)."""
    return names.popular(text, expand_b=EXPAND_B_TO_IBN)


def strip_blessing_tail(label: str) -> str:
    """Remove a trailing '(peace and blessings be upon him)' from a name."""
    return _BLESSING_TAIL.sub("", label).strip()


# --------------------------------------------------------------------------
# 2. The Prophet
# --------------------------------------------------------------------------
PBUH_SIGN = "\ufdfa"  # the sallallahu alayhi wa sallam ligature

# The graph has no flag for "this person is the Prophet". He is found by his label,
# once, here. The match is on the folded, lower-cased label; no entity ID is used.
PROPHET_LABEL_PREFIXES = ("the prophet muhammad", "prophet muhammad")

_BLESSING_PAREN = (
    r"\((?:may\s+)?peace(?:\s+and\s+blessings)?\s+(?:be\s+)?upon\s+him\)"
)
_RE_PROPHET_BLESSING = re.compile(
    r"(Prophet(?:\s+Mu[h\u1e25]ammad)?|Mu[h\u1e25]ammad)\s*" + _BLESSING_PAREN, re.IGNORECASE
)
_RE_PROPHET_MENTION = re.compile(
    r"(?<!I am )(?<!I am the )\b((?:[Tt]he\s+)?Prophet)((?:\s+Mu[h\u1e25]ammad)?)(['\u2019]s)?(?![\w'\u2019])(?!\s*" + PBUH_SIGN + ")"
)
_RE_MESSENGER = re.compile(r"\b([Tt]he\s+Messenger\s+of\s+(?:Allah|God))(?!\w)(?!\s*" + PBUH_SIGN + ")")


def is_prophet_label(label: str) -> bool:
    f = fold(label).lower().strip()
    return any(f.startswith(p) for p in PROPHET_LABEL_PREFIXES)


def honour(text: str) -> str:
    """Put the sign after every mention of the Prophet in a name or short note.

    - '(peace and blessings be upon him)' after Prophet / Muhammad becomes the sign.
    - 'the Prophet', 'the Prophet's', 'the Prophet Muhammad' and 'the Messenger of
      Allah' get the sign unless it is already there.
    - 'Prophet Yusuf' (another prophet) is left alone, and so is the Prophet speaking of
      himself ("I am the Prophet, no lie").
    Free text only. Verbatim passages (the story prose) are not passed through this.
    """
    text = _RE_PROPHET_BLESSING.sub(lambda m: f"{m.group(1)} {PBUH_SIGN}", text)

    def mention(m: re.Match) -> str:
        rest = m.string[m.end():]
        if not m.group(2) and re.match(r"\s+[A-Z][a-z]", rest):
            return m.group(0)  # a different prophet
        if m.group(3):
            return f"{m.group(1)}{m.group(2)}{m.group(3)} {PBUH_SIGN}"
        return f"{m.group(1)}{m.group(2)} {PBUH_SIGN}"

    text = _RE_PROPHET_MENTION.sub(mention, text)
    text = _RE_MESSENGER.sub(lambda m: f"{m.group(1)} {PBUH_SIGN}", text)
    return text


def person_display_name(label: str, prophet: bool = False) -> str:
    """The name shown for a person: popular form, honorific rules applied."""
    if prophet or is_prophet_label(label):
        name = popularize(strip_blessing_tail(label))
        return name if name.endswith(PBUH_SIGN) else f"{name} {PBUH_SIGN}"
    return honour(popularize(label))


def name_display(label: str) -> str:
    """The name shown for an event, place or group: popular form, sign rules."""
    return honour(popularize(strip_blessing_tail(label)))


# --------------------------------------------------------------------------
# 3. Companions
# --------------------------------------------------------------------------
# "Other honorifics on every mention only where the graph records the person as a
# Companion and their gender. Never guess either." The graph has no gender field
# (the ontology defines none) and no person carries mrs:companionStatus, so this
# returns None for everyone today. When a gender predicate is added, list its IRI
# in GENDER_PREDICATES and map its values in GENDER_VALUES.
GENDER_PREDICATES: tuple[str, ...] = ()
GENDER_VALUES = {"male": "male", "female": "female"}
COMPANION_ATTESTED = "attested"  # mrs:comp_attested, the only value that counts


def companion_honorific_key(companion_status: str | None, gender: str | None) -> str | None:
    """i18n key of the honorific to show after a name, or None."""
    if companion_status != COMPANION_ATTESTED:
        return None
    if gender == "male":
        return "honorific.companion_male"
    if gender == "female":
        return "honorific.companion_female"
    return None


# --------------------------------------------------------------------------
# 4. Dates
# --------------------------------------------------------------------------
# Gregorian first, then Hijri in brackets: "622 CE (1 AH)". Only what the graph has.
# A date is shown from the recorded native text where that has both calendars;
# otherwise the Gregorian part is the recorded earliest/latest bounds (for a Hijri
# date these are a stored conversion, and the note says so with its uncertainty).
# Nothing is computed here and no bound is narrowed.
_DIGITS = str.maketrans("\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669"
                        "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9",
                        "0123456789" "0123456789")
_ISO = re.compile(r"^(-?\d{1,6})-(\d\d)-(\d\d)")
_C_DOT = re.compile(r"(?<![\w])c\.\s*")


def _ymd(value: str | None):
    if not value:
        return None
    m = _ISO.match(value)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def bounds_text(earliest: str | None, latest: str | None, precision: str | None, t) -> str | None:
    """Gregorian text from recorded bounds. `t(key, **kw)` is the translator."""
    e, l = _ymd(earliest), _ymd(latest)
    ce = t("date.ce")
    if e and not l:
        return t("date.from", date=f"{e[0]} {ce}")
    if l and not e:
        return t("date.until", date=f"{l[0]} {ce}")
    if not e or not l:
        return None
    month = lambda m: t(f"date.month.{m}")
    if precision == "day":
        if e == l:
            return f"{e[2]} {month(e[1])} {e[0]} {ce}"
        if (e[0], e[1]) == (l[0], l[1]):
            return f"{e[2]}–{l[2]} {month(e[1])} {e[0]} {ce}"
        if e[0] == l[0]:
            return f"{e[2]} {month(e[1])} – {l[2]} {month(l[1])} {e[0]} {ce}"
        return f"{e[2]} {month(e[1])} {e[0]} – {l[2]} {month(l[1])} {l[0]} {ce}"
    if precision == "month":
        if (e[0], e[1]) == (l[0], l[1]):
            return f"{month(e[1])} {e[0]} {ce}"
        gap = (l[0] * 12 + l[1]) - (e[0] * 12 + e[1])
        if 0 < gap <= 2 and e[0] == l[0]:
            return f"{month(e[1])}–{month(l[1])} {e[0]} {ce}"
        # bounds wider than the stated precision: say the year(s) only, never a month
    if e[0] == l[0]:
        return f"{e[0]} {ce}"
    return f"{e[0]}–{l[0]} {ce}"


def format_extent(ext: dict, t) -> dict:
    """ext keys: native, calendar, earliest, latest, precision, basis, conv_method,
    conv_days, relative, disputed (all optional, strings or bools).
    Returns {'text': str|None, 'notes': [str]}. `text` may contain Arabic script;
    the renderer marks that up."""
    native = (ext.get("native") or "").strip()
    cal = ext.get("calendar")
    g_text = h_text = other = None
    ah, ce = t("date.ah"), t("date.ce")

    remark = None
    if native:
        n = native.translate(_DIGITS)
        # a trailing "(...)" in the recorded text is the recorder's remark, not part of the date
        m = re.match(r"^(.*\d.*?\S)\s*\(([^()]+)\)\s*$", n)
        if m:
            n, remark = m.group(1), m.group(2).strip()
        if " / " in n and n.split(" / ", 1)[0].rstrip().endswith("AH") and "CE" in n.split(" / ", 1)[1]:
            h_text, g_text = [p.strip() for p in n.split(" / ", 1)]
        elif re.search(r"\bCE\b", n) and not re.search(r"\bAH\b", n):
            g_text = n
        elif re.search(r"\bAH\b", n):
            h_text = n
        elif cal == "hijri" and re.fullmatch(r"\d{1,4}", n):
            h_text = f"{n} {ah}"
        else:
            other = native  # recorded text we do not parse; shown as it stands

    notes: list[str] = []
    converted = False
    if g_text is None:
        derived = bounds_text(ext.get("earliest"), ext.get("latest"), ext.get("precision"), t)
        if derived:
            g_text = derived
            converted = cal == "hijri"
    if converted:
        days = ext.get("conv_days")
        method = ext.get("conv_method")
        if days not in (None, "") and method:
            key = "date.converted_one" if str(days) == "1" else "date.converted"
            notes.append(t(key, method=method, days=days))
        else:
            notes.append(t("date.converted_plain"))
    if remark:
        notes.append(t("date.remark", value=_C_DOT.sub(t("date.around") + " ", remark)))

    def tidy(s: str | None) -> str | None:
        if s is None:
            return None
        s = _C_DOT.sub(t("date.around") + " ", s)
        return popularize(s) if not has_arabic(s) else s

    g_text, h_text, other = tidy(g_text), tidy(h_text), tidy(other)
    if g_text and h_text:
        text = f"{g_text} ({h_text})"
    else:
        text = g_text or h_text or other
    if other and (g_text or h_text):
        text = f"{text} ({other})"

    if ext.get("precision"):
        notes.append(t("date.precision", value=t_opt(t, f"precision.{ext['precision']}", ext["precision"])))
    if ext.get("basis"):
        notes.append(t("date.basis", value=t_opt(t, f"basis.{ext['basis']}", ext["basis"])))
    if ext.get("relative"):
        notes.append(t("date.relative"))
    if ext.get("disputed"):
        notes.append(t("date.disputed"))
    return {"text": text, "notes": notes}


def t_opt(t, key: str, fallback: str) -> str:
    """Translate a data-derived key; use the graph's own label when no key exists."""
    try:
        return t(key)
    except KeyError:
        return fallback


# --------------------------------------------------------------------------
# 5. Sorting, Arabic-script markup, glossary linking
# --------------------------------------------------------------------------
_ARTICLE_PREFIX = re.compile(r"^(?:the\s+|(?:a[lsdrznt]|ash|adh|ath)-)", re.IGNORECASE)


def sort_key(name: str) -> str:
    """A-Z key: folded, lower-case, a leading 'The' or 'al-'-type article ignored."""
    key = fold(name).lower().strip()
    key = re.sub(r"^[^a-z0-9]+", "", key)
    key = _ARTICLE_PREFIX.sub("", key)
    return key


def index_letter(name: str) -> str:
    k = sort_key(name)
    return k[:1].upper() if k[:1].isalpha() else "#"


# Arabic, Arabic Supplement, Arabic Extended-A, Presentation Forms A and B; the honorific
# ligature U+FDFA is left out on purpose (see mark_arabic)
_ARABIC_BLOCKS = "\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdf9\ufdfb-\ufdff\ufe70-\ufeff"
_ARABIC_RUN = re.compile(f"[{_ARABIC_BLOCKS}]+(?:[ \u200c\u200d]+[{_ARABIC_BLOCKS}]+)*")


def has_arabic(text: str) -> bool:
    return bool(_ARABIC_RUN.search(text))


def mark_arabic(escaped: str) -> str:
    """Wrap each run of Arabic script in an already-escaped string with lang/dir.
    The honorific sign is wrapped on its own (class pbuh) so that fonts and screen
    readers treat it as Arabic; being one isolated character it does not reorder the
    English words around it."""
    out = _ARABIC_RUN.sub(lambda m: f'<span lang="ar" dir="rtl">{m.group(0)}</span>', escaped)
    return out.replace(PBUH_SIGN, f'<span class="pbuh" lang="ar" dir="rtl">{PBUH_SIGN}</span>')


# Plain words (maintainer answer B11): an on/off switch, JavaScript only, for readers who
# want plain English instead of Arabic terms. The pages are complete and unchanged without
# it. link_terms marks two things for it, and the switch (static/enhance.js) acts only on
# these marks:
#   - a term in brackets right after the words it names, "Generation (ṭabaqa)" or "the
#     Trench (al-Khandaq)": the brackets are wrapped in <span class="t-gloss">, which plain
#     words hides, since the plain words are already there;
#   - any other term whose glossary entry records a plain wording (with its source, like a
#     definition) gets data-plain="..." with that wording, which plain words shows instead.
#     A term joined to another word (al-Khandaq, Isra wal-Mi'raj) or already followed by
#     its gloss in brackets is left as written, so no sentence is broken.
_GLOSS_OPEN = re.compile(r"\s\((?:[Aa]l-)?$")
_JOINED_BEFORE = "-'’ʼʿʾ"


def plain_form(wording: str, original: str) -> str:
    """The plain wording, capitalised when the term it replaces is."""
    if original[:1].isupper() and wording[:1].islower():
        return wording[0].upper() + wording[1:]
    return wording


def link_terms(text: str, matchers, href_for, linked: set | None = None, once: bool = False,
               plain_for=None) -> tuple[str, set]:
    """Escape `text` and wrap glossary terms in links. Returns (html, keys_linked_here).

    `matchers`: list of (compiled regex on FOLDED text, term_key), longest first.
    `href_for(term_key)` gives the glossary URL. Terms are matched on the folded
    text, so 'sahabi' finds 'ṣaḥābī', and the original characters are wrapped.
    With once=True a term already in `linked` (the page's set) is not linked again;
    the set is updated in place. `plain_for(term_key)` gives the plain wording the
    glossary records for a term, or None (see "Plain words" above).
    """
    folded, idx = fold_with_map(text)
    text = unicodedata.normalize("NFC", text)
    spans: list[tuple[int, int, str]] = []
    taken = [False] * len(folded)
    here: set = set()
    for rx, key in matchers:
        for m in rx.finditer(folded):
            if m.start() == m.end() or any(taken[m.start():m.end()]):
                continue
            for i in range(m.start(), m.end()):
                taken[i] = True
            spans.append((idx[m.start()], idx[m.end() - 1] + 1, key))
    spans.sort()
    esc = lambda s: mark_arabic(html.escape(s, quote=False))
    out, pos = [], 0
    for a, b, key in spans:
        if a < pos:
            continue
        linking = not (once and linked is not None and key in linked)
        g = _GLOSS_OPEN.search(text, pos, a) if text[b:b + 1] == ")" else None
        gloss = g is not None and g.end() == a and re.search(r"\w", text[:g.start()]) is not None
        wording = None if gloss or plain_for is None else plain_for(key)
        joined = a > 0 and text[a - 1] in _JOINED_BEFORE
        if wording and (joined or re.match(r"\s*\(", text[b:])):
            wording = None
        if not linking and not gloss and not wording:
            continue
        attr = f' data-plain="{html.escape(plain_form(wording, text[a:b]))}"' if wording else ""
        if linking:
            term = f'<a class="term" href="{html.escape(href_for(key))}"{attr}>{esc(text[a:b])}</a>'
            here.add(key)
            if once and linked is not None:
                linked.add(key)
        elif attr:
            term = f'<span class="term-text"{attr}>{esc(text[a:b])}</span>'
        else:
            term = esc(text[a:b])
        if gloss:
            out.append(esc(text[pos:g.start()]))
            out.append(f'<span class="t-gloss">{esc(text[g.start():a])}{term})</span>')
            pos = b + 1
        else:
            out.append(esc(text[pos:a]))
            out.append(term)
            pos = b
    out.append(esc(text[pos:]))
    return "".join(out), here


# --------------------------------------------------------------------------
# 6. AI-generated sources
# --------------------------------------------------------------------------
# Maintainer answer E35: the 50 Stories document was generated by an AI platform and
# its authenticity is unknown. Slice 1d records that in the graph (the Work's creator
# becomes a software agent, which model.py already treats as AI-generated). Until that
# lands, the Work is recognised by the start of its title, here and nowhere else.
AI_GENERATED_WORK_LABEL_PREFIXES = ("50 Stories",)
