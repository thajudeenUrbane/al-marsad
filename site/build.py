#!/usr/bin/env python3
"""Static site generator for the reader tier.

    .venv/bin/python site/build.py [--graph build/graph.ttl] [--out site/dist]

Reads build/graph.ttl only (run ontology/build_graph.py first; if the file is missing
this script runs it). Writes one HTML page per person, group, place, event and story,
an index per type, a home page and a glossary, plus one Turtle file per entity.
No JavaScript, no web fonts, no external requests.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

MARKER = ".al-marsad-site"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from glossary import Glossary  # noqa: E402
from model import KINDS, Site  # noqa: E402
from render import I18n, Renderer  # noqa: E402


def build(graph: Path, out: Path, quiet: bool = False) -> dict:
    if not graph.exists():
        print(f"{graph} not found; running ontology/build_graph.py", file=sys.stderr)
        subprocess.run([sys.executable, str(ROOT / "ontology" / "build_graph.py")], check=True, cwd=ROOT)
    site = Site(graph)
    glossary = Glossary(HERE / "data" / "glossary.json", site.all_graph_labels(), site.vocabulary_labels())
    i18n = I18n(HERE / "i18n" / "en.json")
    r = Renderer(site, glossary, i18n, HERE / "templates")

    if out.exists():
        if any(out.iterdir()) and not (out / MARKER).exists():
            sys.exit(f"{out} exists and was not made by site/build.py; refusing to delete it")
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    (out / MARKER).write_text("made by site/build.py; safe to delete and rebuild\n", encoding="utf-8")
    shutil.copyfile(HERE / "static" / "site.css", out / "assets" / "site.css")

    def write(rel: str, content: str):
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    counts = {k: 0 for k in KINDS}
    write("index.html", r.home_page())
    for kind in KINDS:
        write(f"{kind}/index.html", r.index_page(kind))
        for e in site.by_kind[kind]:
            write(f"{kind}/{e.pid}/index.html", r.entity_page(e))
            write(f"{kind}/{e.pid}/entity.ttl", site.turtle_for(e.iri))
            counts[kind] += 1
    write("glossary/index.html", r.glossary_page())  # last: it lists the terms the pages linked

    summary = {"pages": counts, "indexes": len(KINDS), "other": 2,
               "total_html": sum(counts.values()) + len(KINDS) + 2,
               "glossary_defined": len(glossary.listed()[0]), "glossary_needed": len(glossary.listed()[1])}
    if not quiet:
        print("built", summary["total_html"], "pages into", out)
        print("  " + ", ".join(f"{k}: {v}" for k, v in counts.items()),
              f"| index pages: {summary['indexes']} | home + glossary: 2")
        print(f"  glossary: {summary['glossary_defined']} defined, {summary['glossary_needed']} definition needed")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", default=str(ROOT / "build" / "graph.ttl"))
    ap.add_argument("--out", default=str(HERE / "dist"))
    a = ap.parse_args(argv)
    build(Path(a.graph), Path(a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
