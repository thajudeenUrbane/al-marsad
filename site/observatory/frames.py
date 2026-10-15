"""The five coordinate frames of the morph field (docs/04 §2), computed offline.

Every node gets a position in every frame. A node that a frame cannot place from
recorded data (no date, no located place, no story, no chain) goes on that frame's
labelled shelf, never onto the axis, the map, the dial or the chain.

Positions are deterministic: the force layout starts each node at a point derived from
a hash of its IRI (so adding a node does not move the starting point of any other),
iterates in a fixed order with fixed constants, and every coordinate is rounded to one
decimal. Frames share one world space, about 1000 units wide.
"""
from __future__ import annotations

import hashlib
import math

from obsdata import KIND_ORDER, TABAQA_ORDER

WIDTH = 1000.0
GOLDEN = math.pi * (3 - math.sqrt(5))


def _h01(key: str, salt: str) -> float:
    d = hashlib.sha256(f"{salt}|{key}".encode("utf-8")).digest()
    return int.from_bytes(d[:8], "big") / 2.0 ** 64


def _r(v: float) -> float:
    return round(v, 1) + 0.0  # + 0.0 turns -0.0 into 0.0


# --------------------------------------------------------------------------- shelves
def shelf(data, members: list[int], top: float, heading: str, t, pos: dict, deco: list,
          region: dict, region_name: str = "shelf", cell: float = 22.0, width: float = WIDTH) -> float:
    """Lay members out in a labelled grid below y=top, grouped by kind. Text sits a
    fixed number of pixels above the row it labels ("dy"), so it never overlaps at
    any zoom. Returns the y below the shelf."""
    if not members:
        return top
    y = top + 80
    deco.append({"t": "text", "x": -width / 2, "y": y, "dy": -40, "s": heading, "a": "start", "z": 13, "w": 600})
    deco.append({"t": "line", "x1": -width / 2, "y1": y, "x2": width / 2, "y2": y, "dy": -33, "o": 0.35})
    per_row = max(1, int(width // cell))
    by_kind = {k: [] for k in KIND_ORDER}
    for i in members:
        by_kind[data.nodes[i]["k"]].append(i)
    for kind in KIND_ORDER:
        items = sorted(by_kind[kind], key=lambda i: (data.nodes[i]["n"].lower(), data.nodes[i]["id"]))
        if not items:
            continue
        deco.append({"t": "text", "x": -width / 2, "y": y, "dy": -11, "s": t(f"shelf.kind.{kind}", n=len(items)), "a": "start", "z": 11, "o": 0.8})
        for j, i in enumerate(items):
            r, c = divmod(j, per_row)
            pos[i] = (-width / 2 + cell / 2 + c * cell, y + r * cell)
            region[i] = region_name
        rows = (len(items) + per_row - 1) // per_row
        y += (rows - 1) * cell + 34
    return y


# --------------------------------------------------------------------------- network
def force_layout(keys: list[str], edges: list[tuple[int, int]], iterations: int = 450) -> list[tuple[float, float]]:
    """Spring layout with hub-normalised springs: every pair of nodes repels (k/d), every
    recorded link pulls like a spring whose stiffness is 1/sqrt(deg(a)*deg(b)), so a
    story or event gathers its own people while a node linked to everything does not
    pull everything into one ball. Weak gravity keeps the part round. A linearly cooling
    step limit; deterministic for the same keys and edges. No degree changes any size."""
    n = len(keys)
    if n == 0:
        return []
    deg = [0] * n
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    w = [1.0 / math.sqrt(deg[a] * deg[b]) for a, b in edges]
    spread = 14.0 * math.sqrt(n)
    xs = [(_h01(k, "x") * 2 - 1) * spread for k in keys]
    ys = [(_h01(k, "y") * 2 - 1) * spread for k in keys]
    kr, ka, kg = 120.0, 0.6, 0.012
    t0 = spread * 0.2
    for it in range(iterations):
        dx = [0.0] * n
        dy = [0.0] * n
        for i in range(n):
            xi, yi = xs[i], ys[i]
            fx = fy = 0.0
            for j in range(i + 1, n):
                ddx = xi - xs[j]
                ddy = yi - ys[j]
                f = kr / (ddx * ddx + ddy * ddy + 0.5)
                ddx *= f
                ddy *= f
                fx += ddx
                fy += ddy
                dx[j] -= ddx
                dy[j] -= ddy
            dx[i] += fx
            dy[i] += fy
        for e, (a, b) in enumerate(edges):
            f = ka * w[e]
            ddx = (xs[a] - xs[b]) * f
            ddy = (ys[a] - ys[b]) * f
            dx[a] -= ddx
            dy[a] -= ddy
            dx[b] += ddx
            dy[b] += ddy
        temp = t0 * (1.0 - it / iterations) + 0.05
        for i in range(n):
            gx = dx[i] - kg * xs[i]
            gy = dy[i] - kg * ys[i]
            L = math.sqrt(gx * gx + gy * gy)
            if L > 0:
                s = min(L, temp) / L
                xs[i] += gx * s
                ys[i] += gy * s
    return list(zip(xs, ys))


def _fit(points: dict, width: float = WIDTH, height: float | None = None, top: float | None = None) -> dict:
    """Scale and centre points so they span `width` (and at most `height`)."""
    if not points:
        return {}
    xs = [p[0] for p in points.values()]
    ys = [p[1] for p in points.values()]
    w = (max(xs) - min(xs)) or 1.0
    h = (max(ys) - min(ys)) or 1.0
    s = width / w
    if height is not None:
        s = min(s, height / h)
    cx = (max(xs) + min(xs)) / 2
    cy = (max(ys) + min(ys)) / 2
    oy = 0.0 if top is None else top + h * s / 2
    return {i: ((x - cx) * s, (y - cy) * s + oy) for i, (x, y) in points.items()}


def _components(n: int, pairs) -> list[list[int]]:
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return sorted(groups.values(), key=lambda g: (-len(g), g[0]))


def network_frame(data, t) -> dict:
    """The largest connected part by force layout; smaller parts laid out the same way
    and set in a row beneath it; items with no recorded link on a shelf."""
    n = len(data.nodes)
    pairs = sorted({(min(l["a"], l["b"]), max(l["a"], l["b"])) for l in data.links if l["a"] != l["b"]})
    comps = [c for c in _components(n, pairs) if len(c) > 1]
    pos, deco, region = {}, [], {}
    scale = None
    row_x, row_y, row_h = -WIDTH / 2, None, 0.0
    for ci, comp in enumerate(comps):
        local_ix = {g: k for k, g in enumerate(comp)}
        cp = [(local_ix[a], local_ix[b]) for a, b in pairs if a in local_ix]
        xy = force_layout([data.nodes[i]["_iri"] for i in comp], cp, iterations=500 if ci == 0 else 200)
        if ci == 0:
            pts = _fit({comp[k]: xy[k] for k in range(len(comp))}, width=WIDTH, height=WIDTH)
            raw_w = (max(p[0] for p in xy) - min(p[0] for p in xy)) or 1.0
            raw_h = (max(p[1] for p in xy) - min(p[1] for p in xy)) or 1.0
            scale = min(WIDTH / raw_w, WIDTH / raw_h)
            row_y = max(p[1] for p in pts.values()) + 70
            if len(comps) > 1:
                deco.append({"t": "text", "x": -WIDTH / 2, "y": row_y, "dy": -16, "s": t("frame.network.parts"), "a": "start", "z": 11, "o": 0.75})
        else:
            x0 = min(p[0] for p in xy)
            y0 = min(p[1] for p in xy)
            w = (max(p[0] for p in xy) - x0) * scale
            h = (max(p[1] for p in xy) - y0) * scale
            if row_x + w > WIDTH / 2 and row_x > -WIDTH / 2:
                row_x = -WIDTH / 2
                row_y += row_h + 30
                row_h = 0.0
            pts = {comp[k]: (row_x + (xy[k][0] - x0) * scale, row_y + (xy[k][1] - y0) * scale) for k in range(len(comp))}
            row_x += w + 40
            row_h = max(row_h, h)
        for i, p in pts.items():
            pos[i] = p
            region[i] = "main"
    isolated = [i for i in range(n) if i not in pos]
    bottom = max((p[1] for p in pos.values()), default=0.0)
    shelf(data, isolated, bottom + 60, t("frame.network.shelf"), t, pos, deco, region)
    return {"pos": pos, "deco": deco, "region": region}


# --------------------------------------------------------------------------- time
def _year_ticks(y0: int, y1: int) -> list[int]:
    span = y1 - y0
    step = 5 if span <= 80 else 10 if span <= 200 else 50
    first = int(math.ceil(y0 / step) * step)
    return list(range(first, y1 + 1, step))


def time_frame(data, t) -> dict:
    pos, deco, region, marks = {}, [], {}, {}
    dated = [i for i, nd in enumerate(data.nodes) if nd["_marks"]]
    if dated:
        lo = min(m[0] for i in dated for m in data.nodes[i]["_marks"])
        hi = max(m[1] for i in dated for m in data.nodes[i]["_marks"])
        y0 = int(math.floor(lo / 5.0) * 5)
        y1 = int(math.ceil(hi / 5.0) * 5)
        if y1 <= y0:
            y1 = y0 + 5
    else:
        y0, y1 = 600, 700
    X = lambda yr: -WIDTH / 2 + (yr - y0) / (y1 - y0) * WIDTH  # noqa: E731
    axis_y = -40.0
    deco.append({"t": "text", "x": -WIDTH / 2, "y": axis_y, "dy": -30, "s": t("frame.time.axis_title"), "a": "start", "z": 13, "w": 600})
    deco.append({"t": "line", "x1": -WIDTH / 2, "y1": axis_y, "x2": WIDTH / 2, "y2": axis_y, "o": 0.7})
    for yr in _year_ticks(y0, y1):
        x = X(yr)
        deco.append({"t": "line", "x1": x, "y1": axis_y - 5, "x2": x, "y2": axis_y + 5, "o": 0.7})
        deco.append({"t": "text", "x": x, "y": axis_y, "dy": -9, "s": t("frame.time.tick", year=yr), "a": "middle", "z": 11, "o": 0.85})
    lanes = [("event", t("frame.time.lane_events")), ("story", t("frame.time.lane_stories")),
             ("person", t("frame.time.lane_people")), ("group", t("frame.time.lane_groups")),
             ("place", t("frame.time.lane_places"))]
    y = axis_y + 44
    row_h = 15.0
    lane_bounds = []
    for kind, label in lanes:
        items = [i for i in dated if data.nodes[i]["k"] == kind]
        if not items:
            continue
        items.sort(key=lambda i: (data.nodes[i]["_marks"][0][0], data.nodes[i]["_marks"][-1][1], data.nodes[i]["n"].lower(), data.nodes[i]["id"]))
        deco.append({"t": "text", "x": -WIDTH / 2, "y": y, "dy": -12, "s": label, "a": "start", "z": 12, "w": 600})
        top = y
        rows_end: list[float] = []
        for i in items:
            ms = data.nodes[i]["_marks"]
            hx0 = X(min(m[0] for m in ms))
            hx1 = max(X(max(m[1] for m in ms)), hx0 + 10)
            first = ms[0]
            nx = (X(first[0]) + X(first[1])) / 2
            hx0 = min(hx0, nx - 6)
            hx1 = max(hx1, nx + 6)
            row = next((r for r, end in enumerate(rows_end) if end + 4 <= hx0), None)
            if row is None:
                row = len(rows_end)
                rows_end.append(hx1)
            else:
                rows_end[row] = hx1
            pos[i] = (nx, top + row * row_h)
            region[i] = "axis"
            marks[i] = [[_r(X(m[0])), _r(max(X(m[1]), X(m[0]) + 1.5))] for m in ms]
        bottom = top + max(1, len(rows_end)) * row_h
        lane_bounds.append((label, y - 12, bottom))
        deco.append({"t": "line", "x1": -WIDTH / 2, "y1": bottom + 6, "x2": WIDTH / 2, "y2": bottom + 6, "o": 0.25})
        y = bottom + 44
    # generation band: people with a recorded tabaqa but no dated mark
    band = [i for i, nd in enumerate(data.nodes) if nd["k"] == "person" and not nd["_marks"] and nd.get("tb")]
    if band:
        y += 70
        deco.append({"t": "text", "x": -WIDTH / 2, "y": y, "dy": -48, "s": t("frame.time.band_title"), "a": "start", "z": 13, "w": 600})
        deco.append({"t": "text", "x": -WIDTH / 2, "y": y, "dy": -33, "s": t("frame.time.band_note"), "a": "start", "z": 11, "o": 0.8})
        deco.append({"t": "line", "x1": -WIDTH / 2, "y1": y, "x2": WIDTH / 2, "y2": y, "dy": -26, "o": 0.35})
        order = {k: n for n, k in enumerate(TABAQA_ORDER)}
        keys = sorted({data.nodes[i].get("tbk") for i in band}, key=lambda k: (order.get(k, 99), k or ""))
        col_w = WIDTH / max(1, len(keys))
        cell = 22.0
        per_row = max(1, int((col_w - 20) // cell))
        tallest = 0
        for c, key in enumerate(keys):
            members = sorted([i for i in band if data.nodes[i].get("tbk") == key], key=lambda i: (data.nodes[i]["n"].lower(), data.nodes[i]["id"]))
            x0 = -WIDTH / 2 + c * col_w
            label = data.nodes[members[0]]["tb"]
            deco.append({"t": "text", "x": x0, "y": y, "dy": -11, "s": t("frame.time.band_column", label=label, n=len(members)), "a": "start", "z": 12})
            for j, i in enumerate(members):
                r, cc = divmod(j, per_row)
                pos[i] = (x0 + cell / 2 + cc * cell, y + r * cell)
                region[i] = "band"
            tallest = max(tallest, (len(members) + per_row - 1) // per_row)
        y = y + (tallest - 1) * cell + 20
    rest = [i for i in range(len(data.nodes)) if i not in pos]
    shelf(data, rest, y, t("frame.time.shelf"), t, pos, deco, region)
    return {"pos": pos, "deco": deco, "region": region, "marks": marks,
            "axis": {"y0": y0, "y1": y1, "x0": -WIDTH / 2, "x1": WIDTH / 2}}


# --------------------------------------------------------------------------- geography
def geo_frame(data, t) -> dict:
    pos, deco, region = {}, [], {}
    located = [i for i, nd in enumerate(data.nodes) if nd["k"] == "place" and "geo" in nd]
    height = 820.0
    if located:
        lons = [data.nodes[i]["geo"][0] for i in located]
        lats = [data.nodes[i]["geo"][1] for i in located]
        lon0 = (min(lons) + max(lons)) / 2
        lat0 = (min(lats) + max(lats)) / 2
        kx = math.cos(math.radians(lat0))
        span = max((max(lons) - min(lons)) * kx, max(lats) - min(lats), 0.5)
        S = height / span
        P = lambda lon, lat: ((lon - lon0) * kx * S, -(lat - lat0) * S)  # noqa: E731
        # graticule every degree around the located places
        lo_lon, hi_lon = math.floor(min(lons)) - 1, math.ceil(max(lons)) + 1
        lo_lat, hi_lat = math.floor(min(lats)) - 1, math.ceil(max(lats)) + 1
        for lon in range(lo_lon, hi_lon + 1):
            xa, ya = P(lon, lo_lat)
            xb, yb = P(lon, hi_lat)
            deco.append({"t": "line", "x1": xa, "y1": ya, "x2": xb, "y2": yb, "o": 0.18})
            deco.append({"t": "text", "x": xa, "y": ya, "dy": 13, "s": t("frame.geo.lon", deg=lon), "a": "middle", "z": 10, "o": 0.6})
        for lat in range(lo_lat, hi_lat + 1):
            xa, ya = P(lo_lon, lat)
            xb, yb = P(hi_lon, lat)
            deco.append({"t": "line", "x1": xa, "y1": ya, "x2": xb, "y2": yb, "o": 0.18})
            deco.append({"t": "text", "x": xa - 6, "y": ya, "dy": 4, "s": t("frame.geo.lat", deg=lat), "a": "end", "z": 10, "o": 0.6})
        top_y = P(lo_lon, hi_lat)[1]
        deco.append({"t": "text", "x": P(lo_lon, hi_lat)[0], "y": top_y, "dy": -30, "s": t("frame.geo.title"), "a": "start", "z": 13, "w": 600})
        deco.append({"t": "text", "x": P(lo_lon, hi_lat)[0], "y": top_y, "dy": -15, "s": t("frame.geo.note"), "a": "start", "z": 11, "o": 0.8})
        for i in sorted(located, key=lambda i: data.nodes[i]["id"]):
            lon, lat = data.nodes[i]["geo"][:2]
            pos[i] = P(lon, lat)
            region[i] = "map"
        # members around each located place, nearest ring first
        members: dict[int, list[int]] = {p: [] for p in located}
        for i, nd in enumerate(data.nodes):
            if i in pos or nd["k"] == "place":
                continue
            if nd["_places"]:
                members[nd["_places"][0]].append(i)
        for p in sorted(located, key=lambda i: data.nodes[i]["id"]):
            cx, cy = pos[p]
            ms = sorted(members[p], key=lambda i: (KIND_ORDER.index(data.nodes[i]["k"]) if data.nodes[i]["k"] != "event" else -1, data.nodes[i]["n"].lower(), data.nodes[i]["id"]))
            for j, i in enumerate(ms):
                r = 7.0 * math.sqrt(j + 1.6)
                a = (j + 1) * GOLDEN
                pos[i] = (cx + r * math.cos(a), cy + r * math.sin(a))
                region[i] = "map"
        bottom = P(lo_lon, lo_lat)[1] + 30
    else:
        bottom = 0.0
    rest = [i for i in range(len(data.nodes)) if i not in pos]
    shelf(data, rest, bottom + 30, t("frame.geo.shelf"), t, pos, deco, region)
    return {"pos": pos, "deco": deco, "region": region}


# --------------------------------------------------------------------------- stories
def stories_frame(data, t) -> dict:
    pos, deco, region = {}, [], {}
    stories = sorted([i for i, nd in enumerate(data.nodes) if nd["k"] == "story"],
                     key=lambda i: (data.nodes[i].get("no") is None, data.nodes[i].get("no", 0), data.nodes[i]["n"].lower()))
    R = 400.0
    if stories:
        parts = []
        for i in stories:
            p = data.nodes[i].get("part")
            if not parts or parts[-1][0] != p:
                parts.append((p, data.nodes[i].get("partl"), []))
            parts[-1][2].append(i)
        gap = 1.5
        slots = len(stories) + gap * len(parts)
        slot = 0.0
        deco.append({"t": "circle", "x": 0, "y": 0, "r": R, "o": 0.18})
        deco.append({"t": "text", "x": -WIDTH / 2, "y": -R - 50, "dy": -16, "s": t("frame.stories.title"), "a": "start", "z": 13, "w": 600})
        deco.append({"t": "text", "x": -WIDTH / 2, "y": -R - 50, "dy": 0, "s": t("frame.stories.note"), "a": "start", "z": 11, "o": 0.8})
        for p, plabel, items in parts:
            start = slot
            for i in items:
                ang = -math.pi / 2 + (slot + 0.5) / slots * 2 * math.pi
                pos[i] = (R * math.cos(ang), R * math.sin(ang))
                region[i] = "dial"
                slot += 1
            mid = -math.pi / 2 + ((start + slot) / 2) / slots * 2 * math.pi
            lx, ly = (R + 48) * math.cos(mid), (R + 48) * math.sin(mid)
            if plabel and plabel.lower().startswith("part"):
                text = plabel  # the recorded label already names the part
            elif plabel:
                text = t("frame.stories.part", n=p, label=plabel)
            else:
                text = t("frame.stories.part_plain", n=p if p is not None else "?")
            deco.append({"t": "text", "x": lx, "y": ly, "s": text, "a": "middle", "z": 12, "w": 600, "o": 0.9})
            slot += gap
        # nodes tied to stories: start at the mean of their stories, pulled inside the ring
        free = [i for i, nd in enumerate(data.nodes) if nd["k"] != "story" and nd["_stories"]]
        anchor = {}
        for i in free:
            sx = sum(pos[s][0] for s in data.nodes[i]["_stories"]) / len(data.nodes[i]["_stories"])
            sy = sum(pos[s][1] for s in data.nodes[i]["_stories"]) / len(data.nodes[i]["_stories"])
            d = math.hypot(sx, sy)
            lim = R * 0.84
            if d > lim:
                sx, sy = sx / d * lim, sy / d * lim
            anchor[i] = (sx, sy)
        groups: dict[tuple, list[int]] = {}
        for i in free:
            groups.setdefault(tuple(data.nodes[i]["_stories"]), []).append(i)
        xy = {}
        for key in sorted(groups):
            ms = sorted(groups[key], key=lambda i: (data.nodes[i]["k"], data.nodes[i]["n"].lower(), data.nodes[i]["id"]))
            for j, i in enumerate(ms):
                ax, ay = anchor[i]
                r = 0.0 if j == 0 else 8.0 * math.sqrt(j)
                a = j * GOLDEN
                xy[i] = [ax + r * math.cos(a), ay + r * math.sin(a)]
        order = sorted(xy, key=lambda i: data.nodes[i]["id"])
        mind = 9.0
        for _ in range(60):
            moved = False
            for a_i in range(len(order)):
                i = order[a_i]
                for b_i in range(a_i + 1, len(order)):
                    j = order[b_i]
                    dx = xy[j][0] - xy[i][0]
                    dy = xy[j][1] - xy[i][1]
                    d2 = dx * dx + dy * dy
                    if d2 < mind * mind:
                        d = math.sqrt(d2) or 0.01
                        if d2 == 0:
                            dx, dy = _h01(data.nodes[j]["id"], "dx") - 0.5, _h01(data.nodes[j]["id"], "dy") - 0.5
                            d = math.hypot(dx, dy) or 0.01
                        push = (mind - d) / 2
                        ux, uy = dx / d, dy / d
                        xy[i][0] -= ux * push
                        xy[i][1] -= uy * push
                        xy[j][0] += ux * push
                        xy[j][1] += uy * push
                        moved = True
            for i in order:
                d = math.hypot(*xy[i])
                if d > R * 0.9:
                    xy[i][0] *= R * 0.9 / d
                    xy[i][1] *= R * 0.9 / d
            if not moved:
                break
        for i in order:
            pos[i] = (xy[i][0], xy[i][1])
            region[i] = "dial"
    rest = [i for i in range(len(data.nodes)) if i not in pos]
    shelf(data, rest, R + 110, t("frame.stories.shelf"), t, pos, deco, region)
    return {"pos": pos, "deco": deco, "region": region}


# --------------------------------------------------------------------------- transmission
def isnad_frame(data, t) -> dict:
    pos, deco, region = {}, [], {}
    y = -260.0
    deco.append({"t": "text", "x": -WIDTH / 2, "y": y - 60, "dy": -34, "s": t("frame.isnad.title"), "a": "start", "z": 13, "w": 600})
    deco.append({"t": "text", "x": -WIDTH / 2, "y": y - 60, "dy": -19, "s": t("frame.isnad.note", n=len(data.chains)), "a": "start", "z": 11, "o": 0.85})
    deco.append({"t": "text", "x": -WIDTH / 2, "y": y - 60, "dy": -5, "s": t("frame.isnad.grows"), "a": "start", "z": 11, "o": 0.85})
    col = 0
    bottom = y
    for ch in data.chains:
        x = -WIDTH / 2 + 260 + col * 360
        seq = []
        if ch["terminal"] is not None:
            seq.append(ch["terminal"])
        for ln in ch["links"]:
            for i in ln[:2]:
                if i not in seq:
                    seq.append(i)
        rep = data.reports[ch["rep"]] if ch.get("rep") is not None else None
        title = ch["label"] or t("frame.isnad.chain")
        deco.append({"t": "text", "x": x, "y": y, "dy": -18, "s": title, "a": "middle", "z": 12, "w": 600})
        if rep and rep.get("asc"):
            deco.append({"t": "text", "x": x, "y": y, "dy": -4, "s": t("frame.isnad.ascription", value=rep["asc"]), "a": "middle", "z": 11, "o": 0.8})
        yy = y + 30
        for i in seq:
            if i in pos:
                continue
            pos[i] = (x, yy)
            region[i] = "chain"
            yy += 62
        if ch["collector"] is not None and ch["collector"] not in pos:
            yy += 20
            deco.append({"t": "text", "x": x + 16, "y": yy, "dy": 4, "s": t("frame.isnad.collector"), "a": "start", "z": 11, "o": 0.85})
            deco.append({"t": "text", "x": x + 16, "y": yy, "dy": 17, "s": t("frame.isnad.no_line"), "a": "start", "z": 10, "o": 0.7})
            pos[ch["collector"]] = (x, yy)
            region[ch["collector"]] = "chain"
            yy += 40
        bottom = max(bottom, yy)
        col += 1
    rest = [i for i in range(len(data.nodes)) if i not in pos]
    shelf(data, rest, bottom + 40, t("frame.isnad.shelf"), t, pos, deco, region)
    return {"pos": pos, "deco": deco, "region": region}


FRAMES = (("network", network_frame), ("time", time_frame), ("geo", geo_frame),
          ("stories", stories_frame), ("isnad", isnad_frame))


def compute_frames(data, t) -> dict:
    out = {}
    n = len(data.nodes)
    for name, fn in FRAMES:
        f = fn(data, t)
        missing = [i for i in range(n) if i not in f["pos"]]
        if missing:
            raise ValueError(f"frame {name}: {len(missing)} nodes without a position")
        flat = []
        for i in range(n):
            x, y = f["pos"][i]
            flat.extend((_r(x), _r(y)))
        deco = []
        for d in f["deco"]:
            dd = dict(d)
            for k in ("x", "y", "x1", "y1", "x2", "y2", "r"):
                if k in dd:
                    dd[k] = _r(dd[k])
            deco.append(dd)
        entry = {"pos": flat, "deco": deco, "region": [f["region"][i] for i in range(n)]}
        if "marks" in f:
            entry["marks"] = {str(i): f["marks"][i] for i in sorted(f["marks"])}
        if "axis" in f:
            entry["axis"] = f["axis"]
        out[name] = entry
    return out
