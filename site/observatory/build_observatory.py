#!/usr/bin/env python3
"""Builds the L1 Observatory: one self-contained page over the unified graph.

    .venv/bin/python site/observatory/build_observatory.py [--graph build/graph.ttl]
        [--out site/dist/observatory] [--reader-base ../] [--ask-url URL]

Reads build/graph.ttl only (runs ontology/build_graph.py if it is missing), through
site/model.py and site/display.py, so names, dates and statuses match the reader
pages. Writes one index.html with its CSS, script, strings and data inlined: no
external request, system fonts only, under 2 MB. The page also works when published
on its own as a single file (links to reader pages then point at the main site).

Standalone: this script does not touch site/build.py or its output, except that when
it has to create site/dist itself it leaves the marker site/build.py looks for, so a
later reader-tier build may clear and rebuild site/dist as usual.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
ROOT = SITE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SITE))

import display  # noqa: E402
from frames import compute_frames  # noqa: E402
from model import Site  # noqa: E402
from obsdata import ABSENCE_PREDICATES, ObsData, Translator  # noqa: E402

BUDGET = 2_000_000
SITE_MARKER = ".al-marsad-site"  # the marker site/build.py checks before clearing site/dist
SITE_MARKER_TEXT = "made by site/build.py; safe to delete and rebuild\n"
URL_LICENSING = "https://github.com/thajudeenUrbane/al-marsad/blob/main/LICENSING.md"
URL_CC_BY_SA = "https://creativecommons.org/licenses/by-sa/4.0/"
URL_AGPL = "https://www.gnu.org/licenses/agpl-3.0.html"


# --------------------------------------------------------------------------- vantage presets
def _fold(s: str) -> str:
    return display.fold(s).lower().replace("\ufdfa", "").strip()


def find(data, kinds, pattern) -> list[int]:
    rx = re.compile(pattern)
    return [i for i, nd in enumerate(data.nodes) if nd["k"] in kinds and rx.search(_fold(nd["n"]))]


def neighbours(data, i, classes=None, skip_absence=True) -> set[int]:
    out = set()
    for li in data.adj[i]:
        l = data.links[li]
        if classes and l["c"] not in classes:
            continue
        if skip_absence and all(data.claims[ci].get("pk") in ABSENCE_PREDICATES for ci in l["cl"]):
            continue
        out.add(l["b"] if l["a"] == i else l["a"])
    return out


def _window(data, items) -> list[int] | None:
    spans = [m for i in items for m in data.nodes[i]["_marks"]]
    if not spans:
        return None
    y0 = int(min(m[0] for m in spans))
    y1 = int(max(m[1] for m in spans) - 1e-6)
    return [y0, max(y0, y1)]


def find_presets(data, log) -> list[dict]:
    """Vantage points (docs/00 §3.5), found by name in the graph. A preset whose data
    is missing or ambiguous is skipped and reported, never forced."""
    out = []
    # 1. The Hijrah from Abu Bakr's side
    ab = find(data, ("person",), r"^abu bakr\b")
    hij = find(data, ("event", "story"), r"\bhijra|\bthawr\b")
    if len(ab) == 1 and hij:
        a = ab[0]
        hl = {a, *hij}
        near_ab = neighbours(data, a)
        for h in hij:
            for x in neighbours(data, h):
                if x in near_ab or data.nodes[x]["k"] == "place":
                    hl.add(x)
        out.append({"key": "hijrah_abubakr", "focus": a, "hl": sorted(hl), "frame": "network",
                    "win": _window(data, hij), "found": [data.nodes[a]["n"]] + [data.nodes[h]["n"] for h in hij]})
    else:
        log(f"preset hijrah_abubakr skipped: {len(ab)} person(s) named Abu Bakr, {len(hij)} Hijrah item(s)")
    # 2. The people of Badr
    badr = find(data, ("event", "story", "group", "place"), r"\bbadr\b")
    battle = [i for i in badr if data.nodes[i]["k"] == "event"]
    if badr and battle:
        hl = set(badr)
        for b in badr:
            hl |= {x for x in neighbours(data, b) if data.nodes[x]["k"] in ("person", "group")}
        out.append({"key": "badr", "focus": battle[0], "hl": sorted(hl), "frame": "network", "win": None,
                    "found": [data.nodes[i]["n"] for i in badr]})
    else:
        log("preset badr skipped: no event named Badr")
    # 3. The first believers
    fb = find(data, ("story", "event", "group"), r"\bfirst believers\b")
    if len(fb) >= 1:
        s = fb[0]
        out.append({"key": "first_believers", "focus": s, "hl": sorted({s, *neighbours(data, s)}), "frame": "stories",
                    "win": None, "found": [data.nodes[s]["n"]]})
    else:
        log("preset first_believers skipped: no story named 'the first believers'")
    # 4. Family around the Prophet
    prophet = [i for i, nd in enumerate(data.nodes) if nd["k"] == "person" and nd["_ent"].prophet]
    if len(prophet) == 1:
        p = prophet[0]
        fam = neighbours(data, p, classes=("kinship",))
        if fam:
            out.append({"key": "family", "focus": p, "hl": sorted({p, *fam}), "frame": "network", "win": None,
                        "cls": ["kinship"], "found": [data.nodes[p]["n"]]})
        else:
            log("preset family skipped: no kinship claim recorded for the Prophet")
    else:
        log(f"preset family skipped: {len(prophet)} person(s) recognised as the Prophet")
    # 5. The one chain
    if data.chains and data.chains[0]["links"]:
        ch = data.chains[0]
        hl = {x for ln in ch["links"] for x in ln[:2]}
        if ch["collector"] is not None:
            hl.add(ch["collector"])
        out.append({"key": "chain", "focus": None, "hl": sorted(hl), "frame": "isnad", "win": None,
                    "found": [ch["label"] or ""]})
    else:
        log("preset chain skipped: no transmission chain in the graph")
    return out


# --------------------------------------------------------------------------- page
def _json_for_script(obj) -> str:
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def payload(data: ObsData, frames: dict, presets: list[dict], reader_base: str, ask: str | None) -> dict:
    nodes = []
    for nd in data.nodes:
        out = {k: v for k, v in nd.items() if not k.startswith("_")}
        if nd["_marks"]:
            out["mk"] = [[round(m[0], 3), round(m[1], 3)] for m in nd["_marks"]]
        if nd["_places"] and nd["k"] != "place":
            out["pl"] = nd["_places"][0]
        nodes.append(out)
    return {
        "meta": {"version": data.fingerprint(), "counts": data.counts(), "readerBase": reader_base, "ask": ask},
        "nodes": nodes,
        "links": data.links,
        "claims": data.claims,
        "sources": data.sources,
        "strings": data.strings,
        "reports": data.reports,
        "chains": [{k: v for k, v in ch.items()} for ch in data.chains],
        "frames": frames,
        "presets": [{k: v for k, v in p.items() if k != "found"} for p in presets],
    }


STATIC = HERE / "static"
TEMPLATE = STATIC / "template.html"
CSS_FILES = (STATIC / "observatory.css",)
# the renderer first: observatory.js calls the window.MarsadRenderer it defines
JS_FILES = (STATIC / "render2d.js", STATIC / "observatory.js")


def render(strings: dict, data_json: str, ask: str | None, reader_base: str,
           template: Path = TEMPLATE, css_files=CSS_FILES, js_files=JS_FILES) -> str:
    """The page: one template with its CSS, script, strings and data inlined. The Sky
    (site/sky/build_sky.py) calls this with its own template, a second stylesheet and
    its own renderer in place of render2d.js."""
    tpl = template.read_text(encoding="utf-8")
    css = "\n".join(f.read_text(encoding="utf-8") for f in css_files)
    js = "\n".join(f.read_text(encoding="utf-8") for f in js_files)
    if "</script" in js.lower() or "</style" in css.lower():
        raise ValueError("inline script or style would close its own tag")
    t = Translator(strings)
    ask_html = f'<a class="btn" href="{html.escape(ask)}">{html.escape(t("nav.ask"))}</a>' if ask else ""
    values = {
        "CSS": css, "JS": js, "DATA": data_json, "I18N": _json_for_script(strings), "ASK": ask_html,
        "READER_HOME": html.escape(reader_base), "URL_LICENSING": URL_LICENSING,
        "URL_CC_BY_SA": URL_CC_BY_SA, "URL_AGPL": URL_AGPL,
    }

    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key.startswith("t:"):
            return html.escape(t(key[2:]))
        return values[key]

    return re.sub(r"\{\{([A-Z0-9_]+|t:[a-z0-9_.]+)\}\}", sub, tpl)


def build(graph: Path, out: Path, reader_base: str = "../", ask: str | None = None, quiet: bool = False) -> dict:
    if not graph.exists():
        print(f"{graph} not found; running ontology/build_graph.py", file=sys.stderr)
        subprocess.run([sys.executable, str(ROOT / "ontology" / "build_graph.py")], check=True, cwd=ROOT)
    strings = json.loads((HERE / "i18n" / "en.json").read_text(encoding="utf-8"))
    t = Translator(strings)
    site = Site(graph)
    data = ObsData(site, t)
    frames = compute_frames(data, t)
    notes: list[str] = []
    presets = find_presets(data, notes.append)
    if ask is None:
        default_ask = out.parent / "ask" / "index.html"
        ask = "../ask/" if default_ask.exists() else None
    page = render(strings, _json_for_script(payload(data, frames, presets, reader_base, ask)), ask, reader_base)
    size = len(page.encode("utf-8"))
    if size > BUDGET:
        raise SystemExit(f"observatory page is {size:,} bytes, over the {BUDGET:,}-byte budget")
    if not out.parent.exists():
        out.parent.mkdir(parents=True)
        (out.parent / SITE_MARKER).write_text(SITE_MARKER_TEXT, encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    counts = data.counts()
    summary = {"bytes": size, "nodes": len(data.nodes), "links": len(data.links), "claims": len(data.claims),
               "presets": [p["key"] for p in presets], "skipped": notes, "ask": ask, "counts": counts}
    if not quiet:
        print(f"wrote {out / 'index.html'} ({size:,} bytes; budget {BUDGET:,})")
        print(f"  {len(data.nodes)} items, {len(data.links)} links, {len(data.claims)} claims and records")
        print(f"  frames: {', '.join(frames)}; presets: {', '.join(summary['presets']) or 'none'}")
        for note in notes:
            print("  " + note)
        print(f"  ask link: {ask or 'hidden (no ask page found)'}")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", default=str(ROOT / "build" / "graph.ttl"))
    ap.add_argument("--out", default=str(SITE / "dist" / "observatory"))
    ap.add_argument("--reader-base", default="../", help="URL prefix of the reader pages (default ../)")
    ap.add_argument("--ask-url", default=None, help="link for the Ask verb; default: ../ask/ if that page exists")
    a = ap.parse_args(argv)
    build(Path(a.graph), Path(a.out), a.reader_base, a.ask_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
