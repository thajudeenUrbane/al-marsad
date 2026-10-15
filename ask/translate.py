"""Plain question -> typed query, deterministically, and the refusal classifier.

    .venv/bin/python -m ask.translate "Who was at both Badr and Uhud?"

The pipeline, for every question (answer() below):
  1. Empty or over-long questions stop here. A question that is already a query
     (it starts with an operation name and a bracket) is run as it stands.
  2. The question is folded and lower-cased (ask/normalise.py text_key).
  3. The refusal classifier runs before anything else (docs/07 section 5, docs/06
     section 10): rulings, interpretation of scripture, grading, writing reports,
     depiction, ranking people, speculation, judgement of persons. A refused question
     is never translated, linked or run.
  4. Translators run in order; the first that returns a result wins. Today there is
     one, RuleTranslator: a fixed list of question shapes (ask/rules.json "shapes"),
     each a set of patterns and a query template with slots. Names in the slots are
     linked to entities with spelling-tolerant matching (ask/normalise.py); an
     ambiguous name is put back to the visitor, never resolved silently.
  5. The query text is parsed and validated like any typed-in query, run, and
     rendered back in plain words (ask/dsl.py).

A model-backed translator can be added later behind the Translator interface below;
it is not implemented, and nothing here calls a model.
"""
from __future__ import annotations

import re
import sys
from typing import Protocol

from ask.dsl import LIMITS, DslError, Engine, load_i18n, parse
from ask.normalise import RULES, name_tokens, score, text_key

_RX: dict[str, re.Pattern] = {}


def rx(pattern: str) -> re.Pattern:
    if pattern not in _RX:
        _RX[pattern] = re.compile(pattern)
    return _RX[pattern]


def trim(s: str) -> str:
    """Strip leading and trailing white space, by the shared class in rules.json."""
    sp = RULES["normalise"]["spaces"]
    return rx("^(?:" + sp + ")|(?:" + sp + ")$").sub("", s)


def strip_trailing(q: str) -> str:
    return rx(RULES["cleanup"]["trailing"]).sub("", q)


def strip_fillers(q: str) -> str:
    return rx(RULES["cleanup"]["fillers"]).sub("", q).strip(" ")


def classify_refusal(q: str) -> str | None:
    """The refusal class of a folded, lower-cased question, or None."""
    padded = " " + q + " "
    for cls in RULES["refusals"]:
        if cls.get("unless") and rx(cls["unless"]).search(padded):
            continue
        for pat in cls["patterns"]:
            if rx(pat).search(padded):
                return cls["class"]
    return None


class Translator(Protocol):
    """Turns a folded, refusal-checked question into one of:
      {"outcome": "query", "dsl": text, "notes": [...], "alts": [...]}
      {"outcome": "not_found" | "ambiguous" | "unsupported", ...}
      None, to pass the question to the next translator.
    Whatever DSL it returns is parsed and validated like any typed-in query, so it can
    only ask for what the closed set of operations allows. It never writes an answer."""
    name: str

    def translate(self, q: str) -> dict | None: ...


class ModelTranslator:
    """Placeholder for a later model-backed translator (docs/13 D4: no live AI for every
    visitor until funding allows; answers then cached and shared). Not implemented and
    never registered. Its contract, when it is built: it runs only after
    classify_refusal; it returns query text, never prose; a query that fails validation
    falls back to the next translator; the question, the query, the graph version and
    the translator's name and version are kept as the audit record (docs/07 section 2,
    step 9). Measure it against ask/golden/questions.jsonl before use."""
    name = "model"

    def translate(self, q: str) -> dict | None:
        raise NotImplementedError("no model-backed translator in this release")


class Linker:
    """Mention -> entity, spelling-tolerant (ask/normalise.py score)."""

    def __init__(self, engine: Engine):
        self.E = engine.E
        self.L = RULES["linking"]

    def scored(self, mention: str) -> list[tuple[int, int]]:
        m = name_tokens(mention)
        out = []
        if not m:
            return out
        for i, e in enumerate(self.E):
            best = 0
            for k in e["keys"]:
                s = score(m, k)
                if s > best:
                    best = s
            if best >= self.L["min_score"]:
                out.append((best, i))
        out.sort(key=lambda x: (-x[0], x[1]))
        return out

    def link(self, mention: str, kinds: list[str], min_score: int = 1) -> dict:
        allc = self.scored(mention)
        inkind = [(s, i) for s, i in allc if self.E[i]["k"] in kinds]
        if not inkind or inkind[0][0] < min_score:
            others = [i for s, i in allc if s >= 2][: self.L["max_alternatives"]]
            return {"status": "below" if min_score > 1 else "none", "others": others}
        best = inkind[0][0]
        top = [i for s, i in inkind if s == best]
        for k in kinds:
            tk = [i for i in top if self.E[i]["k"] == k]
            if tk:
                top = tk
                break
        if len(top) > 1:
            return {"status": "ambiguous", "cands": top[: self.L["max_candidates"]], "n": len(top)}
        # other matches worth offering: another kind of entry (the story of an event, the
        # event at a place), or the same kind matching almost as well
        chosen = top[0]
        alts = [i for s, i in inkind if i != chosen and s >= self.L["alternatives_min_score"]
                and (self.E[i]["k"] != self.E[chosen]["k"] or s >= best - 1)]
        return {"status": "ok", "e": chosen, "score": best, "alts": alts[: self.L["max_alternatives"]]}


