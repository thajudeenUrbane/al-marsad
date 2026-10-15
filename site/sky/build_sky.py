#!/usr/bin/env python3
"""Builds the Sky: the Observatory's graph as a three-dimensional sky, in one page.

    .venv/bin/python site/sky/build_sky.py [--graph build/graph.ttl]
        [--out site/dist/sky] [--reader-base ../] [--ask-url URL]

Everything the Observatory has, the Sky has, because it is the same page logic
(site/observatory/static/observatory.js) over the same data (site/observatory/obsdata.py,
frames.py and the vantage presets of build_observatory.py) with a different renderer
(static/render3d.js) and one more frame: the Sky itself (skylayout.py), which takes the
place of the flat Relationship layout. The Time, Geography, Stories and Transmission
frames are the Observatory's, lying flat inside the sky.

Reads build/graph.ttl only (runs ontology/build_graph.py if it is missing). Writes one
index.html with its CSS, script, strings and data inlined: no external request, system
fonts only, under 2 MB. New records in the graph become new stars on the next build:
nothing about any person is written here.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
ROOT = SITE.parent
OBS = SITE / "observatory"
for p in (HERE, OBS, SITE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import build_observatory as bo  # noqa: E402
from frames import compute_frames  # noqa: E402
from model import Site  # noqa: E402
from obsdata import ObsData, Translator  # noqa: E402
from skylayout import sky_frame  # noqa: E402

BUDGET = bo.BUDGET
TEMPLATE = HERE / "static" / "template.html"
CSS_FILES = (OBS / "static" / "observatory.css", HERE / "static" / "sky.css")
JS_FILES = (HERE / "static" / "render3d.js", OBS / "static" / "observatory.js")


def strings() -> dict:
    """The Observatory's strings with the Sky's own on top (same keys win)."""
    out = json.loads((OBS / "i18n" / "en.json").read_text(encoding="utf-8"))
    out.update(json.loads((HERE / "i18n" / "en.json").read_text(encoding="utf-8")))
    return out


def light_index(data, log) -> int | None:
    """The one person the reader tier recognises as the Prophet ﷺ (site/display.py), or
    None if there is not exactly one: then no light is drawn and the build says so."""
    found = [i for i, nd in enumerate(data.nodes) if nd["k"] == "person" and nd["_ent"].prophet]
    if len(found) != 1:
        log(f"no light drawn: {len(found)} person(s) recognised as the Prophet")
        return None
    return found[0]


def build(graph: Path, out: Path, reader_base: str = "../", ask: str | None = None, quiet: bool = False) -> dict:
    if not graph.exists():
        print(f"{graph} not found; running ontology/build_graph.py", file=sys.stderr)
        subprocess.run([sys.executable, str(ROOT / "ontology" / "build_graph.py")], check=True, cwd=ROOT)
    s = strings()
    t = Translator(s)
    data = ObsData(Site(graph), t)
    frames = compute_frames(data, t)
    notes: list[str] = []
    presets = bo.find_presets(data, notes.append)
    light = light_index(data, notes.append)
    sky = sky_frame(data, light)
    # the Sky takes the Relationship frame's place: same key, so view states and presets carry over
    frames["network"] = {"pos": [], "deco": [], "region": sky["region"], "pos3": sky["pos3"], "ring": sky["ring"]}
    if ask is None:
        ask = "../ask/" if (out.parent / "ask" / "index.html").exists() else None
    pl = bo.payload(data, frames, presets, reader_base, ask)
    pl["meta"]["light"] = light
    pl["meta"]["shells"] = sky["shells"]
    page = bo.render(s, bo._json_for_script(pl), ask, reader_base, template=TEMPLATE, css_files=CSS_FILES, js_files=JS_FILES)
    size = len(page.encode("utf-8"))
    if size > BUDGET:
        raise SystemExit(f"sky page is {size:,} bytes, over the {BUDGET:,}-byte budget")
    if not out.parent.exists():
        out.parent.mkdir(parents=True)
        (out.parent / bo.SITE_MARKER).write_text(bo.SITE_MARKER_TEXT, encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    summary = {"bytes": size, "nodes": len(data.nodes), "links": len(data.links), "light": light,
               "presets": [p["key"] for p in presets], "skipped": notes, "ask": ask, "counts": data.counts()}
    if not quiet:
        print(f"wrote {out / 'index.html'} ({size:,} bytes; budget {BUDGET:,})")
        print(f"  {len(data.nodes)} items, {len(data.links)} links; light: {data.nodes[light]['n'] if light is not None else 'none'}")
        regions = {r: sky["region"].count(r) for r in sorted(set(sky["region"]))}
        print("  sky: " + ", ".join(f"{k} {v}" for k, v in regions.items()))
        print(f"  presets: {', '.join(summary['presets']) or 'none'}")
        for note in notes:
            print("  " + note)
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", default=str(ROOT / "build" / "graph.ttl"))
    ap.add_argument("--out", default=str(SITE / "dist" / "sky"))
    ap.add_argument("--reader-base", default="../", help="URL prefix of the reader pages (default ../)")
    ap.add_argument("--ask-url", default=None, help="link for the Ask verb; default: ../ask/ if that page exists")
    a = ap.parse_args(argv)
    build(Path(a.graph), Path(a.out), a.reader_base, a.ask_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
