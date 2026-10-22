#!/usr/bin/env python3
"""Static site generator for the reader tier.

    .venv/bin/python site/build.py [--graph build/graph.ttl] [--out site/dist]
    .venv/bin/python site/build.py --hub     # after the view builders: rewrite only the hub pages

Reads build/graph.ttl only (run ontology/build_graph.py first; if the file is missing
this script runs it). Writes one HTML page per person, group, place, event and story,
an index per type, the home page (three doors and the hub of every view), the Study and
Research door pages, a glossary, a search page and the Experiments page with copies of
the earlier prototypes; plus one Turtle file per entity, the whole graph for download,
the search index (search-index/: a manifest and its shards) and the thread data
(thread/<kind>/<id>.json). No web fonts, no
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
from thread import build_thread, thread_files  # noqa: E402

STATIC = ("site.css", "search.js", "enhance.js", "thread.js", "parts.js", "archive.css")
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


SEARCH_DIR = "search-index"   # the search index: a manifest and its shards (slice 11b)
# words too common to file a name under: nasab particles, and the English of descriptions such as
# "(father of ...)" that the full-book pass gave namesakes; they still count when a query is ranked
SHARD_SKIP = {"ibn", "bint", "abd", "بن", "بنت", "عبد", "of", "the", "and", "father", "mother", "son", "daughter",
              "in", "ancestor", "line", "lineage", "named", "with", "from", "not", "otherwise", "identified"}


def search_index(site: Site) -> dict:
    """The whole search index: the shared rules (names.RULES, so the browser holds no copy of
    its own) and one item per entity, in index order (type, then A-Z). Each item carries what a
    result line shows: the name, the Arabic names, the type and the coverage (keys; the page
    holds their words in its language)."""
    items = []
    for kind in KINDS:
        for e in site.by_kind[kind]:
            it = names.index_item(f"{e.kind}/{e.pid}", e.name, search_names(e))
            it["t"], it["v"], it["o"] = e.subtype or e.kind, e.coverage or "", len(items)
            if e.arabic:
                it["a"] = list(e.arabic)
            items.append(it)
    return {"v": 1, "rules": names.RULES, "items": items}


SHARD_MAX = 120_000   # a shard larger than this is cut again by a third letter


def shard_words(it: dict) -> set[str]:
    """What an item is filed under: "n" + each word of its names, and "s" + each word's
    sound skeleton (so Uthman and Othman meet)."""
    out = set()
    for k in it["k"]:
        for w in k.split():
            if len(w) >= 2 and w not in SHARD_SKIP:
                out.add("n" + w)
                sk = (names.skeleton_words(w) or [""])[0]
                if len(sk) >= 2:
                    out.add("s" + sk)
    return out


def shard_file(key: str) -> str:
    """A shard's file name: the key, each character outside a-z and 0-9 as _<hex>
    (search.js derives it the same way)."""
    return "".join(c if c.isascii() and c.isalnum() else f"_{ord(c):x}" for c in key) + ".json"


def write_search(index: dict, out: Path) -> dict:
    """search-index/index.json (the rules and the shards' sizes) and one shard per key; a
    shard keeps index order, so results rank as over the whole index."""
    def size(items: list) -> int:
        return len(json.dumps({"v": 2, "items": items}, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    words = [shard_words(it) for it in index["items"]]
    shards: dict[str, list] = {}
    for it, ws in zip(index["items"], words):
        for key in sorted({w[:3] for w in ws}):   # "n" or "s", and two letters
            shards.setdefault(key, []).append(it)
    split: dict[str, list[str]] = {}
    for key in [k for k, v in shards.items() if size(v) > SHARD_MAX]:
        # cut by the third letter; a two-letter word stays in the key itself
        sub: dict[str, list] = {}
        for it, ws in zip(index["items"], words):
            for w in {w for w in ws if w[:3] == key}:
                sub.setdefault(w[:4], [])
                if not sub[w[:4]] or sub[w[:4]][-1] is not it:
                    sub[w[:4]].append(it)
        del shards[key]
        split[key] = sorted(sub)
        shards.update(sub)
    # a sound shard still too large (one skeleton shared by thousands of names: ʿAmr, ʿUmar, Murra)
    # is left out: those names are found by their spelling, not by their sound
    dropped = sorted(k for k, v in shards.items() if k.startswith("s") and size(v) > SHARD_MAX)
    for k in dropped:
        del shards[k]
    folder = out / SEARCH_DIR
    folder.mkdir(parents=True, exist_ok=True)
    sizes = {}
    for key, items in sorted(shards.items()):
        text = json.dumps({"v": 2, "items": items}, ensure_ascii=False, separators=(",", ":"))
        (folder / shard_file(key)).write_text(text, encoding="utf-8")
        sizes[key] = len(text.encode("utf-8"))
    manifest = {"v": 2, "rules": names.RULES, "skip": sorted(SHARD_SKIP), "shards": sizes, "split": split}
    (folder / "index.json").write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {"items": len(index["items"]), "shards": len(sizes), "largest": max(sizes.values()),
            "manifest": (folder / "index.json").stat().st_size}


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


RENAMES = ROOT / "ontology" / "corpus" / "id-renames.csv"
IDENTITY = ROOT / "ontology" / "corpus" / "identity.csv"
SEGMENT = {"per": "person", "plc": "place", "ev": "event", "grp": "group", "sty": "story"}


def retired(site: Site) -> dict[tuple[str, str], Entity]:
    """Every retired address of a record the site has: (kind, old id) -> the record now. From
    id-renames.csv (re-minted IDs, followed to the last) and identity.csv's variant_ids (merges);
    addresses never change, they redirect (maintainer G5)."""
    import csv
    nxt = {}
    if RENAMES.exists():
        with RENAMES.open(encoding="utf-8", newline="") as fh:
            nxt = {r["old_id"]: r["new_id"] for r in csv.DictReader(fh)}
    if IDENTITY.exists():
        with IDENTITY.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                for v in filter(None, r.get("variant_ids", "").split(";")):
                    nxt.setdefault(v, r["canonical_id"])
    by_pid = {(e.kind, e.pid): e for e in site.entities.values()}
    out = {}
    for old in nxt:
        pre, _, pid = old.partition(":")
        if pre not in SEGMENT:
            continue
        cur, seen = old, set()
        while cur in nxt and cur not in seen:
            seen.add(cur)
            cur = nxt[cur]
        cpre, _, cpid = cur.partition(":")
        e = by_pid.get((SEGMENT.get(cpre, ""), cpid))
        if e is not None and (SEGMENT[pre], pid) not in by_pid:
            out[(SEGMENT[pre], pid)] = e
    return out


def write_moved(r: Renderer, site: Site, out: Path, prefix: str = "") -> int:
    pages = retired(site)
    for (kind, pid), e in sorted(pages.items(), key=lambda kv: kv[0]):
        path = out / prefix / kind / pid / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(r.moved_page(kind, pid, e), encoding="utf-8")
    return len(pages)


def write_extra(r: Renderer, out: Path, prefix: str = "") -> int:
    """The pages a renderer split off (a page per letter of a long list, the parts of a long
    page), under `prefix` ("" or "ar/")."""
    pages = r.take_extra()
    for rel, page in pages.items():
        (out / prefix / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / prefix / rel).write_text(page, encoding="utf-8")
    return len(pages)


def write_hub_pages(r: Renderer, out: Path, prefix: str = "") -> list[str]:
    """The pages that list the views: home, Study and Research, under `prefix` ("" or "ar/").
    Returns the views found."""
    views = hub.built(out)
    for rel, page in (("index.html", r.home_page(views)), ("study/index.html", r.study_page(views)),
                      ("research/index.html", r.research_page(views, downloads_in(out)))):
        (out / prefix / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / prefix / rel).write_text(page, encoding="utf-8")
    write_extra(r, out, prefix)
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
    pages += write_extra(r, out, "ar")
    pages += write_moved(r, site, out, "ar")
    thread = build_thread(site, r.t, "ar")
    sizes = write_threads(thread, out / "ar")
    write("search/index.html", r.search_page())
    pages += write_extra(r, out, "ar")
    write_hub_pages(r, out, "ar")
    write("glossary/index.html", r.glossary_page())   # last: it lists the terms the pages linked
    return {"pages": pages + 5, "thread_bytes": max(sizes)}


def write_threads(thread: dict, out: Path) -> list[int]:
    """thread/<kind>/<id>.json, one per person and group (site/thread.py); returns their sizes."""
    sizes = []
    for key, data in thread_files(thread).items():
        path = out / "thread" / f"{key}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        path.write_text(text, encoding="utf-8")
        sizes.append(len(text.encode("utf-8")))
    return sizes


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
    split_pages = write_extra(r, out)
    moved = write_moved(r, site, out)
    index = search_index(site)
    search = write_search(index, out)
    thread = build_thread(site, r.t)
    thread_sizes = write_threads(thread, out)
    write("search/index.html", r.search_page())
    split_pages += write_extra(r, out)
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
    summary = {"pages": counts, "indexes": len(KINDS), "other": len(other), "split_pages": split_pages, "moved": moved,
               "total_html": sum(counts.values()) + len(KINDS) + len(other), "prototype_copies": len(copies),
               "views": views, "arabic_pages": arabic["pages"], "arabic_thread_bytes": arabic["thread_bytes"],
               "search_items": search["items"], "search_shards": search["shards"], "search_bytes": search["largest"],
               "thread_files": len(thread_sizes), "thread_bytes": max(thread_sizes), "thread_claims": len(thread["c"]),
               "external_matches": sum(len(v) for v in r.external.values()),
               "glossary_defined": len(glossary.listed()[0]), "glossary_needed": len(glossary.listed()[1])}
    if not quiet:
        print("built", summary["total_html"], "pages into", out, f"(+ {len(copies)} prototype copies)")
        print("  " + ", ".join(f"{k}: {v}" for k, v in counts.items()),
              f"| index pages: {summary['indexes']} | {', '.join(other)}: {len(other)}"
              f" | split off (letter pages, parts): {split_pages} | retired addresses redirected: {moved}")
        print(f"  search index: {summary['search_items']} names in {summary['search_shards']} shards,"
              f" the largest {summary['search_bytes']:,} bytes;"
              f" thread: {summary['thread_claims']} claims and links in {summary['thread_files']} files,"
              f" the largest {summary['thread_bytes']:,} bytes")
        print(f"  Arabic interface (draft) under ar/: {arabic['pages']} pages; largest thread file: {arabic['thread_bytes']:,} bytes")
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
