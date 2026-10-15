"""The typed query DSL (docs/07 section 4): parser, validator, executor, plain-language
rendering. The grammar and every operation are described in ask/DSL.md.

A query is text such as

    both(people(at: place "Badr"), people(at: place "Uḥud"))

It is parsed into a tree, validated against a closed table of operations (unknown
operations, wrong argument types, unknown or ambiguous names, years out of range and
over-deep queries fail loudly, before anything runs), executed over the index built
from build/graph.ttl (ask/index.py), and rendered back as a plain sentence. Every row
of a result carries the numbers of the claims behind it; a claim carries its status.

    .venv/bin/python -m ask.dsl 'participants(event "Battle of Badr")'

ask/static/ask.js is a line-by-line port of this module; ask/tests/test_parity.py
checks that both give the same output.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ask.normalise import ASK, RULES, name_tokens

KINDS = ("person", "group", "place", "event", "story")
AGENTS = ("person", "group")
LIMITS = RULES["limits"]
NEGATIVE = ("absent_from",)
PLACE_LINKS = ("took_place_at", "occurred_at")
LEFT_OUT = ("rejected", "superseded")
SET_TYPES = ("agents", "events", "stories", "places")
TIES = ("any", "parent", "father", "mother", "child", "spouse", "sibling")

# The closed set of operations. pos: positional argument types; kw: keyword -> type or
# list of allowed words (the first word is the default); need: required keywords;
# need_any: at least one keyword; ret: what it returns ("same": the type of its
# arguments, "first": the type of its first argument).
SIGS = {
    "participants": {"pos": ["target"], "kw": {"as": ["any", "leader"]}, "ret": "agents"},
    "people": {"pos": [], "kw": {"at": "place", "from": "year", "to": "year"}, "need": ["at"], "ret": "agents"},
    "absent": {"pos": ["target"], "kw": {}, "ret": "agents"},
    "events": {"pos": [], "kw": {"at": "place", "involving": "agent", "from": "year", "to": "year"},
               "need_any": True, "ret": "events"},
    "stories": {"pos": [], "kw": {"involving": "agent"}, "need": ["involving"], "ret": "stories"},
    "relatives": {"pos": ["person"], "kw": {"tie": list(TIES)}, "ret": "agents"},
    "connected": {"pos": ["agent"], "kw": {"via": ["any", "ties", "events"]}, "ret": "agents"},
    "between": {"pos": ["agent", "happening_or_place"], "kw": {}, "ret": "links"},
    "path": {"pos": ["entity", "entity"], "kw": {"max": "steps"}, "ret": "path"},
    "when": {"pos": ["dated"], "kw": {}, "ret": "dates"},
    "where": {"pos": ["happening"], "kw": {}, "ret": "places"},
    "about": {"pos": ["entity"], "kw": {}, "ret": "about"},
    "both": {"pos": ["set", "set"], "kw": {}, "ret": "same"},
    "either": {"pos": ["set", "set"], "kw": {}, "ret": "same"},
    "except": {"pos": ["set", "set"], "kw": {}, "ret": "same"},
    "count": {"pos": ["set"], "kw": {}, "ret": "count"},
    "reviewed": {"pos": ["set"], "kw": {}, "ret": "first"},
}
REF_KINDS = {
    "person": ["person"], "agent": ["person", "group"], "place": ["place"],
    "entity": ["person", "group", "place", "event", "story"],
    "happening": ["event", "story"], "happening_or_place": ["event", "story", "place"],
    "dated": ["event", "story", "person"],
}
DEFAULTS = {("participants", "as"): "any", ("relatives", "tie"): "any", ("connected", "via"): "any",
            ("path", "max"): LIMITS["path_default"]}


class DslError(Exception):
    """A query that cannot run. key is an i18n key under "error."; params fill it."""

    def __init__(self, error_key: str, /, **params):
        super().__init__(error_key)
        self.key = error_key
        self.params = params

    def as_dict(self) -> dict:
        return {"key": self.key, "params": self.params}


# ---------------------------------------------------------------------------- text
def fmt(template: str, /, **kw) -> str:
    """Fill {name} slots. The same simple rule as the JS port (no format spec)."""
    return re.sub(r"\{([a-z_]+)\}", lambda m: str(kw[m.group(1)]), template)


def quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _near(tok: dict) -> str:
    return "" if tok["t"] == "end" else str(tok["v"])


def _alpha(c: str) -> bool:
    return ("a" <= c <= "z") or ("A" <= c <= "Z") or c == "_"


def _alnum(c: str) -> bool:
    return _alpha(c) or ("0" <= c <= "9")


# ---------------------------------------------------------------------------- scanner
def scan(text: str) -> list[dict]:
    toks: list[dict] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\n\r":
            i += 1
            continue
        if c in "(),:":
            toks.append({"t": c, "v": c})
            i += 1
            continue
        if c == '"':
            j, buf = i + 1, []
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                    continue
                buf.append(text[j])
                j += 1
            if j >= n:
                raise DslError("error.unterminated")
            toks.append({"t": "str", "v": "".join(buf)})
            i = j + 1
            continue
        if c == "#":
            j = i + 1
            while j < n and _alnum(text[j]) and text[j] != "_":
                j += 1
            if j == i + 1:
                raise DslError("error.syntax", near="#")
            toks.append({"t": "pid", "v": text[i + 1:j]})
            i = j
            continue
        if "0" <= c <= "9":
            j = i
            while j < n and "0" <= text[j] <= "9":
                j += 1
            if j - i > 6:
                raise DslError("error.number", near=text[i:j])
            toks.append({"t": "num", "v": int(text[i:j])})
            i = j
            continue
        if _alpha(c):
            j = i
            while j < n and _alnum(text[j]):
                j += 1
            toks.append({"t": "id", "v": text[i:j].lower()})
            i = j
            continue
        raise DslError("error.character", near=c)
    toks.append({"t": "end", "v": ""})
    return toks


# ---------------------------------------------------------------------------- parser
class Parser:
    def __init__(self, text: str):
        if len(text) > LIMITS["dsl_max"]:
            raise DslError("error.too_long")
        self.toks = scan(text)
        self.i = 0

    def peek(self, k: int = 0) -> dict:
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def take(self) -> dict:
        tok = self.toks[self.i]
        self.i += 1
        return tok

    def expect(self, t: str) -> dict:
        tok = self.take()
        if tok["t"] != t:
            raise DslError("error.expected", want=t, near=_near(tok))
        return tok

    def parse(self) -> dict:
        node = self.value(0)
        if self.peek()["t"] != "end":
            raise DslError("error.trailing", near=_near(self.peek()))
        return node

    def value(self, depth: int) -> dict:
        if depth > LIMITS["max_depth"]:
            raise DslError("error.too_deep")
        tok = self.peek()
        if tok["t"] == "id":
            nxt = self.peek(1)
            if nxt["t"] == "(":
                return self.call(depth)
            if tok["v"] in KINDS and nxt["t"] in ("str", "pid"):
                self.take()
                self.take()
                if nxt["t"] == "str":
                    return {"t": "ref", "kind": tok["v"], "label": nxt["v"]}
                return {"t": "ref", "kind": tok["v"], "pid": nxt["v"]}
            self.take()
            return {"t": "word", "w": tok["v"]}
        if tok["t"] == "num":
            self.take()
            nxt = self.peek()
            if nxt["t"] == "id" and nxt["v"] in ("ah", "ce"):
                self.take()
                return {"t": "year", "n": tok["v"], "era": nxt["v"]}
            return {"t": "num", "n": tok["v"]}
        raise DslError("error.unexpected", near=_near(tok))

    def call(self, depth: int) -> dict:
        name = self.take()["v"]
        self.expect("(")
        args: list = []
        kw: dict = {}
        if self.peek()["t"] != ")":
            while True:
                if self.peek()["t"] == "id" and self.peek(1)["t"] == ":":
                    key = self.take()["v"]
                    self.take()
                    if key in kw:
                        raise DslError("error.duplicate", op=name, key=key)
                    kw[key] = self.value(depth + 1)
                else:
                    if kw:
                        raise DslError("error.positional", op=name)
                    args.append(self.value(depth + 1))
                if self.peek()["t"] == ",":
                    self.take()
                    continue
                break
        self.expect(")")
        return {"t": "op", "op": name, "args": args, "kw": kw}


def parse(text: str) -> dict:
    return Parser(text).parse()


# ---------------------------------------------------------------------------- calendar
# Year bounds for the time filter. The graph's own conversions (mrs:conversionMethod
# "tabular-islamic-civil") give Julian-calendar dates for these centuries, so the query
# bounds use the same: the tabular Islamic calendar with the civil epoch (1 Muharram
# 1 AH = Julian 16 July 622 = JDN 1948440). Only query bounds are converted; no date of
# any event is computed here.
def julian_from_jdn(jdn: int) -> str:
    c = jdn + 32082
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = d - 4800 + m // 10
    return f"{year:04d}-{month:02d}-{day:02d}"


def ah_year_start_jdn(y: int) -> int:
    return 1948440 + 354 * (y - 1) + (3 + 11 * y) // 30


def year_bounds(n: int, era: str) -> tuple[str, str]:
    if era == "ah":
        return julian_from_jdn(ah_year_start_jdn(n)), julian_from_jdn(ah_year_start_jdn(n + 1) - 1)
    return f"{n:04d}-01-01", f"{n:04d}-12-31"


# ---------------------------------------------------------------------------- engine
class Engine:
    """Validates and runs queries over one index (ask/index.py)."""

    def __init__(self, ix: dict):
        self.ix = ix
        self.E = ix["entities"]
        self.C = ix["claims"]
        self.touch: list[list[int]] = [[] for _ in self.E]
        for j, c in enumerate(self.C):
            self.touch[c["s"]].append(j)
            if c["o"] != c["s"]:
                self.touch[c["o"]].append(j)
        self.by_key: dict[str, list[int]] = {}
        self.by_ref: dict[str, int] = {}
        for i, e in enumerate(self.E):
            self.by_ref[e["r"]] = i
            for k in e["keys"]:
                lst = self.by_key.setdefault(e["k"] + "|" + " ".join(k), [])
                if i not in lst:
                    lst.append(i)

    # ------------------------------------------------------------ helpers
    def kind(self, i: int) -> str:
        return self.E[i]["k"]

    def usable(self, c: dict) -> bool:
        return c.get("st") not in LEFT_OUT

    def positive(self, c: dict) -> bool:
        """A claim that puts its subject in an event: a participation, or an assertion
        whose relation is not a recorded absence."""
        return c["k"] == "p" or (c["k"] == "a" and c["p"] not in NEGATIVE)

    def is_leader(self, c: dict) -> bool:
        return (c["k"] == "a" and c["p"] == "led") or (c["k"] == "p" and c.get("rk") == "leader")

    def ref_text(self, i: int) -> str:
        e = self.E[i]
        if e["u"]:
            return e["k"] + " " + quote(e["l"])
        return e["k"] + " #" + e["r"].split("/", 1)[1]

    # ------------------------------------------------------------ validation
    def resolve(self, node: dict) -> int:
        kind = node["kind"]
        if "pid" in node:
            i = self.by_ref.get(kind + "/" + node["pid"])
            if i is None:
                raise DslError("error.no_id", kind=kind, id=node["pid"])
            return i
        key = kind + "|" + " ".join(name_tokens(node["label"]))
        found = self.by_key.get(key, [])
        if not found:
            raise DslError("error.not_found", kind=kind, label=node["label"])
        if len(found) > 1:
            raise DslError("error.ambiguous", kind=kind, label=node["label"], n=len(found))
        return found[0]

    def validate(self, node: dict) -> dict:
        self._ops = 0
        return self._check(node, 0)

    def _arg(self, op: str, want, node: dict, depth: int, where: str) -> dict:
        if isinstance(want, list):
            if node["t"] != "word" or node["w"] not in want:
                raise DslError("error.word", op=op, key=where, allowed=", ".join(want))
            return node
        if want == "year":
            if node["t"] != "year":
                raise DslError("error.type", op=op, key=where, want="year")
            n, era = node["n"], node["era"]
            ok = 1 <= n <= RULES["time"]["max_ah"] if era == "ah" else RULES["time"]["min_ce"] <= n <= RULES["time"]["max_ce"]
            if not ok:
                raise DslError("error.year", year=f"{n} {era.upper()}")
            s, e = year_bounds(n, era)
            return {"t": "year", "n": n, "era": era, "start": s, "end": e}
        if want == "steps":
            if node["t"] != "num" or not (1 <= node["n"] <= LIMITS["path_max"]):
                raise DslError("error.steps", max=LIMITS["path_max"])
            return node
        if want in ("target", "set"):
            if node["t"] == "ref" and want == "target":
                if node["kind"] not in ("event", "story"):
                    raise DslError("error.type", op=op, key=where, want="target")
                return {"t": "ref", "kind": node["kind"], "e": self.resolve(node)}
            if node["t"] != "op":
                raise DslError("error.type", op=op, key=where, want=want)
            sub = self._check(node, depth + 1)
            ok = ("events", "stories") if want == "target" else SET_TYPES
            if sub["ty"] not in ok:
                raise DslError("error.type", op=op, key=where, want=want)
            return sub
        kinds = REF_KINDS[want]
        if node["t"] != "ref" or node["kind"] not in kinds:
            raise DslError("error.type", op=op, key=where, want=want)
        return {"t": "ref", "kind": node["kind"], "e": self.resolve(node)}

    def _check(self, node: dict, depth: int) -> dict:
        if node["t"] != "op":
            raise DslError("error.not_op")
        if depth > LIMITS["max_depth"]:
            raise DslError("error.too_deep")
        self._ops += 1
        if self._ops > LIMITS["max_ops"]:
            raise DslError("error.too_many")
        op = node["op"]
        sig = SIGS.get(op)
        if sig is None:
            raise DslError("error.unknown_op", op=op)
        if len(node["args"]) != len(sig["pos"]):
            raise DslError("error.arity", op=op, n=len(sig["pos"]))
        args = [self._arg(op, want, a, depth, str(k + 1)) for k, (want, a) in enumerate(zip(sig["pos"], node["args"]))]
        kw = {}
        for key, val in node["kw"].items():
            if key not in sig["kw"]:
                raise DslError("error.keyword", op=op, key=key)
            kw[key] = self._arg(op, sig["kw"][key], val, depth, key)
        for key in sig.get("need", []):
            if key not in kw:
                raise DslError("error.missing", op=op, key=key)
        if sig.get("need_any") and not kw:
            raise DslError("error.filter", op=op)
        if "from" in kw and "to" in kw and kw["from"]["start"] > kw["to"]["end"]:
            raise DslError("error.range")
        if op == "path" and args[0]["e"] == args[1]["e"]:
            raise DslError("error.same")
        ret = sig["ret"]
        if ret == "same":
            if args[0]["ty"] != args[1]["ty"]:
                raise DslError("error.mixed", op=op)
            ret = args[0]["ty"]
        elif ret == "first":
            ret = args[0]["ty"]
        return {"t": "op", "op": op, "args": args, "kw": kw, "ty": ret}

    # ------------------------------------------------------------ canonical text
    def text(self, node: dict) -> str:
        t = node["t"]
        if t == "ref":
            if "e" in node:
                return self.ref_text(node["e"])
            if "label" in node:
                return node["kind"] + " " + quote(node["label"])
            return node["kind"] + " #" + node["pid"]
        if t == "year":
            return f"{node['n']} {node['era'].upper()}"
        if t == "num":
            return str(node["n"])
        if t == "word":
            return node["w"]
        op = node["op"]
        parts = [self.text(a) for a in node["args"]]
        order = list(SIGS[op]["kw"]) if op in SIGS else list(node["kw"])
        for key in order:
            if key not in node["kw"]:
                continue
            v = node["kw"][key]
            default = DEFAULTS.get((op, key))
            if default is not None and ((v["t"] == "word" and v["w"] == default) or (v["t"] == "num" and v["n"] == default)):
                continue
            parts.append(key + ": " + self.text(v))
        return op + "(" + ", ".join(parts) + ")"

    # ------------------------------------------------------------ execution
    def execute(self, node: dict) -> dict:
        return getattr(self, "op_" + node["op"])(node)

    def _word(self, node: dict, key: str) -> str:
        v = node["kw"].get(key)
        return v["w"] if v else DEFAULTS[(node["op"], key)]

    def _rows(self, rows: dict, tags: dict | None = None) -> list[dict]:
        out = []
        for i in sorted(rows):
            row = {"e": i, "c": sorted(set(rows[i]))}
            if tags and i in tags:
                row["tag"] = tags[i]
            out.append(row)
        return out

    def _set(self, of: str, rows: dict, notes: list, tags: dict | None = None, **extra) -> dict:
        res = {"type": "set", "of": of, "rows": self._rows(rows, tags), "notes": notes}
        res.update(extra)
        return res

    def _targets(self, node: dict) -> tuple[list[int], list[dict] | None, list[dict]]:
        """Entities a target stands for, the searched events (when it was a query), notes."""
        if node["t"] == "ref":
            return [node["e"]], None, []
        sub = self.execute(node)
        return [r["e"] for r in sub["rows"]], sub["rows"], sub["notes"]

    def _window(self, node: dict):
        f, t = node["kw"].get("from"), node["kw"].get("to")
        if not f and not t:
            return None
        return {"s": f["start"] if f else None, "e": t["end"] if t else None,
                "ah": bool((f and f["era"] == "ah") or (t and t["era"] == "ah"))}

    def _time_tag(self, ent: dict, w: dict) -> str | None:
        dates = ent.get("dates") or []
        starts = [d["s"] for d in dates if d.get("s")]
        ends = [d["e"] for d in dates if d.get("e")]
        if not starts or not ends:
            return "undated"
        es, ee = min(starts), max(ends)
        within = (w["s"] is None or es >= w["s"]) and (w["e"] is None or ee <= w["e"])
        if within:
            return "within"
        overlaps = (w["e"] is None or es <= w["e"]) and (w["s"] is None or ee >= w["s"])
        return "overlaps" if overlaps else None

    def _time_notes(self, w, tags: dict, undated: int, undated_direct: int = 0) -> list:
        notes = []
        if w is None:
            return notes
        if w["ah"]:
            notes.append({"key": "note.time_ah"})
        n = sum(1 for v in tags.values() if v == "overlaps")
        if n:
            notes.append({"key": "note.time_overlaps", "n": n})
        if undated:
            notes.append({"key": "note.time_undated", "n": undated})
        if undated_direct:
            notes.append({"key": "note.time_undated_direct", "n": undated_direct})
        return notes

    def _left_out(self, n: int) -> list:
        return [{"key": "note.left_out", "n": n}] if n else []

    def _participation(self, targets: list[int], leader: bool):
        rows: dict = {}
        absent: list[int] = []
        left = 0
        for t in targets:
            for j in self.touch[t]:
                c = self.C[j]
                if c["o"] != t or c["k"] not in ("a", "p") or self.kind(c["s"]) not in AGENTS:
                    continue
                if not self.usable(c):
                    left += 1
                    continue
                if not self.positive(c):
                    absent.append(j)
                    continue
                if leader and not self.is_leader(c):
                    continue
                rows.setdefault(c["s"], []).append(j)
        return rows, sorted(set(absent)), left

    def op_participants(self, node: dict) -> dict:
        targets, searched, sub_notes = self._targets(node["args"][0])
        rows, absent, left = self._participation(targets, self._word(node, "as") == "leader")
        notes = sub_notes + self._left_out(left)
        if any(self.kind(t) == "story" for t in targets):
            notes.append({"key": "note.story_list"})
        extra = {"absent": absent}
        if searched is not None:
            extra["searched"] = searched
        return self._set("agents", rows, notes, **extra)

    def op_absent(self, node: dict) -> dict:
        targets, searched, sub_notes = self._targets(node["args"][0])
        _, absent, left = self._participation(targets, False)
        rows: dict = {}
        for j in absent:
            rows.setdefault(self.C[j]["s"], []).append(j)
        extra = {"searched": searched} if searched is not None else {}
        return self._set("agents", rows, sub_notes + self._left_out(left), **extra)

    def op_events(self, node: dict) -> dict:
        kw = node["kw"]
        at = kw["at"]["e"] if "at" in kw else None
        inv = kw["involving"]["e"] if "involving" in kw else None
        w = self._window(node)
        rows: dict = {}
        tags: dict = {}
        undated = 0
        for i, ent in enumerate(self.E):
            if ent["k"] != "event":
                continue
            ev: list[int] = []
            if at is not None:
                hits = [j for j in self.touch[i] if self.C[j]["s"] == i and self.C[j]["o"] == at
                        and self.C[j]["p"] in PLACE_LINKS and self.usable(self.C[j])]
                if not hits:
                    continue
                ev += hits
            if inv is not None:
                hits = [j for j in self.touch[i] if self.C[j]["s"] == inv and self.C[j]["o"] == i
                        and self.positive(self.C[j]) and self.usable(self.C[j])]
                if not hits:
                    continue
                ev += hits
            if w is not None:
                tag = self._time_tag(ent, w)
                if tag is None:
                    continue
                if tag == "undated":
                    undated += 1
                    continue
                tags[i] = tag
            rows[i] = ev
        return self._set("events", rows, self._time_notes(w, tags, undated), tags)

    def op_people(self, node: dict) -> dict:
        place = node["kw"]["at"]["e"]
        evs = self.op_events({"op": "events", "kw": {k: v for k, v in node["kw"].items()}})
        rows, absent, left = self._participation([r["e"] for r in evs["rows"]], False)
        w = self._window(node)
        undated_direct = 0
        for j in self.touch[place]:
            c = self.C[j]
            if c["o"] != place or c["k"] != "a" or c.get("c") != "spatial" or self.kind(c["s"]) not in AGENTS:
                continue
            if not self.usable(c):
                left += 1
                continue
            if w is not None:
                undated_direct += 1
                continue
            rows.setdefault(c["s"], []).append(j)
        tags = {r["e"]: r["tag"] for r in evs["rows"] if r.get("tag")}
        notes = self._time_notes(w, tags, 0, undated_direct)
        notes = [n for n in evs["notes"]] + [n for n in notes if n["key"] == "note.time_undated_direct"] + self._left_out(left)
        return self._set("agents", rows, notes, absent=absent, searched=evs["rows"])

    def op_stories(self, node: dict) -> dict:
        x = node["kw"]["involving"]["e"]
        rows: dict = {}
        for j in self.touch[x]:
            c = self.C[j]
            if c["s"] == x and c["k"] == "a" and self.kind(c["o"]) == "story" and self.usable(c):
                rows.setdefault(c["o"], []).append(j)
        return self._set("stories", rows, [{"key": "note.story_list"}] if rows else [])

    def op_relatives(self, node: dict) -> dict:
        p = node["args"][0]["e"]
        tie = self._word(node, "tie")
        rows: dict = {}
        for j in self.touch[p]:
            c = self.C[j]
            if c["k"] != "a" or c.get("c") != "kinship" or not self.usable(c):
                continue
            other = c["o"] if c["s"] == p else c["s"]
            if other == p:
                continue
            pred, subj = c["p"], c["s"] == p
            ok = (tie == "any"
                  or (tie == "parent" and ((not subj and pred in ("father_of", "mother_of")) or (subj and pred == "child_of")))
                  or (tie == "father" and not subj and pred == "father_of")
                  or (tie == "mother" and not subj and pred == "mother_of")
                  or (tie == "child" and ((subj and pred in ("father_of", "mother_of")) or (not subj and pred == "child_of")))
                  or (tie == "spouse" and pred == "spouse_of")
                  or (tie == "sibling" and pred == "sibling_of"))
            if ok:
                rows.setdefault(other, []).append(j)
        return self._set("agents", rows, [])

    def op_connected(self, node: dict) -> dict:
        x = node["args"][0]["e"]
        via = self._word(node, "via")
        rows: dict = {}
        if via in ("any", "ties"):
            for j in self.touch[x]:
                c = self.C[j]
                if c["k"] != "a" or not self.usable(c):
                    continue
                other = c["o"] if c["s"] == x else c["s"]
                if other != x and self.kind(other) in AGENTS:
                    rows.setdefault(other, []).append(j)
        notes = []
        if via in ("any", "events"):
            for j in self.touch[x]:
                c = self.C[j]
                if c["s"] != x or not self.positive(c) or self.kind(c["o"]) != "event" or not self.usable(c):
                    continue
                ev = c["o"]
                for j2 in self.touch[ev]:
                    c2 = self.C[j2]
                    if (c2["o"] != ev or c2["s"] == x or c2["k"] not in ("a", "p") or not self.positive(c2)
                            or self.kind(c2["s"]) not in AGENTS or not self.usable(c2)):
                        continue
                    rows.setdefault(c2["s"], []).extend([j, j2])
            notes.append({"key": "note.same_event"})
        return self._set("agents", rows, notes if rows else [])

    def op_between(self, node: dict) -> dict:
        x, y = node["args"][0]["e"], node["args"][1]["e"]
        targets = [y]
        links: dict = {}
        if self.kind(y) == "place":
            for j in self.touch[y]:
                c = self.C[j]
                if c["o"] == y and c["p"] in PLACE_LINKS and self.kind(c["s"]) == "event" and self.usable(c):
                    if c["s"] not in links:
                        targets.append(c["s"])
                    links.setdefault(c["s"], []).append(j)
        rows: dict = {}
        for t in targets:
            for j in self.touch[t]:
                c = self.C[j]
                if self.usable(c) and ((c["s"] == x and c["o"] == t) or (c["s"] == t and c["o"] == x)):
                    rows.setdefault(t, []).append(j)
            if t in rows and t in links:
                rows[t].extend(links[t])
        return {"type": "links", "rows": self._rows(rows), "notes": [], "a": x, "b": y}

    def op_path(self, node: dict) -> dict:
        x, y = node["args"][0]["e"], node["args"][1]["e"]
        mx = node["kw"]["max"]["n"] if "max" in node["kw"] else DEFAULTS[("path", "max")]
        prev: dict = {x: None}
        depth = {x: 0}
        queue = [x]
        k = 0
        found = False
        while k < len(queue) and not found:
            n = queue[k]
            k += 1
            if depth[n] >= mx:
                continue
            for j in self.touch[n]:
                c = self.C[j]
                if not self.usable(c):
                    continue
                m = c["o"] if c["s"] == n else c["s"]
                if m in prev:
                    continue
                prev[m] = (n, j)
                depth[m] = depth[n] + 1
                if m == y:
                    found = True
                    break
                queue.append(m)
        steps = []
        if found:
            m = y
            while prev[m] is not None:
                n, j = prev[m]
                steps.append({"a": n, "c": j, "b": m})
                m = n
            steps.reverse()
        return {"type": "path", "steps": steps, "a": x, "b": y, "max": mx,
                "notes": [{"key": "note.path"}] if steps else []}

    def op_when(self, node: dict) -> dict:
        x = node["args"][0]["e"]
        ent = self.E[x]
        field = "death" if ent["k"] == "person" else "dates"
        return {"type": "dates", "e": x, "field": field, "dates": ent.get(field) or [],
                "notes": [{"key": "note.fields"}]}

    def op_where(self, node: dict) -> dict:
        x = node["args"][0]["e"]
        rows: dict = {}
        for j in self.touch[x]:
            c = self.C[j]
            if c["s"] == x and c["p"] in PLACE_LINKS and self.kind(c["o"]) == "place" and self.usable(c):
                rows.setdefault(c["o"], []).append(j)
        return self._set("places", rows, [])

    def op_about(self, node: dict) -> dict:
        x = node["args"][0]["e"]
        counts = {"stories": 0, "events": 0, "places": 0, "groups": 0, "kinship": 0, "people": 0}
        status: dict = {}
        for j in self.touch[x]:
            c = self.C[j]
            other = c["o"] if c["s"] == x else c["s"]
            k = self.kind(other)
            if k == "story":
                key = "stories"
            elif k == "event":
                key = "events"
            elif k == "place":
                key = "places"
            elif k == "group":
                key = "groups"
            elif c.get("c") == "kinship":
                key = "kinship"
            else:
                key = "people"
            counts[key] += 1
            st = c.get("st") or "none"
            status[st] = status.get(st, 0) + 1
        return {"type": "about", "e": x, "counts": counts, "n": len(self.touch[x]),
                "status": dict(sorted(status.items())), "notes": []}

    def _setop(self, node: dict, mode: str) -> dict:
        a, b = self.execute(node["args"][0]), self.execute(node["args"][1])
        ra = {r["e"]: r for r in a["rows"]}
        rb = {r["e"]: r for r in b["rows"]}
        rows: dict = {}
        tags: dict = {}
        if mode == "both":
            keep = [e for e in ra if e in rb]
        elif mode == "either":
            keep = list(ra) + [e for e in rb if e not in ra]
        else:
            keep = [e for e in ra if e not in rb]
        for e in keep:
            claims = list(ra[e]["c"] if e in ra else []) + (list(rb[e]["c"]) if (e in rb and mode != "except") else [])
            rows[e] = claims
            tag = (ra.get(e) or rb.get(e)).get("tag")
            if tag:
                tags[e] = tag
        notes = []
        for n in a["notes"] + b["notes"]:
            if n not in notes:
                notes.append(n)
        if mode == "except":
            notes.append({"key": "note.except"})
        return self._set(a["of"], rows, notes, tags)

    def op_both(self, node: dict) -> dict:
        return self._setop(node, "both")

    def op_either(self, node: dict) -> dict:
        return self._setop(node, "either")

    def op_except(self, node: dict) -> dict:
        return self._setop(node, "except")

    def op_count(self, node: dict) -> dict:
        sub = self.execute(node["args"][0])
        return {"type": "count", "n": len(sub["rows"]), "set": sub, "notes": [{"key": "note.count"}]}

    def op_reviewed(self, node: dict) -> dict:
        sub = self.execute(node["args"][0])
        rows: dict = {}
        tags: dict = {}
        for r in sub["rows"]:
            keep = [j for j in r["c"] if self.C[j].get("st") == "accepted"]
            if keep:
                rows[r["e"]] = keep
                if r.get("tag"):
                    tags[r["e"]] = r["tag"]
        notes = [n for n in sub["notes"]] + [{"key": "note.reviewed"}]
        return self._set(sub["of"], rows, notes, tags)

    # ------------------------------------------------------------ plain language
    def plain(self, node: dict, T: dict) -> str:
        t = node["t"]
        if t == "ref":
            return self.E[node["e"]]["n"]
        if t == "year":
            return f"{node['n']} {node['era'].upper()}"
        if t == "num":
            return str(node["n"])
        if t == "word":
            return node["w"]
        op, a, kw = node["op"], node["args"], node["kw"]
        if op == "participants":
            key = "plain.participants_leader" if self._word(node, "as") == "leader" else "plain.participants"
            return fmt(T[key], target=self.plain(a[0], T))
        if op == "people":
            if "from" in kw or "to" in kw:
                return fmt(T["plain.people_range"], place=self.plain(kw["at"], T), range=self._range(kw, T))
            return fmt(T["plain.people"], place=self.plain(kw["at"], T))
        if op == "absent":
            return fmt(T["plain.absent"], target=self.plain(a[0], T))
        if op == "events":
            parts = []
            if "at" in kw:
                parts.append(fmt(T["plain.f_at"], place=self.plain(kw["at"], T)))
            if "involving" in kw:
                parts.append(fmt(T["plain.f_involving"], agent=self.plain(kw["involving"], T)))
            if "from" in kw or "to" in kw:
                parts.append(self._range(kw, T))
            return fmt(T["plain.events"], filters=T["plain.and"].join(parts))
        if op == "stories":
            return fmt(T["plain.stories"], agent=self.plain(kw["involving"], T))
        if op == "relatives":
            return fmt(T["plain.relatives_" + self._word(node, "tie")], person=self.plain(a[0], T))
        if op == "connected":
            return fmt(T["plain.connected_" + self._word(node, "via")], agent=self.plain(a[0], T))
        if op == "between":
            key = "plain.between_place" if self.kind(a[1]["e"]) == "place" else "plain.between"
            return fmt(T[key], a=self.plain(a[0], T), b=self.plain(a[1], T))
        if op == "path":
            mx = kw["max"]["n"] if "max" in kw else DEFAULTS[("path", "max")]
            return fmt(T["plain.path"], a=self.plain(a[0], T), b=self.plain(a[1], T), max=mx)
        if op == "when":
            key = "plain.when_death" if self.kind(a[0]["e"]) == "person" else "plain.when"
            return fmt(T[key], x=self.plain(a[0], T))
        if op == "where":
            return fmt(T["plain.where"], x=self.plain(a[0], T))
        if op == "about":
            return fmt(T["plain.about"], x=self.plain(a[0], T))
        if op in ("both", "either", "except"):
            return fmt(T["plain." + op], a=self.plain(a[0], T), b=self.plain(a[1], T))
        if op == "count":
            return fmt(T["plain.count"], set=self.plain(a[0], T))
        if op == "reviewed":
            return fmt(T["plain.reviewed"], set=self.plain(a[0], T))
        raise DslError("error.unknown_op", op=op)

    def _range(self, kw: dict, T: dict) -> str:
        f, t = kw.get("from"), kw.get("to")
        if f and t:
            return fmt(T["plain.range_between"], start=self.plain(f, T), end=self.plain(t, T))
        if f:
            return fmt(T["plain.range_from"], start=self.plain(f, T))
        return fmt(T["plain.range_to"], end=self.plain(t, T))

    # ------------------------------------------------------------ one call
    def run(self, text: str, T: dict) -> dict:
        """Parse, validate, execute. Returns {dsl, plain, result}; raises DslError."""
        typed = self.validate(parse(text))
        return {"dsl": self.text(typed), "plain": self.plain(typed, T), "result": self.execute(typed)}


def load_i18n(path: Path | None = None) -> dict:
    return json.loads((path or ASK / "i18n" / "en.json").read_text(encoding="utf-8"))


def main(argv=None) -> int:
    from ask import index
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__.strip().split("\n\n")[0])
        return 2
    eng = Engine(index.build())
    T = load_i18n()
    try:
        out = eng.run(argv[0], T)
    except DslError as e:
        print("invalid:", e.key, e.params)
        return 1
    print(out["dsl"])
    print(out["plain"])
    res = out["result"]
    for r in res.get("rows", []):
        print("  ", eng.E[r["e"]]["n"], r.get("tag", ""), [eng.C[j]["id"] for j in r["c"]])
    for s in res.get("steps", []):
        print("  ", eng.E[s["a"]]["n"], "--", eng.C[s["c"]]["p"], "--", eng.E[s["b"]]["n"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