class Unsupported(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class RuleTranslator:
    """The deterministic translator: question shapes from ask/rules.json."""
    name = "rules"

    def __init__(self, engine: Engine):
        self.engine = engine
        self.E = engine.E
        self.linker = Linker(engine)

    # ------------------------------------------------------------ time and status
    def _era(self, e: str | None) -> str | None:
        if not e:
            return None
        return {"ad": "ce", "bce": "bh"}.get(e, e)

    def time_window(self, q: str):
        T = RULES["time"]
        m = rx(T["range"]).search(q)
        if m:
            rest, y1, e1, y2, e2 = m.group(1), int(m.group(2)), m.group(3), int(m.group(4)), m.group(5)
        else:
            m = rx(T["single"]).search(q)
            if m:
                rest, y1, e1 = m.group(1), int(m.group(2)), m.group(3)
                y2, e2 = y1, e1
            else:
                m = rx(T["single_bare"]).search(q)
                if not m:
                    return q, None, []
                rest, y1, e1 = m.group(1), int(m.group(2)), None
                y2, e2 = y1, None
        e1, e2 = self._era(e1), self._era(e2)
        if e1 == "bh" or e2 == "bh":
            raise Unsupported("time_bh")
        notes = []
        a, b = e1 or e2, e2 or e1
        if a is None:
            if y1 <= T["bare_ah_max"] and y2 <= T["bare_ah_max"]:
                a = b = "ah"
                notes.append({"key": "note.time_assumed_ah"})
            elif y1 >= T["min_ce"] and y2 >= T["min_ce"]:
                a = b = "ce"
            else:
                raise Unsupported("time_era")
        return rest.strip(" "), {"from": [y1, a], "to": [y2, b]}, notes

    def _time_text(self, w) -> str:
        if not w:
            return ""
        return f", from: {w['from'][0]} {w['from'][1].upper()}, to: {w['to'][0]} {w['to'][1].upper()}"

    # ------------------------------------------------------------ building the query
    def expand(self, stype: str, e: int) -> str:
        ref = self.engine.ref_text(e)
        if stype == "presence":
            return f"people(at: {ref}{{time}})" if self.E[e]["k"] == "place" else f"participants({ref})"
        if stype == "happening_set" and self.E[e]["k"] == "place":
            return f"events(at: {ref}{{time}})"
        return ref

    def build(self, shape: dict, chosen: dict, w, reviewed: bool) -> str:
        text = shape["dsl"]
        for num, (stype, e) in chosen.items():
            text = text.replace("{" + num + "}", self.expand(stype, e))
        used_time = "{time}" in text
        if w and not used_time:
            raise Unsupported("time_needs_place")
        text = text.replace("{time}", self._time_text(w)).replace("(, ", "(")
        if reviewed:
            text = "count(reviewed(" + text[6:] + ")" if text.startswith("count(") else "reviewed(" + text + ")"
            try:
                self.engine.validate(parse(text))
            except DslError:
                raise Unsupported("reviewed_needs_list")
        return text

    # ------------------------------------------------------------ shapes
    def fill(self, shape: dict, m: re.Match, w, reviewed: bool):
        slots = []
        if shape.get("pair"):
            whole = m.group(1)
            found = None
            for hit in re.finditer(" and ", whole):
                left = whole[: hit.start()].strip(" ")
                right = re.sub("^(?:at|in) ", "", whole[hit.end():].strip(" "))
                kinds = RULES["slots"]["presence"]["kinds"]
                a = self.linker.link(left, kinds, RULES["linking"]["pair_min_score"])
                b = self.linker.link(right, kinds, RULES["linking"]["pair_min_score"])
                if a["status"] == "ok" and b["status"] == "ok" and a["e"] != b["e"]:
                    found = (a, b, left, right)
                    break
            if not found:
                return None
            a, b, left, right = found
            slots = [("1", "presence", a, left), ("2", "presence", b, right)]
        else:
            for num in sorted(shape["slots"]):
                stype = shape["slots"][num]
                mention = (m.group(int(num)) or "").strip(" ")
                res = self.linker.link(mention, RULES["slots"][stype]["kinds"], shape.get("min_score", 1))
                if res["status"] == "below":
                    return None
                slots.append((num, stype, res, mention))
        notes = [{"key": "note." + shape["note"]}] if shape.get("note") else []
        for num, stype, res, mention in slots:
            if res["status"] == "none":
                return {"outcome": "not_found", "mention": mention,
                        "kinds": RULES["slots"][stype]["kinds"], "others": res["others"]}
        chosen = {num: (stype, res["e"]) for num, stype, res, mention in slots if res["status"] == "ok"}
        for num, stype, res, mention in slots:
            if res["status"] == "ambiguous":
                options = []
                for c in res["cands"]:
                    dsl = None
                    if len(chosen) == len(slots) - 1:
                        try:
                            dsl = self.build(shape, {**chosen, num: (stype, c)}, w, reviewed)
                        except Unsupported:
                            dsl = None
                    options.append({"e": c, "dsl": dsl})
                return {"outcome": "ambiguous", "mention": mention, "options": options, "n": res["n"]}
        dsl = self.build(shape, chosen, w, reviewed)
        alts = []
        for num, stype, res, mention in slots:
            opts = []
            for a in res.get("alts", []):
                try:
                    opts.append({"e": a, "dsl": self.build(shape, {**chosen, num: (stype, a)}, w, reviewed)})
                except Unsupported:
                    continue
            if opts:
                alts.append({"mention": mention, "options": opts})
        return {"outcome": "query", "dsl": dsl, "notes": notes, "alts": alts}

    def translate(self, q: str) -> dict | None:
        try:
            reviewed = False
            for pat in RULES["status_suffix"]:
                m = rx(pat).search(q)
                if m:
                    q, reviewed = m.group(1).strip(" "), True
                    break
            q, w, notes = self.time_window(q)
            for shape in RULES["shapes"]:
                if shape.get("needs_time") and w is None:
                    continue
                for pat in shape["patterns"]:
                    m = rx(pat).search(q)
                    if not m:
                        continue
                    res = self.fill(shape, m, w, reviewed)
                    if res is None:
                        continue
                    if res["outcome"] == "query":
                        res["notes"] = notes + res["notes"]
                    return res
            return {"outcome": "unsupported", "reason": "generic"}
        except Unsupported as u:
            return {"outcome": "unsupported", "reason": u.reason}


def refs_of(node: dict) -> list[int]:
    out: list[int] = []

    def walk(n):
        if n["t"] == "ref" and "e" in n:
            if n["e"] not in out:
                out.append(n["e"])
        elif n["t"] == "op":
            for a in n["args"]:
                walk(a)
            for v in n["kw"].values():
                walk(v)
    walk(node)
    return out


def run_query(text: str, engine: Engine, T: dict, out: dict, notes=(), alts=()) -> dict:
    try:
        typed = engine.validate(parse(text))
    except DslError as e:
        out.update({"outcome": "invalid", "dsl": text, "error": e.as_dict()})
        return out
    out.update({"outcome": "answer", "dsl": engine.text(typed), "plain": engine.plain(typed, T),
                "result": engine.execute(typed), "refs": refs_of(typed),
                "notes": list(notes), "alts": list(alts)})
    return out


def answer(question: str, engine: Engine, T: dict, translators: list | None = None) -> dict:
    """The whole pipeline for one question. Returns a plain dict (see ask/DSL.md, "The
    answer object"); ask/present.py turns it into HTML."""
    raw = trim(question or "")
    out: dict = {"q": raw, "version": engine.ix["version"]}
    if not raw:
        out["outcome"] = "empty"
        return out
    if len(raw) > LIMITS["question_max"]:
        out["outcome"] = "too_long"
        return out
    if rx(RULES["dsl_direct"]).search(raw.lower()):
        out["direct"] = 1
        return run_query(raw, engine, T, out)
    q = strip_trailing(text_key(raw))
    cls = classify_refusal(q)
    if cls:
        out.update({"outcome": "refusal", "refusal": cls})
        return out
    q = strip_fillers(q)
    chain = translators if translators is not None else [RuleTranslator(engine)]
    res = None
    for k, tr in enumerate(chain):
        res = tr.translate(q)
        if res is None:
            continue
        if res["outcome"] == "query" and k < len(chain) - 1:
            try:
                engine.validate(parse(res["dsl"]))
            except DslError:
                continue
        break
    if res is None:
        res = {"outcome": "unsupported", "reason": "generic"}
    if res["outcome"] != "query":
        out.update(res)
        return out
    return run_query(res["dsl"], engine, T, out, res["notes"], res["alts"])


def main(argv=None) -> int:
    import json
    from ask import index
    argv = sys.argv[1:] if argv is None else argv
    eng = Engine(index.build())
    T = load_i18n()
    for q in argv:
        a = answer(q, eng, T)
        brief = {k: v for k, v in a.items() if k not in ("result",)}
        print(json.dumps(brief, ensure_ascii=False))
        res = a.get("result") or {}
        for r in res.get("rows", [])[:40]:
            print("   ", eng.E[r["e"]]["l"], r.get("tag", ""), len(r["c"]))
        for s in res.get("steps", []):
            print("   ", eng.E[s["a"]]["l"], "--", eng.C[s["c"]]["p"], "--", eng.E[s["b"]]["l"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
