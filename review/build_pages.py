#!/usr/bin/env python3
"""
Build the scholars' review pages (slice 3b) from the review queue.

    .venv/bin/python review/build_pages.py                  # rebuild review/dist/queue.json, then the pages
    .venv/bin/python review/build_pages.py --queue FILE     # pages from an existing queue file (no rebuild)
    .venv/bin/python review/build_pages.py --scope "source:stories-50"   # only what this roster scope covers

Writes into review/dist/ (gitignored; --out DIR elsewhere): index.html (every batch), one
page per batch (<batch>.html) and sw.js (keeps visited pages for offline use when the
pages are served over https or localhost).

Each page is one self-contained file: its style and script are inlined, it loads nothing
from anywhere else, so it can be sent as a file or served as a link. The page keeps the
reviewer's decisions on the device (localStorage) and "Send my decisions" makes one
decision file in the format review/import_decisions.py reads (docs/handover/slice-3a.md).
Nothing here reads the roster or writes a name: a reviewer enters their own opaque ID.

Every visible string comes from review/i18n/en.json (keys in the templates as [[key]]);
every other word on a page comes from the queue, which comes from the graph. The output
is deterministic: no dates or times are written.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from string import Template

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

REVIEW = Path(__file__).resolve().parent
DIST = REVIEW / "dist"
TEMPLATES = REVIEW / "templates"
STATIC = REVIEW / "static"
STRINGS = json.loads((REVIEW / "i18n" / "en.json").read_text(encoding="utf-8"))

URL_LICENSING = "https://github.com/thajudeenUrbane/al-marsad/blob/main/LICENSING.md"
URL_CC_BY_SA = "https://creativecommons.org/licenses/by-sa/4.0/"
URL_AGPL = "https://www.gnu.org/licenses/agpl-3.0.html"
KINDS = ("story", "person", "file", "identity")
ENTITY_KINDS = ("person", "place", "event", "group")
SEP = " · "

esc = html.escape


# ---------------------------------------------------------------------------
# strings and templates
# ---------------------------------------------------------------------------

def t(key: str, **kw) -> str:
    """The string for key, escaped; keyword values are escaped here unless already HTML (Raw)."""
    s = esc(STRINGS[key], quote=False)  # a missing key is a build error on purpose
    return s.format(**{k: v if isinstance(v, Raw) else esc(str(v), quote=False) for k, v in kw.items()}) if kw else s


def tn(key: str, n: int, **kw) -> str:
    return t(f"{key}.{'one' if n == 1 else 'other'}", n=n, **kw)


class Raw(str):
    """Text that is already HTML."""


_TPL: dict[str, str] = {}


def tpl(name: str, **values) -> str:
    if name not in _TPL:
        src = (TEMPLATES / f"{name}.html").read_text(encoding="utf-8")
        _TPL[name] = re.sub(r"\[\[([a-z0-9_.]+)\]\]", lambda m: t(m.group(1)), src)
    return Template(_TPL[name]).substitute(values).rstrip("\n")


def ar(text: str, tag: str = "span") -> str:
    return f'<{tag} lang="ar" dir="rtl">{esc(text)}</{tag}>'


def page_file(batch_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", batch_id) + ".html"


def js_keys(js: str) -> list[str]:
    """The i18n keys review.js uses: every string literal that is a key, and key.one and key.other
    for tn("key", n)."""
    keys = {s for s in re.findall(r'"([a-z0-9_.]+)"', js) if s in STRINGS}
    for base in re.findall(r'\btn\("([a-z0-9_.]+)"', js):
        keys |= {f"{base}.one", f"{base}.other"}
    return sorted(keys)


def inline_css() -> str:
    css = (STATIC / "review.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return re.sub(r"\n\s*\n+", "\n", css).strip()


def inline_js() -> tuple[str, str]:
    js = (STATIC / "review.js").read_text(encoding="utf-8")  # a test checks it never closes its own script tag
    strings = {k: STRINGS[k] for k in js_keys(js)}
    data = json.dumps(strings, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    return js.strip(), data


# ---------------------------------------------------------------------------
# pieces of a card
# ---------------------------------------------------------------------------

def passage_block(p: dict) -> str:
    out = ['<div class="passage">']
    head = p.get("citation") or p.get("title")
    if head:
        out.append(f'<p class="cite">{esc(head)}</p>')
    if p.get("work") and p.get("work") != head:
        out.append(f'<p class="work">{esc(p["work"])}</p>')
    if p.get("ai_generated"):
        out.append(f'<p class="flag ai">{t("card.passage.ai")}</p>')
    if p.get("text"):
        out.append(f'<blockquote class="text"><p>{esc(p["text"])}</p></blockquote>')
    if p.get("text_ar"):
        out.append(f'<blockquote class="text-ar" lang="ar" dir="rtl"><p>{esc(p["text_ar"])}</p></blockquote>')
    if not p.get("text") and not p.get("text_ar"):
        out.append(f'<p class="muted">{t("card.passage.notext")}</p>')
    out.append("</div>")
    return "\n".join(out)


def period_text(period) -> str:
    if not period:
        return t("card.undated")
    a, b = period
    return t("card.period.one", a=a) if a == b else t("card.period.range", a=a, b=b)


def earlier_html(decisions: list) -> str:
    if not decisions:
        return ""
    items = []
    for d in decisions:
        parts = [t("card.earlier.item", decision=STRINGS.get(f"decision.{d['decision']}", d["decision"]), date=d["date"])]
        if d.get("note"):
            parts.append(t("card.earlier.note", value=d["note"]))
        if d.get("citation"):
            parts.append(t("card.earlier.citation", value=d["citation"]))
        items.append("<li>" + SEP.join(parts) + "</li>")
    return f'<div class="earlier"><p class="label">{t("card.earlier")}</p><ul>' + "".join(items) + "</ul></div>"


def checks_html(checks: list) -> str:
    return "\n".join(tpl("check", value=esc(k), label=t(f"check.{k}")) for k in checks)


def claim_card(u: dict, n: int, total: int, seq: int, passages: dict, story_passage: str | None) -> str:
    names = [e for e in (u["subject"], u["object"]) if e.get("name_ar")]
    detail = ""
    if names:
        detail = (f'<p class="names-ar">{t("card.names_ar")} '
                  + "; ".join(f'{ar(e["name_ar"])} ({esc(e["name"])})' for e in names) + "</p>")
    facts = [t("card.status", value=STRINGS.get(f"status.{u['status']}", u["status"])), t("card.file", value=u["file"]),
             t("card.topic", value=u["topic"]), period_text(u.get("period")), t("card.id", value=u["id"])]
    flags = []
    if u.get("ai_generated_basis"):
        flags.append(f'<p class="flag ai">{t("card.ai")}</p>')
    if u.get("citation_required_to_accept"):
        flags.append(f'<p class="flag cite">{t("card.cite_needed")}</p>')
    flags.append(earlier_html(u.get("earlier_decisions") or []))

    src = []
    if u.get("source_wording"):
        src.append(f'<p class="label">{t("card.wording")}</p><blockquote class="wording"><p>{esc(u["source_wording"])}</p></blockquote>')
    basis = u.get("basis") or {}
    if basis.get("kind") == "report":
        src.append(f'<p class="label">{t("card.report", label=basis.get("report_label") or basis.get("report") or "")}</p>')
        if basis.get("matn_ar"):
            src.append(f'<p class="label">{t("card.matn_ar")}</p>' + ar(basis["matn_ar"], "blockquote"))
        if basis.get("matn"):
            src.append(f'<p class="label">{t("card.matn")}</p><blockquote><p>{esc(basis["matn"])}</p></blockquote>')
    elif basis.get("text"):
        src.append(f'<p class="label">{t("card.basis")}</p><p class="basis">{esc(basis["text"])}</p>')
    pids = basis.get("passages") or []
    for pid in pids:
        p = passages.get(pid)
        if p is None:
            continue
        block = passage_block(p)
        if pid == story_passage:
            src.append(f'<details class="passage-d"><summary>{t("card.passage.same")}</summary>\n{block}\n</details>')
        else:
            src.append(block)
    if not pids:
        src.append(f'<p class="muted">{t("card.passage.none")}</p>')

    cite = bool(u.get("citation_required_to_accept"))
    return tpl("card", n=n, target=esc(u["id"]), kind="claim", cite="1" if cite else "0", seq=seq,
               number=t("card.number", n=n, total=total), claim=esc(u["claim"]), detail=detail,
               facts=SEP.join(f"<span>{f}</span>" for f in facts), flags="\n".join(f for f in flags if f),
               source="\n".join(src))


def identity_card(u: dict, n: int, total: int, seq: int) -> str:
    kind = u.get("entity") if u.get("entity") in ENTITY_KINDS else "other"
    title = esc(u["name"]) + (" " + ar(u["name_ar"]) if u.get("name_ar") else "")
    q = "real_group" if u.get("question") == "real_group" else kind
    detail = f'<p class="question">{t("identity.question." + q)}</p><p class="hint">{t("identity.hint")}</p>'
    facts = [t("identity.confidence", value=u.get("confidence") or ""), t("card.id", value=u["id"])]
    if u.get("variant_ids"):
        facts.append(t("identity.variants", value=", ".join(u["variant_ids"])))
    if u.get("files"):
        facts.append(t("identity.files", value=", ".join(u["files"])))
    flags = []
    if u.get("stories50_names"):
        flags.append(f'<p>{t("identity.names50", value="; ".join(u["stories50_names"]))}</p>')
    flags.append(earlier_html(u.get("earlier_decisions") or []))
    why = "".join(f"<li>{esc(p)}</li>" for p in u.get("note_parts") or [])
    src = f'<p class="label">{t("identity.why")}</p><ul class="why">{why}</ul>' if why else f'<p class="muted">{t("card.passage.none")}</p>'
    return tpl("card", n=n, target=esc(u["id"]), kind="identity", cite="0", seq=seq,
               number=t("card.number", n=n, total=total), claim=title, detail=detail,
               facts=SEP.join(f"<span>{f}</span>" for f in facts), flags="\n".join(f for f in flags if f),
               source=src)


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------

def batch_title(b: dict, html_out: bool = True) -> str:
    kind = b["kind"]
    title = b.get("title") or b["batch"]
    if kind == "story" and b.get("story_number") is not None:
        s = t("batch.title.story", n=b["story_number"], title=title)
    elif kind == "identity":
        s = t("batch.title.identity")
    elif kind in ("person", "file"):
        s = t(f"batch.title.{kind}", title=title)
    else:
        s = esc(title)
    if b.get("parts", 1) > 1:
        s = t("batch.part", title=Raw(s), part=b["part"], parts=b["parts"])
    if html_out and b.get("title_ar"):
        s += " " + ar(b["title_ar"])
    return s


def plain(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment))


def page(kind: str, title: str, body: str, queue: dict, css: str, js: str, strings: str, batch: str = "", file: str = "") -> str:
    fp = queue.get("fingerprint") or ""
    return tpl("base", title=esc(STRINGS["page.title"].format(title=title)), css=css, page=kind, batch=esc(batch),
               file=esc(file), fingerprint=esc(fp), body=body, strings=strings, js=js,
               index_current=' aria-current="page"' if kind == "index" else "",
               queue_line=t("footer.queue", fingerprint=fp), url_licensing=URL_LICENSING,
               url_cc_by_sa=URL_CC_BY_SA, url_agpl=URL_AGPL) + "\n"


def in_scope(unit: dict, grants) -> bool:
    if grants is None:
        return True
    if unit["kind"] == "identity":
        facets = {"sources": set(unit.get("files") or []), "topic": "identity", "period": None}
    else:
        facets = {"sources": {unit["file"].rsplit(".ttl", 1)[0]}, "topic": unit["topic"],
                  "period": tuple(unit["period"]) if unit.get("period") else None}
    return c.scope_matches(grants, facets)


def batches_of(queue: dict, grants) -> list[dict]:
    out = []
    for b in list(queue.get("claims") or []) + list(queue.get("identity") or []):
        units = [u for u in b["units"] if in_scope(u, grants)]
        if units:
            out.append(dict(b, units=units))
    return out


def build(queue: dict, out: Path, scope_text: str | None = None, grants=None) -> list[Path]:
    css = inline_css()
    js, strings = inline_js()
    checks = list(queue.get("checks") or c.CHECKS)
    passages = queue.get("passages") or {}
    batches = batches_of(queue, grants)
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("*.html")):
        old.unlink()
    written = []
    seq = 0
    reviewer, send, keys = tpl("reviewer"), tpl("send"), tpl("keys")
    decide = tpl("decide", checks=checks_html(checks))  # one copy; review.js clones it into each card
    for i, b in enumerate(batches):
        total = len(b["units"])
        cards = []
        story_passage = b.get("passage") if b["kind"] == "story" else None
        for n, u in enumerate(b["units"], start=1):
            seq += 1
            if u.get("kind") == "identity":
                cards.append(identity_card(u, n, total, seq))
            else:
                cards.append(claim_card(u, n, total, seq, passages, story_passage))
        story = ""
        if story_passage and story_passage in passages:
            p = passages[story_passage]
            story = tpl("story", passage=passage_block(p),
                        ai=f'<p class="warn">{t("batch.passage.ai")}</p>' if p.get("ai_generated") else "")
        pager = []
        if i > 0:
            pager.append(f'<li><a rel="prev" href="{page_file(batches[i - 1]["batch"])}">'
                         f'{t("pager.prev", title=Raw(batch_title(batches[i - 1])))}</a></li>')
        if i + 1 < len(batches):
            pager.append(f'<li><a rel="next" href="{page_file(batches[i + 1]["batch"])}">'
                         f'{t("pager.next", title=Raw(batch_title(batches[i + 1])))}</a></li>')
        unit_count = tn("count.questions", total) if b["kind"] == "identity" else tn("count.claims", total)
        body = tpl("batch", h1=batch_title(b), lead=t("batch.lead", count=unit_count), reviewer=reviewer,
                   story=story, cards="\n".join(cards), decide=decide, send=send, pager="\n".join(pager), keys=keys)
        name = page_file(b["batch"])
        path = out / name
        path.write_text(page("batch", plain(batch_title(b)), body, queue, css, js, strings, b["batch"], name), encoding="utf-8")
        written.append(path)

    sections = []
    for kind in KINDS:
        items = [tpl("batch_item", batch=esc(b["batch"]), total=len(b["units"]), href=page_file(b["batch"]),
                     title=batch_title(b), count=(tn("count.questions", len(b["units"])) if kind == "identity"
                                                  else tn("count.claims", len(b["units"]))))
                 for b in batches if b["kind"] == kind]
        if items:
            sections.append(tpl("section", kind=kind, heading=t(f"index.section.{kind}"), lead=t(f"index.lead.{kind}"),
                                items="\n".join(items)))
    if not sections:
        sections.append(f'<p class="muted">{t("index.empty")}</p>')
    n_claims = sum(len(b["units"]) for b in batches if b["kind"] != "identity")
    n_questions = sum(len(b["units"]) for b in batches if b["kind"] == "identity")
    in_batches = Raw(tn("count.batches", len(batches)))
    if n_questions:
        lead = t("index.lead", claims=Raw(tn("count.claims", n_claims)), questions=Raw(tn("count.questions", n_questions)),
                 batches=in_batches)
    else:
        lead = t("index.lead_claims", claims=Raw(tn("count.claims", n_claims)), batches=in_batches)
    lens = (queue.get("tradition") or {}).get("label") or ""
    scope = f'<p class="scope">{t("index.scope", scope=scope_text)}</p>' if scope_text else ""
    body = tpl("index", lead=lead, lens=t("index.lens", label=lens), scope=scope, reviewer=reviewer,
               sections="\n".join(sections), send=send, keys=keys)
    path = out / "index.html"
    path.write_text(page("index", STRINGS["index.title"], body, queue, css, js, strings, "", "index.html"), encoding="utf-8")
    written.append(path)
    (out / "sw.js").write_text((STATIC / "sw.js").read_text(encoding="utf-8"), encoding="utf-8")
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--queue", type=Path, help="build from this queue file instead of rebuilding review/dist/queue.json")
    ap.add_argument("--out", type=Path, default=DIST, help=f"output folder (default {DIST.relative_to(c.ROOT)})")
    ap.add_argument("--ontology", type=Path, default=c.ONTOLOGY, help="ontology folder, for the queue and --scope")
    ap.add_argument("--scope", help="only the units this roster scope covers, e.g. \"source:stories-50; topic:kinship\"")
    args = ap.parse_args(argv)
    queue_path = args.queue
    if queue_path is None:
        import build_queue
        queue_path = args.out / "queue.json"
        code = build_queue.main(["--ontology", str(args.ontology), "--out", str(queue_path)])
        if code:
            return code
    try:
        queue = json.loads(Path(queue_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: cannot read the queue {queue_path}: {e}")
        return 2
    if queue.get("format") != "marsad-review-queue" or queue.get("version") != 1:
        print(f"error: {queue_path} is not a review queue (format marsad-review-queue, version 1)")
        return 2
    grants = None
    if args.scope:
        tree = c.Tree(args.ontology)
        try:
            grants = c.parse_scope(args.scope, tree.topics(), tree.sources())
        except ValueError as e:
            print(f"error: --scope: {e}")
            return 2
    written = build(queue, args.out, args.scope, grants)
    sizes = sorted((p.stat().st_size, p.name) for p in written)
    print(f"wrote {len(written)} pages to {args.out} (largest {sizes[-1][1]}, {sizes[-1][0]:,} bytes) and sw.js")
    return 0


if __name__ == "__main__":
    sys.exit(main())
