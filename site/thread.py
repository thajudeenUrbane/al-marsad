"""thread.json: what the "follow the thread" view (static/thread.js) walks.

The view is a port of the person thread in generation-1/wider-network.template.html, as a
progressive enhancement of the person and group pages: pick anyone who shares a moment
with the person and the thread moves on to them. Every page is complete without it.

Everything here is read from the model (the graph), and every visible string is resolved
from site/i18n/en.json at build time, so the script holds no data and no UI text:

    {"v": 1, "s": {strings},
     "k": ["person", "group", "place", "event", "story"],
     "e": [[kind, pid, name, when, sort, number], ...]   one row per entity, in index
          order (type, then A to Z), so a row's position is also its A-Z rank;
          when: the first recorded date as the pages show it; sort: the earliest
          recorded day (YYYY-MM-DD) or ""; number: a story's place in reading order
     "p": {entity: [place, ...]}                       where an event took place
     "c": [[subject, object, label, status, role, source, ai], ...]   one row per claim
          or link touching two entities; label/status/role/source index the tables
     "l": [labels], "t": [[status key, status text], ...], "o": [roles], "u": [sources]}
     (role and source 0 are "", none recorded; status key "none" is no status recorded)

No date is computed: "when" is the recorded date in the display form, and "sort" only
orders moments. Stories have no recorded date, so the view lists them in reading order
and says so; it never places them in time. The two strings needed before this file
arrives (loading, failed) are in the page itself (templates/thread_root.html).
"""
from __future__ import annotations

import re

import display
from model import KINDS, Claim, Site

FOCUS_KINDS = ("person", "group")
# the keys the script uses, written whole so the i18n tests can see them
STRINGS = ("thread.close", "thread.kicker", "thread.path", "thread.lead.one", "thread.lead.other",
           "thread.open_page", "thread.also", "thread.more", "thread.group_dated", "thread.group_stories",
           "thread.group_undated", "thread.group_people", "thread.group_places", "thread.none", "thread.note",
           "thread.title")


def _short_date(exts: list[dict], t) -> str:
    for x in exts:
        v = display.format_extent(x, t)
        if v["text"]:
            return v["text"]
    return ""


def _sort_day(exts: list[dict]) -> str:
    days = sorted(x["earliest"][:10] for x in exts if x.get("earliest"))
    return days[0] if days else ""


def _status(c: Claim, t) -> tuple[str, str]:
    word = display.t_opt(t, f"status.{c.status}", c.status) if c.status else t("status.none")
    return (c.status or "none", t("status.label", value=word))


def _role(c: Claim, t) -> str:
    if not c.role:
        return ""
    if c.kind == "participation":
        return t("claim.role", value=c.role.text)
    return display.honour(c.role.text)


def _source(c: Claim, t) -> str:
    if c.citation:
        return t("thread.source", value=c.citation)
    if c.agents:
        return t("claim.recorded_by", value="; ".join(a.label for a in c.agents))
    return ""


def build_thread(site: Site, t, lang: str = "en") -> dict:
    ents = [e for kind in KINDS for e in site.by_kind[kind]]
    index = {e.iri: i for i, e in enumerate(ents)}
    rows, places = [], {}
    for i, e in enumerate(ents):
        exts = (e.data.get("dates") or []) if e.kind in ("event", "story") else []
        row = [KINDS.index(e.kind), e.pid, e.name, _short_date(exts, t), _sort_day(exts),
               e.data.get("number") if e.kind == "story" else None]
        while row and row[-1] in ("", None):
            row.pop()
        rows.append(row)
        ps = sorted({index[p] for p in e.data.get("places") or [] if p in index}) if e.kind in ("event", "story") else []
        if ps:
            places[str(i)] = ps

    found, seen = set(), set()
    for e in ents:
        for c in site.claims.get(e.iri, []):
            if id(c) in seen:
                continue
            seen.add(id(c))
            if c.subject not in index or c.object not in index or c.subject == c.object:
                continue
            label = t(c.predicate) if c.predicate_is_key else c.predicate
            if lang == "ar" and not c.predicate_is_key and re.search("[A-Za-z]", label):
                label = f"\u2066{label}\u2069"   # recorded English inside an Arabic sentence
            found.add((index[c.subject], index[c.object], display.honour(label), _status(c, t),
                       _role(c, t), _source(c, t), 1 if c.ai_draft else 0))
    # tables sorted, so the file does not depend on the order the graph was read in
    tables = {"l": sorted({f[2] for f in found}), "t": sorted({f[3] for f in found}),
              "o": sorted({f[4] for f in found} | {""}), "u": sorted({f[5] for f in found} | {""})}
    pos = {k: {v: i for i, v in enumerate(vals)} for k, vals in tables.items()}
    claims = sorted([a, b, pos["l"][l], pos["t"][st], pos["o"][o], pos["u"][u], ai]
                    for a, b, l, st, o, u, ai in found)
    strings = {k.split(".", 1)[1]: t(k) for k in STRINGS}
    for cat in ("zero", "two", "few", "many"):   # the plural forms Arabic adds to one and other
        form = display.t_opt(t, f"thread.lead.{cat}", None)
        if form is not None:
            strings[f"lead.{cat}"] = form
    sc, cc = site.status_counts(), site.coverage_counts()
    if not sc.get("accepted") and not cc.get("reviewed") and not cc.get("verified"):
        strings["note"] = t("thread.unreviewed") + " " + strings["note"]
    if any(c[6] for c in claims):
        strings["note"] += " " + t("claims.ai_note")
    return {"v": 1, "s": strings, "k": list(KINDS), "e": rows, "p": places, "c": claims, **tables}
