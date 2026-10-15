#!/usr/bin/env python3
"""Writes the ask page into the built site: site/dist/ask/.

    .venv/bin/python site/build.py          # first: the reader pages
    .venv/bin/python ask/build_ask.py [--graph build/graph.ttl] [--site site/dist]

Standalone: it reads build/graph.ttl (through ask/index.py) and adds files under
site/dist/ask/ only; it never changes the site's own files. Run it again after every
site build (site/build.py starts from an empty site/dist/).

Writes:
  ask/index.html        the page: a question box (shown only with JavaScript), the list
                        of questions already answered, what the tool will not do, and
                        what the graph covers
  ask/q/<slug>/         one page per answered question, built here in Python, so every
                        answer can be read with JavaScript off and has its own address
  ask/ask.js, ask.css   the browser port of the translator, executor and renderer
  ask/ask-index.json    the compact index plus the rules and strings the port uses;
                        loaded only when a visitor starts typing

The answered questions are the golden questions marked "cache" (ask/golden/
questions.jsonl). Fails (exit 1) if site/dist is missing or ask/ is over 2 MB.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from string import Template

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ask import index as ask_index  # noqa: E402
from ask.dsl import Engine, load_i18n  # noqa: E402
from ask.normalise import RULES, text_key  # noqa: E402
from ask.present import Presenter, esc  # noqa: E402
from ask.translate import answer  # noqa: E402

URL_LICENSING = "https://github.com/thajudeenUrbane/al-marsad/blob/main/LICENSING.md"
URL_CC_BY_SA = "https://creativecommons.org/licenses/by-sa/4.0/"
URL_AGPL = "https://www.gnu.org/licenses/agpl-3.0.html"
BUDGET = 2_000_000
SITE_MARKER = ".al-marsad-site"
GOLDEN = HERE / "golden" / "questions.jsonl"
GROUPS = ("presence", "family", "events", "links", "stories", "other", "refusal")
TRY = 4


def golden(path: Path = GOLDEN) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def slugify(q: str, used: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text_key(q)).strip("-")[:60].strip("-") or "q"
    slug, k = base, 2
    while slug in used:
        slug, k = f"{base}-{k}", k + 1
    used.add(slug)
    return slug


def fill_i18n(text: str, T: dict) -> str:
    return re.sub(r"\[\[([a-z0-9_.]+)\]\]", lambda m: esc(T[m.group(1)]), text)


def page(T: dict, title: str, body: str, base: str, script: str = "", current: bool = False) -> str:
    tpl = Template((HERE / "templates" / "base.html").read_text(encoding="utf-8"))
    html = tpl.substitute(title=esc(title), body=body, base=base, script=script,
                          ask_current=' aria-current="page"' if current else "",
                          url_licensing=URL_LICENSING, url_cc_by_sa=URL_CC_BY_SA, url_agpl=URL_AGPL)
    return fill_i18n(html, T)


def title_of(T: dict, name: str) -> str:
    return f"{name} {T['title.sep']} {T['site.name']}"


def build(graph: Path, site: Path, quiet: bool = False) -> dict:
    if not site.is_dir() or not (site / SITE_MARKER).exists():
        sys.exit(f"{site} is not a built site; run site/build.py first")
    out = site / "ask"
    if out.exists():
        shutil.rmtree(out)
    (out / "q").mkdir(parents=True)

    ix = ask_index.build(graph)
    eng = Engine(ix)
    T = load_i18n()
    cache = [g for g in golden() if g.get("cache")]
    used: set = set()
    for g in cache:
        g["slug"] = slugify(g["question"], used)
    examples = [[g["question"], g["slug"]] for g in cache if g.get("group") != "refusal"][:6]
    pres = Presenter(eng, T, "../../../", examples)

    def write(rel: str, text: str):
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    # one page per answered question
    for g in cache:
        ans = answer(g["question"], eng, T)
        body = Template((HERE / "templates" / "cached.html").read_text(encoding="utf-8")).substitute(
            question=pres.h(g["question"]), answer=pres.render(ans))
        write(f"q/{g['slug']}/index.html", page(T, title_of(T, g["question"]), fill_i18n(body, T), "../../../"))

    # the ask page
    groups = []
    for grp in GROUPS:
        items = [g for g in cache if g.get("group", "other") == grp]
        if not items:
            continue
        lis = "".join(f'<li><a href="q/{g["slug"]}/">{pres.h(g["question"])}</a></li>' for g in items)
        groups.append(f'<h3>{esc(T["page.group." + grp])}</h3><ul class="plain cached-list">{lis}</ul>')
    tries = []
    for grp in GROUPS[:-1]:
        g = next((g for g in cache if g.get("group") == grp), None)
        if g and len(tries) < TRY:
            tries.append(f'<button type="button" class="try" data-q="{esc(g["question"])}">{pres.h(g["question"])}</button>')
    limits = "\n".join(f"<li>{pres.h(T['refusal.limit.' + r['class']])}</li>" for r in RULES["refusals"])
    st = ix["status"]
    coverage = pres.h(pres.t("page.coverage", **ix["counts"]))
    coverage_status = pres.h(pres.t("page.coverage_status", proposed=st.get("proposed", 0),
                                    accepted=st.get("accepted", 0), none=st.get("none", 0)))
    gaps = ""
    if ix["gaps"]:
        gaps = (f'<details class="gaps"><summary>{esc(T["page.coverage_gaps"])}</summary><ul>'
                + "".join(f"<li>{pres.h(x)}</li>" for x in ix["gaps"]) + "</ul></details>")
    body = Template((HERE / "templates" / "ask.html").read_text(encoding="utf-8")).substitute(
        max=RULES["limits"]["question_max"], cached="\n".join(groups), limits=limits, coverage=coverage,
        coverage_status=coverage_status, gaps=gaps, **{"try": " ".join(tries)})
    write("index.html", page(T, title_of(T, T["page.title"]), fill_i18n(body, T), "../",
                             script='<script src="ask.js" defer></script>', current=True))

    # the browser engine and its data
    shutil.copyfile(HERE / "static" / "ask.js", out / "ask.js")
    shutil.copyfile(HERE / "static" / "ask.css", out / "ask.css")
    data = dict(ix)
    data.update({"rules": RULES, "i18n": T, "examples": examples})
    write("ask-index.json", json.dumps(data, ensure_ascii=False, separators=(",", ":")))

    sizes = {p.relative_to(out).as_posix(): p.stat().st_size for p in out.rglob("*") if p.is_file()}
    total = sum(sizes.values())
    summary = {"pages": len(cache) + 1, "bytes": total, "index_bytes": sizes["ask-index.json"],
               "js_bytes": sizes["ask.js"], "version": ix["version"]}
    if not quiet:
        print(f"built ask/: {len(cache)} answered questions + the ask page, {total:,} bytes in all "
              f"(index {sizes['ask-index.json']:,}, ask.js {sizes['ask.js']:,}); graph version {ix['version']}")
    if total > BUDGET:
        print(f"FAILED: ask/ is {total:,} bytes, over the {BUDGET:,} byte budget", file=sys.stderr)
        sys.exit(1)
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", default=str(ROOT / "build" / "graph.ttl"))
    ap.add_argument("--site", default=str(ROOT / "site" / "dist"))
    a = ap.parse_args(argv)
    build(Path(a.graph), Path(a.site))
    return 0


if __name__ == "__main__":
    sys.exit(main())
