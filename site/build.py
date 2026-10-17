#!/usr/bin/env python3
"""Static site generator for the reader tier.

    .venv/bin/python site/build.py [--graph build/graph.ttl] [--out site/dist]
    .venv/bin/python site/build.py --hub     # after the view builders: rewrite only the hub pages

Reads build/graph.ttl only (run ontology/build_graph.py first; if the file is missing
this script runs it). Writes one HTML page per person, group, place, event and story,
an index per type, the home page (three doors and the hub of every view), the Study and
Research door pages, a glossary, a search page and the Experiments page with copies of
the earlier prototypes; plus one Turtle file per entity, the whole graph for download,
the search index (search.json) and the thread data (thread.json). No web fonts, no
external requests. JavaScript only enhances: assets/enhance.js (the plain-words switch,
every page), assets/search.js (the search page) and assets/thread.js (person and group
pages); every page works without it.

The Arabic interface (slice 9, a draft awaiting review by the scholars) is a copy of the
reader tier under site/dist/ar/ at the same paths, built from site/i18n/ar.json by
build_arabic; the data on it is as recorded.

The folders other builders write into site/dist (site/hub.py: observatory, lifelines,
timeline, map, learn, ask) are never deleted here. The home page links a view only if
its folder holds an index.html when the hub pages are written: run the view builders
first, or run them after this script and then `site/build.py --hub`.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

MARKER = ".al-marsad-site"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import display  # noqa: E402
import experiments  # noqa: E402
import external  # noqa: E402
import hub  # noqa: E402
import names  # noqa: E402
from glossary import Glossary  # noqa: E402
from model import KINDS, Entity, Site  # noqa: E402
from render import I18n, Renderer  # noqa: E402
from thread import build_thread  # noqa: E402

STATIC = ("site.css", "search.js", "enhance.js", "thread.js", "archive.css")
# data files offered for download on the Research page: (key, source, path in site/dist)
DOWNLOADS = (("graph", None, "data/graph.ttl"),
             ("external_ids", external.CSV_PATH, "data/external-ids.csv"),
             ("external_ids_althurayya", external.CSV_PATH_ALTHURAYYA, "data/external-ids-althurayya.csv"))


def search_names(e: Entity) -> list[str]:
    """Every recorded name of an entity, for the search index: its labels as recorded
    (the scholarly form), its Arabic and other-language names, and for a person the
    parts of each name form a reader may know them by (ism, kunya, laqab, nisba, the
    full form). Nasab parts are left out: they name the father and are in the label."""
    out = [display.strip_blessing_tail(e.scholarly)] + list(e.other_labels) + list(e.arabic)
    out += [lit.text for lit in e.other_names]
    for f in e.data.get("name_forms", []):
        out += [x for x in (f.get("ism"), f.get("kunya"), f.get("full")) if x]
        out += list(f.get("laqab", [])) + list(f.get("nisba", []))
    return out


def search_index(site: Site) -> dict:
    """search.json: the shared rules (names.RULES, so the browser holds no copy of its
    own) and one item per entity, in index order (type, then A-Z)."""
    items = [names.index_item(f"{e.kind}/{e.pid}", e.name, search_names(e))
             for kind in KINDS for e in site.by_kind[kind]]
    return {"v": 1, "rules": names.RULES, "items": items}


def renderer(graph: Path, lang: str = "en", site: Site | None = None) -> tuple[Site, Glossary, Renderer]:
    """The model, the glossary and the page renderer for one language ("en" or "ar"; the Arabic
    pages are written under ar/, see build_arabic). Pass `site` to reuse a model already read."""
    if site is None:
        if not graph.exists():
            print(f"{graph} not found; running ontology/build_graph.py", file=sys.stderr)
            subprocess.run([sys.executable, str(ROOT / "ontology" / "build_graph.py")], check=True, cwd=ROOT)
        site = Site(graph)
    glossary = Glossary(HERE / "data" / "glossary.json", site.all_graph_labels(), site.vocabulary_labels())
    i18n = I18n(HERE / "i18n" / f"{lang}.json", lang)
    matches = external.load(known=set(site.entities))
    return site, glossary, Renderer(site, glossary, i18n, HERE / "templates", external=matches)


def clear(out: Path):
    """Empties `out` for a fresh build, except the folders other builders own (hub.KEEP)."""
    if not out.exists():
        return
    if any(out.iterdir()) and not (out / MARKER).exists():
        sys.exit(f"{out} exists and was not made by site/build.py; refusing to delete it")
    for child in out.iterdir():
        if child.is_dir() and child.name in hub.KEEP:
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def downloads_in(out: Path) -> list[tuple[str, str, int]]:
    return [(key, rel, (out / rel).stat().st_size) for key, _, rel in DOWNLOADS if (out / rel).is_file()]


def write_hub_pages(r: Renderer, out: Path, prefix: str = "") -> list[str]:
    """The pages that list the views: home, Study and Research, under `prefix` ("" or "ar/").
    Returns the views found."""
    views = hub.built(out)
    for rel, page in (("index.html", r.home_page(views)), ("study/index.html", r.study_page(views)),
                      ("research/index.html", r.research_page(views, downloads_in(out)))):
        (out / prefix / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / prefix / rel).write_text(page, encoding="utf-8")
    return views


def build_arabic(site: Site, graph: Path, out: Path) -> dict:
    """The Arabic copy of the reader tier under out/ar/, at the same paths: the home, Study,
    Research, search, glossary, an index per type and a page for every record. The data
    (names, claims, story texts) is the same as recorded; only the interface text is Arabic,
    drafted and awaiting review by the scholars. Assets, search.json, the Turtle files and
    the views are not copied: the Arabic pages link the ones in the site root (the views are
    English only for now)."""
    _, _, r = renderer(graph, "ar", site)

    def write(rel: str, content: str):
        path = out / "ar" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    pages = 0
    for kind in KINDS:
        write(f"{kind}/index.html", r.index_page(kind))
        pages += 1
        for e in site.by_kind[kind]:
            write(f"{kind}/{e.pid}/index.html", r.entity_page(e))
            pages += 1
    thread = build_thread(site, r.t, "ar")
    write("thread.json", json.dumps(thread, ensure_ascii=False, separators=(",", ":")))
    write("search/index.html", r.search_page())
    write_hub_pages(r, out, "ar")
    write("glossary/index.html", r.glossary_page())   # last: it lists the terms the pages linked
    return {"pages": pages + 5, "thread_bytes": (out / "ar" / "thread.json").stat().st_size}


def build(graph: Path, out: Path, quiet: bool = False) -> dict:
    site, glossary, r = renderer(graph)
    clear(out)
    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / MARKER).write_text("made by site/build.py; safe to delete and rebuild\n", encoding="utf-8")
    for name in STATIC:
        shutil.copyfile(HERE / "static" / name, out / "assets" / name)

    def write(rel: str, content: str):
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    counts = {k: 0 for k in KINDS}
    for kind in KINDS:
        write(f"{kind}/index.html", r.index_page(kind))
        for e in site.by_kind[kind]:
            write(f"{kind}/{e.pid}/index.html", r.entity_page(e))
            write(f"{kind}/{e.pid}/entity.ttl", site.turtle_for(e.iri))
            counts[kind] += 1
    index = search_index(site)
    write("search.json", json.dumps(index, ensure_ascii=False, separators=(",", ":")))
    thread = build_thread(site, r.t)
    write("thread.json", json.dumps(thread, ensure_ascii=False, separators=(",", ":")))
    write("search/index.html", r.search_page())
    for key, source, rel in DOWNLOADS:
        src = graph if source is None else source
        if src.is_file():
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, out / rel)
    write(f"{experiments.FOLDER}/index.html", r.experiments_page())
    copies = experiments.copy_all(out, r.archive_note, lambda base: r.footer_html("site-footer archive-footer"))
    views = write_hub_pages(r, out)
    write("glossary/index.html", r.glossary_page())  # last: it lists the terms the pages linked
    arabic = build_arabic(site, graph, out)

    other = ["home", "search", "glossary", "study", "research", "experiments"]
    summary = {"pages": counts, "indexes": len(KINDS), "other": len(other),
               "total_html": sum(counts.values()) + len(KINDS) + len(other), "prototype_copies": len(copies),
               "views": views, "arabic_pages": arabic["pages"], "arabic_thread_bytes": arabic["thread_bytes"],
               "search_items": len(index["items"]), "search_bytes": (out / "search.json").stat().st_size,
               "thread_bytes": (out / "thread.json").stat().st_size, "thread_claims": len(thread["c"]),
               "external_matches": sum(len(v) for v in r.external.values()),
               "glossary_defined": len(glossary.listed()[0]), "glossary_needed": len(glossary.listed()[1])}
    if not quiet:
        print("built", summary["total_html"], "pages into", out, f"(+ {len(copies)} prototype copies)")
        print("  " + ", ".join(f"{k}: {v}" for k, v in counts.items()),
              f"| index pages: {summary['indexes']} | {', '.join(other)}: {len(other)}")
        print(f"  search.json: {summary['search_items']} names, {summary['search_bytes']:,} bytes;"
              f" thread.json: {summary['thread_claims']} claims and links, {summary['thread_bytes']:,} bytes")
        print(f"  Arabic interface (draft) under ar/: {arabic['pages']} pages; thread.json: {arabic['thread_bytes']:,} bytes")
        print(f"  glossary: {summary['glossary_defined']} defined, {summary['glossary_needed']} definition needed;"
              f" possible matches elsewhere: {summary['external_matches']}")
        print(f"  views linked from the home page: {', '.join(views) or 'none built yet'}")
    return summary


def build_hub(graph: Path, out: Path, quiet: bool = False) -> list[str]:
    """Rewrites only the home, Study and Research pages from what site/dist holds now."""
    if not (out / MARKER).exists() or not (out / "index.html").exists():
        sys.exit(f"{out} has no reader site yet: run site/build.py first")
    site, _, r = renderer(graph)
    views = write_hub_pages(r, out)
    if (out / "ar" / "index.html").exists():
        write_hub_pages(renderer(graph, "ar", site)[2], out, "ar")
    if not quiet:
        print(f"hub pages rewritten in {out}; views linked: {', '.join(views) or 'none built yet'}")
    return views


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", default=str(ROOT / "build" / "graph.ttl"))
    ap.add_argument("--out", default=str(HERE / "dist"))
    ap.add_argument("--hub", action="store_true",
                    help="only rewrite the pages that list the views (run after the view builders)")
    a = ap.parse_args(argv)
    if a.hub:
        build_hub(Path(a.graph), Path(a.out))
    else:
        build(Path(a.graph), Path(a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
