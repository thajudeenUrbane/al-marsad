#!/usr/bin/env python3
"""Derive the map page's basemap from Natural Earth land polygons.

    .venv/bin/python site/interactive/tools/make_basemap.py SRC [--out site/interactive/data/basemap.json]

SRC is Natural Earth's 1:50m land layer as GeoJSON, version 5.1.2:
    https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_50m_land.geojson
Natural Earth is in the public domain ("All versions of Natural Earth raster + vector map
data found on this website are in the public domain", LICENSE.md in the same repository,
https://www.naturalearthdata.com/about/terms-of-use/).

The output is land only: no borders, no names, no rivers, nothing that dates or places
anything. It is clipped to the region around the Arabian Peninsula and the Red Sea,
simplified (Douglas-Peucker) and rounded to two decimals, so that it is a few kilobytes. Its "source" block records where it came from and how it was made.
Standard library only; deterministic for the same input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

SOURCE_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/"
              "geojson/ne_50m_land.geojson")
SOURCE_SHA256 = "e874b27a51d146452be360cafb3cc50c86001074a67d534113e6534682f9826b"

# One layer: (name, west, south, east, north, tolerance in degrees, decimals)
LAYERS = (("land", 30.0, 10.0, 60.0, 36.0, 0.02, 2),)
MIN_RING_POINTS = 4


def clip_ring(ring, w, s, e, n):
    """Sutherland-Hodgman: clip one closed ring to an axis-aligned rectangle."""
    def clip(points, inside, cross):
        out = []
        if not points:
            return out
        prev = points[-1]
        for cur in points:
            if inside(cur):
                if not inside(prev):
                    out.append(cross(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cross(prev, cur))
            prev = cur
        return out

    def at_x(x):
        return lambda p, q: (x, p[1] + (q[1] - p[1]) * (x - p[0]) / (q[0] - p[0]))

    def at_y(y):
        return lambda p, q: (p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1]), y)

    pts = [tuple(p) for p in ring]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    pts = clip(pts, lambda p: p[0] >= w, at_x(w))
    pts = clip(pts, lambda p: p[0] <= e, at_x(e))
    pts = clip(pts, lambda p: p[1] >= s, at_y(s))
    pts = clip(pts, lambda p: p[1] <= n, at_y(n))
    return pts


def simplify(points, tol):
    """Douglas-Peucker on an open polyline (iterative)."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = points[a]
        bx, by = points[b]
        dx, dy = bx - ax, by - ay
        seg = math.hypot(dx, dy)
        best, idx = -1.0, -1
        for i in range(a + 1, b):
            px, py = points[i]
            d = (abs(dy * px - dx * py + bx * ay - by * ax) / seg) if seg else math.hypot(px - ax, py - ay)
            if d > best:
                best, idx = d, i
        if idx >= 0 and best > tol:
            keep[idx] = True
            stack.append((a, idx))
            stack.append((idx, b))
    return [p for p, k in zip(points, keep) if k]


def simplify_ring(ring, tol):
    """Simplify a closed ring: split at the point farthest from the first, simplify both halves."""
    if len(ring) < MIN_RING_POINTS:
        return ring
    far = max(range(len(ring)), key=lambda i: math.hypot(ring[i][0] - ring[0][0], ring[i][1] - ring[0][1]))
    first = simplify(ring[: far + 1], tol)
    second = simplify(ring[far:] + [ring[0]], tol)
    return first[:-1] + second[:-1]


def area(ring):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]))) / 2


def layer(features, name, w, s, e, n, tol, decimals):
    rings = []
    for f in features:
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in polys:
            for ring in poly:
                xs = [p[0] for p in ring]
                ys = [p[1] for p in ring]
                if max(xs) < w or min(xs) > e or max(ys) < s or min(ys) > n:
                    continue
                clipped = clip_ring(ring, w, s, e, n)
                if len(clipped) < MIN_RING_POINTS:
                    continue
                simple = simplify_ring(clipped, tol)
                rounded = []
                for x, y in simple:
                    p = [round(x, decimals), round(y, decimals)]
                    if not rounded or p != rounded[-1]:
                        rounded.append(p)
                if len(rounded) >= MIN_RING_POINTS and area(rounded) >= tol * tol * 4:
                    rings.append(rounded)
    rings.sort(key=lambda r: (-area(r), r[0]))
    return {"bbox": [w, s, e, n], "tolerance_degrees": tol, "rings": rings}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "data" / "basemap.json"))
    a = ap.parse_args(argv)
    raw = Path(a.src).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_SHA256:
        print(f"warning: {a.src} is not the recorded file (sha256 {digest})", file=sys.stderr)
    features = json.loads(raw)["features"]
    out = {
        "source": {
            "name": "Natural Earth, 1:50m land polygons (ne_50m_land), version 5.1.2",
            "url": SOURCE_URL,
            "sha256": digest,
            "licence": "public domain",
            "licence_url": "https://www.naturalearthdata.com/about/terms-of-use/",
            "processing": ("clipped to each layer's bbox (Sutherland-Hodgman), simplified with "
                           "Douglas-Peucker at the layer's tolerance, rounded; rings smaller than "
                           "four times the tolerance squared dropped; made by "
                           "site/interactive/tools/make_basemap.py"),
        },
        "content": "land polygons only: no borders, names, rivers or dates",
        "layers": {name: layer(features, name, w, s, e, n, tol, dec) for name, w, s, e, n, tol, dec in LAYERS},
    }
    text = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(text + "\n", encoding="utf-8")
    pts = {k: sum(len(r) for r in v["rings"]) for k, v in out["layers"].items()}
    print(f"wrote {a.out}: {len(text):,} bytes; points per layer: {pts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
