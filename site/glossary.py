"""Glossary of Arabic terms that appear in the graph's labels and on the pages.

Only a term whose definition already stands in the repository's own documents gets a
definition here, and that definition is quoted word for word with its source
(site/data/glossary.json; tests/test_site.py checks every quote against its source file).
Every other term found in the graph is listed as "definition needed". Nothing is defined
from general knowledge.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import display

_MARKS = "\u02bf\u02be\u02bb\u02bc\u2018\u2019"
_TOKEN = re.compile(r"([\w'\u02bf\u02be\u02bb\u02bc\u2018\u2019\-]+)|([^\w\s'\u02bf\u02be\u02bb\u02bc\u2018\u2019\-]+)|(\s+)")


def slug(text: str) -> str:
    f = display.fold(text).lower()
    return re.sub(r"[^a-z0-9]+", "-", f).strip("-")


def _arabic_like(token: str) -> bool:
    if any(ch in _MARKS for ch in token):
        return True
    return any(ord(ch) > 127 and ch.isalpha() for ch in token)


def candidate_terms(label: str) -> list[str]:
    """Terms written in scholarly transliteration inside a vocabulary label.
    'heard from (samāʿ)' -> samāʿ;  'tābiʿ al-tābiʿīn' -> one phrase;  'sīra / maghāzī' -> two."""
    label = label.replace(display.PBUH_SIGN, " ")
    phrases: list[list[str]] = []
    cur: list[str] = []
    for m in _TOKEN.finditer(label):
        word, sep, space = m.groups()
        if word:
            if _arabic_like(word) or (cur and word.lower().startswith("al-")):
                cur.append(word)
            elif cur:
                phrases.append(cur)
                cur = []
        elif sep:
            if cur:
                phrases.append(cur)
                cur = []
    if cur:
        phrases.append(cur)
    return [" ".join(p) for p in phrases]


class Glossary:
    def __init__(self, data_path: str | Path, graph_labels: list[str], vocabulary_labels: list[str]):
        data = json.loads(Path(data_path).read_text(encoding="utf-8"))
        self.entries: dict[str, dict] = {}
        for e in data["defined"]:
            self._add(e["term"], extra=e.get("forms", []), definition=e["definition"],
                      arabic=e.get("arabic"), source=e["source"])
        for e in data.get("needed", []):
            self._add(e["term"], extra=e.get("forms", []))
        for label in vocabulary_labels:
            for term in candidate_terms(label):
                if not self._matches_existing(term):
                    self._add(term)
        self.matchers: list[tuple[re.Pattern, str]] = []
        for key, e in self.entries.items():
            for alt in e["alts"]:
                rx = re.compile(r"(?<![a-z0-9'])" + re.escape(alt) + r"(?![a-z0-9'])", re.IGNORECASE)
                self.matchers.append((rx, key))
        self.matchers.sort(key=lambda m: -len(m[0].pattern))
        # which entries occur in the graph's own labels
        blob = "\n".join(display.fold(l) for l in graph_labels)
        for key, e in self.entries.items():
            e["in_graph"] = any(rx.search(blob) for rx, k in self.matchers if k == key)
        self.used: set[str] = set()

    @staticmethod
    def _alts(term: str, extra: list[str]) -> list[str]:
        alts = []
        for part in re.split(r"\s+/\s+", term):
            alts.append(display.fold(part).lower().strip())
        alts.extend(display.fold(x).lower().strip() for x in extra)
        return [a for i, a in enumerate(alts) if a and a not in alts[:i]]

    def _matches_existing(self, term: str) -> bool:
        alts = set(self._alts(term, []))
        return any(alts & set(e["alts"]) for e in self.entries.values())

    def _add(self, term, extra=(), definition=None, arabic=None, source=None):
        alts = self._alts(term, list(extra))
        key = slug(alts[0])
        if key in self.entries:
            return
        self.entries[key] = {"key": key, "term": term, "alts": alts, "definition": definition,
                             "arabic": arabic, "source": source}

    def listed(self) -> tuple[list[dict], list[dict]]:
        """(defined, needed) entries that occur in graph labels or were linked on a page."""
        shown = [e for k, e in self.entries.items() if e["in_graph"] or k in self.used]
        key = lambda e: display.sort_key(e["term"])
        defined = sorted((e for e in shown if e["definition"]), key=key)
        needed = sorted((e for e in shown if not e["definition"]), key=key)
        return defined, needed
