#!/usr/bin/env python3
"""Learning paths and practice (slices 6 and 7), built on top of the reader tier.

    .venv/bin/python learn/build_learn.py [--graph build/graph.ttl] [--site site/dist]

Run it after site/build.py (which rebuilds site/dist/ from scratch, learn/ included).
It writes site/dist/learn/ and nothing else: a journey index, one page per journey in
learn/journeys/, the practice page with its question bank (bank.json), and two small
assets (learn.css, learn.js). It reads build/graph.ttl through site/model.py, so every
step links to the page the reader tier built for that entity, and reuses site/display.py
for names and dates and the site's stylesheet for the look.

No page needs JavaScript. learn.js only adds "done" boxes that keep progress in this
browser (localStorage); without it, or without storage, every page is complete.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SITE = ROOT / "site"
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(HERE))

from model import Site  # noqa: E402

import journeys  # noqa: E402
import practice  # noqa: E402
from render_learn import LearnRenderer, Strings  # noqa: E402

MARKER = ".al-marsad-learn"


def build(graph: Path, site_dist: Path, quiet: bool = False, journeys_dir: Path | None = None) -> dict:
    if not graph.exists():
        sys.exit(f"{graph} not found: run ontology/build_graph.py and site/build.py first")
    if not (site_dist / "assets" / "site.css").is_file():
        sys.exit(f"{site_dist} has no reader-tier site: run site/build.py first")
    site = Site(graph)
    strings = Strings(HERE / "i18n" / "en.json", SITE / "i18n" / "en.json")
    specs = journeys.load_specs(journeys_dir or HERE / "journeys")
    built = journeys.build_all(site, specs)
    missing = sorted({f"{st.entity.kind}/{st.entity.pid}/" for j in built for st in j.steps + j.set_apart
                      if not (site_dist / st.entity.kind / st.entity.pid / "index.html").is_file()})
    if missing:
        sys.exit(f"{site_dist} is older than the graph ({len(missing)} step pages missing, e.g. {missing[0]}): "
                 "run site/build.py again")
    bank = practice.bank(site.g)
    counts = practice.status_counts(site.g)
    r = LearnRenderer(site, strings, HERE / "templates")

    out = site_dist / "learn"
    if out.exists():
        if any(out.iterdir()) and not (out / MARKER).exists():
            sys.exit(f"{out} exists and was not made by learn/build_learn.py; refusing to delete it")
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    (out / MARKER).write_text("made by learn/build_learn.py; safe to delete and rebuild\n", encoding="utf-8")
    for name in ("learn.css", "learn.js"):
        shutil.copyfile(HERE / "static" / name, out / "assets" / name)

    def write(rel: str, content: str):
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    for j in built:
        write(f"{j.slug}/index.html", r.journey_page(j))
    pages = r.practice_pages(bank, counts)
    for rel, content in pages.items():
        write(rel, content)
    write("practice/bank.json", json.dumps({"questions": bank}, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    write("index.html", r.index_page(built, len(bank)))

    summary = {"journeys": {j.slug: {"steps": len(j.steps), "apart": len(j.set_apart), "draft": j.is_draft}
                            for j in built},
               "questions": len(bank), "practice_pages": len(pages), "claims": counts}
    if not quiet:
        print(f"built learn/ into {out}")
        for j in built:
            extra = f" (+{len(j.set_apart)} apart)" if j.set_apart else ""
            print(f"  {j.slug}: {len(j.steps)} steps{extra}, {'draft' if j.is_draft else 'approved'}")
        print(f"  practice: {len(bank)} questions from accepted claims "
              f"({counts.get('accepted', 0)} accepted of {sum(counts.values())} claims)")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", default=str(ROOT / "build" / "graph.ttl"))
    ap.add_argument("--site", default=str(SITE / "dist"))
    a = ap.parse_args(argv)
    build(Path(a.graph), Path(a.site))
    return 0


if __name__ == "__main__":
    sys.exit(main())
