#!/usr/bin/env python3
"""
Lab: Badr. A prototype of an evidence-graded learning world for one event. Not a site page.

    .venv/bin/python lab/badr/people.py            # data/people.json from the joined graph's claims
    node lab/badr/sky.cjs <hyg.csv> <astronomy-engine dir>   # data/sky.json, the computed sky
    .venv/bin/python lab/badr/build.py             # fetch terrain tiles (once), write lab/badr/index.html

Every element on the page carries one of four provenance classes (docs/14 §4):
attested (a source says it), located (a gazetteer point, proposed), computed (elevation or
astronomy from stated assumptions) and schematic (layout only, claims nothing). Nothing on the
page is reviewed: the names are proposed claims from the full-book Ibn Hisham pass.
"""

import base64
import io
import json
import math
import struct
import urllib.request
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DATA = HERE / "data"
Z = 12
GRID = 160          # samples per side in the shipped heightmap
CROP = 640          # source pixels per side (z12 pixel ~ 35 m at this latitude: ~22 km square)
TILES = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

BADR = (23.72676, 38.80098, "al-Thurayya BADR_388E237N_S")
MADINAH = (24.47782, 39.60908, "al-Thurayya MADINA_396E244N_S")
MAKKAH = (21.39132, 39.83612, "al-Thurayya MAKKA_398E213N_S")


def tile_xy(lat, lon):
    n = 2 ** Z
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


def terrain():
    fx, fy = tile_xy(BADR[0], BADR[1])
    cx, cy = fx * 256, fy * 256                       # global pixel of Badr
    x0, y0 = int(cx - CROP / 2), int(cy - CROP / 2)
    tx0, ty0, tx1, ty1 = x0 // 256, y0 // 256, (x0 + CROP) // 256, (y0 + CROP) // 256
    CACHE.mkdir(exist_ok=True)
    mosaic = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            f = CACHE / f"t_{Z}_{tx}_{ty}.png"
            if not f.exists():
                f.write_bytes(urllib.request.urlopen(TILES.format(z=Z, x=tx, y=ty), timeout=60).read())
            mosaic.paste(Image.open(f).convert("RGB"), ((tx - tx0) * 256, (ty - ty0) * 256))
    ox, oy = x0 - tx0 * 256, y0 - ty0 * 256
    px = mosaic.load()
    step = CROP / GRID
    heights = []
    for j in range(GRID):
        for i in range(GRID):
            # average a step x step block, terrarium decoding
            acc, k = 0.0, 0
            for dj in range(0, int(step), 2):
                for di in range(0, int(step), 2):
                    r, g, b = px[ox + int(i * step) + di, oy + int(j * step) + dj]
                    acc += r * 256 + g + b / 256 - 32768
                    k += 1
            heights.append(acc / k)
    lo = min(heights)
    raw = struct.pack(f"<{len(heights)}H", *[max(0, min(65535, round(h - lo))) for h in heights])
    # metres per source pixel at this latitude, z12
    mpp = 40075016.686 * math.cos(math.radians(BADR[0])) / (2 ** Z * 256)
    return {"n": GRID, "size_km": round(CROP * mpp / 1000, 3), "base_m": round(lo, 1),
            "max_m": round(max(heights), 1), "h": base64.b64encode(raw).decode()}


def bearing(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    d = 2 * 6371 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
    return {"deg": round((math.degrees(math.atan2(y, x)) + 360) % 360, 1), "km": round(d)}


def people():
    src = json.loads((DATA / "people.json").read_text(encoding="utf-8"))
    code = {"ibn_ishaq": "ishq", "ibn_hisham": "hish"}
    groups, stats = {}, {}
    for key, g in (("badr_emigrants", "e"), ("badr_aws", "a"), ("badr_khazraj", "k")):
        st = stats[g] = {"stated": src[key]["stated"], "found": 0, "ishq": 0, "hish": 0, "none": 0}
        for p in src[key]["people"]:
            groups.setdefault(p["name"], []).append(g)
            st["found"] += 1
            st[code.get(p["voice"], "none")] += 1
    st = stats["all"] = {"stated": src["badr_all"]["stated"], "found": 0, "ishq": 0, "hish": 0, "none": 0}
    sections, rows = {}, []
    for p in src["badr_all"]["people"]:
        c = p["claims"][0]
        label = c["label"].replace(" (Ibn Hisham, Sira, section " + c["section"][1:].lstrip("0") + ")", "")
        sid = sections.setdefault(c["section"], [len(sections), label])[0]
        v = code.get(p["voice"], "none")
        st["found"] += 1
        st[v] += 1
        # group: first clan list holding the name; "x" = after the last clan total; "+" marks a name in two lists
        g = groups.get(p["name"], ["x"])
        rows.append([p["name"], g[0], v, 1 if p["share"] else 0, sid, c["gloss"] if p["share"] else "", "".join(g)])
    return {"rows": rows, "sections": [[k, v[1]] for k, v in sorted(sections.items(), key=lambda kv: kv[1][0])], "stats": stats}


def main():
    sky = json.loads((DATA / "sky.json").read_text(encoding="utf-8"))
    data = {
        "terrain": terrain(),
        "sky": sky,
        "people": people(),
        "places": {"badr": BADR, "madinah": MADINAH, "makkah": MAKKAH,
                   "to_madinah": bearing(BADR, MADINAH), "to_makkah": bearing(BADR, MAKKAH)},
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = (HERE / "template.html").read_text(encoding="utf-8").replace("/*__DATA__*/null", blob)
    (HERE / "index.html").write_text(html, encoding="utf-8")
    # the same page without its document wrapper, for publishing as a claude.ai artifact (the host adds it)
    bare = html
    for tag in ("<!doctype html>\n", '<html lang="en" dir="ltr">\n', "<head>\n", '<meta charset="utf-8">\n',
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n', "</head>\n", "<body>\n", "</body>\n", "</html>\n"):
        assert tag in bare, tag
        bare = bare.replace(tag, "", 1)
    (HERE / "artifact.html").write_text(bare, encoding="utf-8")
    print(f"index.html {len(html.encode()) / 1024:.0f} KB; terrain {data['terrain']['size_km']} km, "
          f"{data['terrain']['base_m']}-{data['terrain']['max_m']} m; Madinah {data['places']['to_madinah']}, "
          f"Makkah {data['places']['to_makkah']}; {len(data['people']['rows'])} names")


if __name__ == "__main__":
    main()
