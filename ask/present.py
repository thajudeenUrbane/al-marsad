"""Answer object -> HTML. Used for the answers built ahead of time (the pages that work
without JavaScript); ask/static/ask.js renders live answers with a port of this module,
and ask/tests/test_parity.py checks that both give the same HTML.

No visible word is written here: every string is an i18n key (ask/i18n/en.json) or
comes from the graph. Arabic script and the honorific sign are marked up with the
site's own rule (display.mark_arabic, imported).
"""
from __future__ import annotations

from ask.dsl import Engine, fmt
from ask.normalise import RULES
import display  # noqa: E402  (site/display.py, on the path through ask.normalise)

ROWS_SHOWN = RULES["limits"]["rows_shown"]
CLAIMS_SHOWN = RULES["limits"]["claims_shown"]


def esc(s) -> str:
    s = str(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#x27;"))


class Presenter:
    def __init__(self, engine: Engine, T: dict, base: str = "../", examples: list | None = None):
        self.eng = engine
        self.E = engine.E
        self.C = engine.C
        self.T = T
        self.base = base
        self.agents = engine.ix["agents"]
        self.examples = examples or []

    # ------------------------------------------------------------ text
    def h(self, s) -> str:
        """Plain text (data or an i18n string) -> HTML."""
        return display.mark_arabic(esc(s))

    def t(self, key: str, /, **kw) -> str:
        return fmt(self.T[key], **kw)

    def hk(self, key: str, /, **html_kw) -> str:
        """An i18n template whose values are already HTML."""
        return fmt(self.h(self.T[key]), **html_kw)

    def plural(self, key: str, n: int) -> str:
        return key + (".one" if n == 1 else ".other")

    def note_text(self, note: dict) -> str:
        n = note.get("n")
        key = note["key"] + (".other" if n is not None and n != 1 else ".one")
        return self.t(key, n=n) if n is not None else self.t(key)

    # ------------------------------------------------------------ pieces
    def href(self, i: int) -> str:
        return self.base + self.E[i]["r"] + "/"

    def link(self, i: int) -> str:
        return '<a href="' + esc(self.href(i)) + '">' + self.h(self.E[i]["n"]) + "</a>"

    def kind(self, i: int) -> str:
        return '<span class="kind">(' + self.h(self.T["kind." + self.E[i]["k"]]) + ")</span>"

    def status(self, st) -> str:
        word = self.T.get("status." + (st or "none"), st or "")
        cls = "status-" + esc(st or "none")
        return '<span class="status ' + cls + '">' + self.h(self.t("status.label", value=word)) + "</span>"

    def source(self, c: dict) -> str:
        label = self.h(self.T["claim.source"])
        if c.get("cit"):
            cit = self.h(c["cit"])
            if c.get("sty") is not None:
                cit = '<a href="' + esc(self.href(c["sty"])) + '">' + cit + "</a>"
            return '<span class="source">' + label + " " + cit + "</span>"
        if c.get("src"):
            return '<span class="source">' + label + " " + self.h(c["src"]) + "</span>"
        if c.get("by") is not None:
            return '<span class="source">' + self.h(self.t("claim.recorded_by", value=self.agents[c["by"]])) + "</span>"
        return '<span class="source not-recorded">' + label + " " + self.h(self.T["claim.not_recorded"]) + "</span>"

    def claim(self, j: int, cls: str = "claim") -> str:
        c = self.C[j]
        if c["k"] == "a":
            pred = c.get("pl") or c["p"]
        else:
            pred = self.T["claim." + c["p"]]
        out = ['<li class="' + cls + '"><p class="claim-text">', self.link(c["s"]), ' <span class="rel">', self.h(pred),
               "</span> ", self.link(c["o"]), "</p>"]
        if c.get("role"):
            text = self.t("claim.role", value=c["role"]) if c["k"] == "p" else c["role"]
            out.append('<p class="claim-role">' + self.h(text) + "</p>")
        if c.get("q"):
            out.append('<p class="claim-marker">' + self.h(self.t("claim.marker", value="; ".join(c["q"]))) + "</p>")
        sep = ' <span class="sep" aria-hidden="true">&middot;</span> '
        meta = self.status(c.get("st")) + sep + self.source(c)
        if c.get("ai"):
            meta += sep + '<span class="ai-note">' + self.h(self.T["claim.ai"]) + "</span>"
        out.append('<p class="claim-meta">' + meta + "</p></li>")
        return "".join(out)

    def claims(self, js: list[int]) -> str:
        if not js:
            return ""
        return '<ul class="claim-list">' + "".join(self.claim(j) for j in js) + "</ul>"

    def claims_folded(self, js: list[int]) -> str:
        """A row's claims: the first few shown, the rest one tap below."""
        if len(js) <= CLAIMS_SHOWN:
            return self.claims(js)
        rest = js[CLAIMS_SHOWN:]
        return (self.claims(js[:CLAIMS_SHOWN]) + '<details class="more-claims"><summary>'
                + self.h(self.t(self.plural("answer.more_claims", len(rest)), n=len(rest))) + "</summary>"
                + self.claims(rest) + "</details>")

    def row(self, r: dict) -> str:
        i = r["e"]
        head = self.link(i) + " " + self.kind(i)
        dates = self.E[i].get("dates") or []
        if dates and dates[0].get("t"):
            head += ' <span class="row-date">' + self.h(dates[0]["t"]) + "</span>"
        if r.get("tag") == "overlaps":
            head += ' <span class="tag">' + self.h(self.T["answer.overlaps"]) + "</span>"
        return '<li class="row"><p class="row-head">' + head + "</p>" + self.claims_folded(r["c"]) + "</li>"

    def rows(self, rows: list[dict]) -> str:
        shown = rows[:ROWS_SHOWN]
        out = '<ol class="rows">' + "".join(self.row(r) for r in shown) + "</ol>"
        if len(rows) > len(shown):
            out += '<p class="note">' + self.h(self.t("answer.more", shown=len(shown), n=len(rows))) + "</p>"
        return out

    def status_summary(self, js: list[int]) -> str:
        ids = sorted(set(js))
        if not ids:
            return ""
        acc = sum(1 for j in ids if self.C[j].get("st") == "accepted")
        if acc == 0:
            text = self.T["answer.status_none"]
        elif acc == len(ids):
            text = self.t("answer.status_all", n=len(ids))
        else:
            text = self.t("answer.status_some", a=acc, n=len(ids))
        return '<p class="status-summary">' + self.h(text) + "</p>"

    def why_empty(self, refs: list[int]) -> str:
        cnt = self.eng.ix["counts"]
        out = "<p>" + self.h(self.t("answer.empty_why", person=cnt["person"], event=cnt["event"],
                                    place=cnt["place"], story=cnt["story"])) + "</p>"
        gaps = []
        for i in refs:
            for g in self.E[i].get("gaps", []):
                if g not in gaps:
                    gaps.append(g)
        if gaps:
            out += ('<p>' + self.h(self.T["answer.gaps"]) + '</p><ul class="gaps">'
                    + "".join("<li>" + self.h(g) + "</li>" for g in gaps) + "</ul>")
        return out

    def notes(self, notes: list[dict]) -> str:
        if not notes:
            return ""
        return ('<div class="notes"><h3>' + self.h(self.T["answer.notes"]) + "</h3><ul>"
                + "".join("<li>" + self.h(self.note_text(n)) + "</li>" for n in notes) + "</ul></div>")

    def asked(self, q: str) -> str:
        return '<p class="asked"><span class="k">' + self.h(self.T["answer.question"]) + "</span> " + self.h(q) + "</p>"

    def open(self, outcome: str, heading_key: str) -> str:
        return ('<section class="answer outcome-' + outcome + '" aria-labelledby="answer-h">'
                '<h2 id="answer-h" tabindex="-1">' + self.h(self.T[heading_key]) + "</h2>")

    def choice(self, i: int, dsl) -> str:
        attr = ' data-dsl="' + esc(dsl) + '"' if dsl else ""
        return ('<li><a href="' + esc(self.href(i)) + '"' + attr + ">" + self.h(self.E[i]["n"]) + "</a> "
                + self.kind(i) + "</li>")

    # ------------------------------------------------------------ results
    def set_body(self, res: dict, refs: list[int]) -> str:
        rows = res["rows"]
        used = [j for r in rows for j in r["c"]] + res.get("absent", []) + [j for r in res.get("searched") or [] for j in r["c"]]
        out = []
        if rows:
            out.append('<p class="lead">' + self.h(self.t(self.plural("answer.lead." + res["of"], len(rows)), n=len(rows))) + "</p>")
            out.append(self.status_summary(used))
        else:
            out.append('<p class="lead empty">' + self.h(self.T["answer.empty"]) + "</p>" + self.why_empty(refs))
        if res.get("searched"):
            out.append('<details class="searched-events"><summary>' + self.h(self.T["answer.searched_events"])
                       + ' <span class="count">(' + str(len(res["searched"])) + ")</span></summary>"
                       + self.rows(res["searched"]) + "</details>")
        if rows:
            out.append(self.rows(rows))
        if res.get("absent"):
            out.append('<h3 class="absent-h">' + self.h(self.T["answer.absent"]) + "</h3>" + self.claims(res["absent"]))
        return "".join(out)

    def body(self, ans: dict) -> str:
        res = ans["result"]
        refs = ans.get("refs", [])
        ty = res["type"]
        if ty == "set":
            return self.set_body(res, refs)
        if ty == "count":
            return self.set_body(res["set"], refs)
        if ty == "path":
            if not res["steps"]:
                return ('<p class="lead empty">' + self.h(self.t("answer.path_none", max=res["max"], a=self.E[res["a"]]["n"],
                                                                  b=self.E[res["b"]]["n"])) + "</p>" + self.why_empty(refs))
            n = len(res["steps"])
            lead = self.hk(self.plural("answer.path_lead", n), a=self.link(res["a"]), b=self.link(res["b"]), n=str(n))
            js = [s["c"] for s in res["steps"]]
            return ('<p class="lead">' + lead + "</p>" + self.status_summary(js)
                    + '<ol class="path claim-list">' + "".join(self.claim(j, "claim step") for j in js) + "</ol>")
        if ty == "links":
            rows = res["rows"]
            a, b = self.link(res["a"]), self.link(res["b"])
            if not rows:
                return '<p class="lead empty">' + self.hk("answer.links_none", a=a, b=b) + "</p>" + self.why_empty(refs)
            used = [j for r in rows for j in r["c"]]
            n = len(set(j for j in used if res["a"] in (self.C[j]["s"], self.C[j]["o"])))
            return ('<p class="lead">' + self.hk(self.plural("answer.links_lead", n), a=a, b=b, n=str(n)) + "</p>"
                    + self.status_summary(used) + self.rows(rows))
        if ty == "dates":
            x = self.link(res["e"])
            if not res["dates"]:
                return '<p class="lead empty">' + self.hk("answer.dates_none", x=x) + "</p>" + self.why_empty(refs)
            items = []
            for d in res["dates"]:
                item = "<li><p>" + self.h(d["t"] or "") + "</p>"
                item += "".join('<p class="note">' + self.h(n) + "</p>" for n in d.get("notes", []))
                items.append(item + "</li>")
            by = self.E[res["e"]].get("by")
            meta = '<span class="status status-none">' + self.h(self.T["answer.field_status"]) + "</span>"
            if by is not None:
                meta += ' <span class="sep" aria-hidden="true">&middot;</span> <span class="source">' + self.h(
                    self.t("answer.recorded_by", by=self.agents[by])) + "</span>"
            return ('<p class="lead">' + self.hk("answer.dates_lead", x=x) + '</p><ul class="dates">' + "".join(items)
                    + '</ul><p class="claim-meta">' + meta + "</p>")
        if ty == "about":
            i = res["e"]
            x = self.link(i)
            if not res["n"]:
                lead = '<p class="lead">' + self.hk("answer.about_none", x=x) + "</p>"
            else:
                lead = '<p class="lead">' + self.hk(self.plural("answer.about_lead", res["n"]), x=x, n=str(res["n"])) + "</p>"
            items = "".join("<li>" + self.h(self.t(self.plural("about." + k, v), n=v)) + "</li>"
                            for k, v in res["counts"].items() if v)
            out = lead + ('<ul class="plain counts">' + items + "</ul>" if items else "")
            st = res["status"]
            total = sum(st.values())
            if total:
                acc = st.get("accepted", 0)
                if acc == 0:
                    text = self.T["answer.status_none"]
                elif acc == total:
                    text = self.t("answer.status_all", n=total)
                else:
                    text = self.t("answer.status_some", a=acc, n=total)
                out += '<p class="status-summary">' + self.h(text) + "</p>"
            cov = self.E[i].get("cov")
            if cov:
                out += '<p class="coverage">' + self.h(self.t("answer.coverage", value=cov)) + "</p>"
            out += '<p><a href="' + esc(self.href(i)) + '">' + self.h(self.T["answer.open_page"]) + "</a></p>"
            return out
        return ""

    def alts(self, alts: list[dict]) -> str:
        out = []
        for a in alts:
            out.append('<div class="alts"><p>' + self.h(self.t("answer.alts", mention=a["mention"])) + '</p><ul class="plain">'
                       + "".join(self.choice(o["e"], o["dsl"]) for o in a["options"]) + "</ul></div>")
        return "".join(out)

    # ------------------------------------------------------------ whole answers
    def render(self, ans: dict) -> str:
        oc = ans["outcome"]
        q = ans.get("q", "")
        if oc == "answer":
            res = ans["result"]
            out = [self.open("answer", "answer.heading"), self.asked(q),
                   '<p class="searched">' + self.h(self.t("answer.searched", plain=ans["plain"])) + "</p>",
                   '<details class="query"><summary>' + self.h(self.T["answer.query"]) + '</summary><p><code class="dsl">'
                   + esc(ans["dsl"]) + '</code></p><p class="note">' + self.h(self.T["answer.query_note"]) + "</p></details>",
                   self.alts(ans.get("alts", [])), self.body(ans),
                   self.notes(ans.get("notes", []) + res.get("notes", []) + (res.get("set") or {}).get("notes", [])),
                   '<p class="composed">' + self.h(self.T["answer.composed"]) + " "
                   + self.h(self.t("answer.version", v=ans["version"])) + "</p></section>"]
            return "".join(out)
        if oc == "refusal":
            cls = ans["refusal"]
            return (self.open("refusal", "refusal.heading") + self.asked(q)
                    + '<p class="refusal-reason">' + self.h(self.T["refusal." + cls + ".reason"]) + "</p>"
                    + "<p>" + self.h(self.T["refusal." + cls + ".offer"]) + "</p></section>")
        if oc == "unsupported":
            ex = "".join('<li><a href="' + esc(self.base + "ask/q/" + slug + "/") + '">' + self.h(text) + "</a></li>"
                         for text, slug in self.examples)
            return (self.open("unsupported", "unsupported.heading") + self.asked(q)
                    + "<p>" + self.h(self.T["unsupported." + ans["reason"]]) + "</p>"
                    + ("<p>" + self.h(self.T["unsupported.examples"]) + '</p><ul class="plain examples">' + ex + "</ul>" if ex else "")
                    + "</section>")
        if oc == "ambiguous":
            more = ('<p class="note">' + self.h(self.T["ambiguous.more"]) + "</p>") if ans["n"] > len(ans["options"]) else ""
            return (self.open("ambiguous", "ambiguous.heading") + self.asked(q)
                    + "<p>" + self.h(self.t("ambiguous.lead", mention=ans["mention"], n=ans["n"])) + "</p>"
                    + '<ul class="plain choices">' + "".join(self.choice(o["e"], o["dsl"]) for o in ans["options"]) + "</ul>"
                    + more + "</section>")
        if oc == "not_found":
            kinds = self.T["kind.or"].join(self.T["kind." + k] for k in ans["kinds"])
            others = ""
            if ans.get("others"):
                others = ("<p>" + self.h(self.T["notfound.others"]) + '</p><ul class="plain">'
                          + "".join(self.choice(i, None) for i in ans["others"]) + "</ul>")
            gaps = self.eng.ix.get("gaps", [])
            gap_html = ""
            if gaps:
                gap_html = ('<details class="gaps"><summary>' + self.h(self.T["answer.gaps"]) + "</summary><ul>"
                            + "".join("<li>" + self.h(g) + "</li>" for g in gaps) + "</ul></details>")
            return (self.open("not-found", "notfound.heading") + self.asked(q)
                    + "<p>" + self.h(self.t("notfound.lead", kinds=kinds, mention=ans["mention"])) + "</p>"
                    + others + self.why_empty([]) + gap_html + "</section>")
        if oc == "invalid":
            err = ans["error"]
            params = dict(err["params"])
            if err["key"] == "error.type" and "want" in params:
                params["want"] = self.T["want." + params["want"]]
            return (self.open("invalid", "invalid.heading") + self.asked(q)
                    + '<p><code class="dsl">' + esc(ans["dsl"]) + "</code></p>"
                    + '<p class="error">' + self.h(self.t(err["key"], **params)) + "</p></section>")
        if oc == "too_long":
            return (self.open("empty", "unsupported.heading")
                    + "<p>" + self.h(self.t("toolong.lead", max=RULES["limits"]["question_max"])) + "</p></section>")
        return self.open("empty", "unsupported.heading") + "<p>" + self.h(self.T["empty.lead"]) + "</p></section>"
