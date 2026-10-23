"""The Sky Atlas layout: three-dimensional positions for the whole joined graph, computed
offline and deterministically.

- The Prophet ﷺ is the light at the origin, never a node (docs/01 §5 rule 1; H4). A
  clear space is kept around it.
- Events lie on a spiral that winds from the north pole to the south, in the order Ibn
  Hishām's text tells them (each event's median OpenITI milestone among the claims
  that cite it; its first mention is often an aside long before its own chapter): the
  "ecliptic of the record". An event the text never names
  but whose date is recorded is set between the named events of the same years; an
  event with neither settles by its links. Position on the spiral is the order of a
  book, never a date and never a rank.
- The 50 Stories sit on an outer ring, tilted like the ecliptic, in reading order.
- Everyone and everything else settles by its recorded links alone (springs along each
  recorded link, a short-range push between marks, a clear space around the light).
  People the graph knows only from lineages (the background layer, F11) are drawn
  gently outwards, so the lineages hang outside the events they lead to.
- No position depends on how many links an item has. Generation is shown by brightness
  in the page (T4), never by position.

Deterministic: each item starts from a hash of its ID, the iteration order and the
constants are fixed, and coordinates are rounded to 0.1.
"""
from __future__ import annotations

import hashlib
import math
from collections import defaultdict

R_SPIRAL = 430.0      # radius of the sphere the event spiral lies on
TURNS = 4.5           # turns of the spiral from pole to pole
LAT_MAX = 0.86        # the spiral stops short of the poles (fraction of the radius)
R_STORY = 700.0       # the ring of the 50 Stories
TILT = math.radians(23.44)
R_CLEAR = 85.0        # nothing but the light inside this
R_BACK = 880.0        # where the lineage-only background is drawn towards
R_MAX = 1150.0
ITERATIONS = 90
CELL = 36.0           # push range; also the grid cell
COLL = 7.0            # marks closer than twice this are pushed apart


def _h(key: str, salt: str) -> float:
    d = hashlib.sha256(f"{salt}:{key}".encode("utf-8")).digest()
    return int.from_bytes(d[:8], "big") / 2 ** 64


def _r(x: float) -> float:
    return round(x, 1) + 0.0


def spiral_point(t: float) -> tuple[float, float, float]:
    """A point on the event spiral, t from 0 (north, first in the text) to 1 (south)."""
    y = (1 - 2 * t) * LAT_MAX * R_SPIRAL
    rr = math.sqrt(max(R_SPIRAL ** 2 - y * y, 0.0))
    a = t * TURNS * math.tau
    return rr * math.cos(a), y, rr * math.sin(a)


def event_order(nodes, tell_ms) -> list[tuple[int, float]]:
    """[(node, order key)] for the events placed on the spiral. The key is where the text
    tells the event; a dated event the text never names takes the median of the named
    events whose recorded year range overlaps its own."""
    named = [(i, tell_ms[i]) for i, nd in enumerate(nodes) if nd["k"] == "event" and i in tell_ms]
    dated_named = []
    for i, ms in named:
        for y0, y1, _t, _n in nodes[i].get("d", []):
            if y0 is not None:
                dated_named.append((y0, y1, ms))
                break
    out = list(named)
    for i, nd in enumerate(nodes):
        if nd["k"] != "event" or i in tell_ms:
            continue
        span = next(((y0, y1) for y0, y1, _t, _n in nd.get("d", []) if y0 is not None), None)
        if span is None:
            continue
        near = sorted(ms for y0, y1, ms in dated_named if y0 <= span[1] and y1 >= span[0])
        if near:
            out.append((i, near[len(near) // 2] + 0.5))
    out.sort(key=lambda x: (x[1], nodes[x[0]]["id"]))
    return out


def sky(nodes, links, tell_ms, light: int, background: set) -> dict:
    n = len(nodes)
    xs, ys, zs = [0.0] * n, [0.0] * n, [0.0] * n
    fixed = [False] * n
    placed = [False] * n

    # the light
    fixed[light] = placed[light] = True

    # the spiral of events
    order = event_order(nodes, tell_ms)
    ecliptic = []
    for r, (i, key) in enumerate(order):
        t = (r + 0.5) / len(order)
        xs[i], ys[i], zs[i] = spiral_point(t)
        fixed[i] = placed[i] = True
        ecliptic.append([i, round(t, 5)])

    # the ring of stories
    stories = sorted((i for i, nd in enumerate(nodes) if nd["k"] == "story"),
                     key=lambda i: (nodes[i].get("no", 10 ** 6), nodes[i]["id"]))
    for k, i in enumerate(stories):
        a = -math.pi / 2 + k / max(len(stories), 1) * math.tau
        x, y = math.cos(a) * R_STORY, math.sin(a) * R_STORY
        xs[i], ys[i], zs[i] = x, y * math.sin(TILT), y * math.cos(TILT)
        fixed[i] = placed[i] = True

    # neighbours along recorded links (the light is not a spring end: everyone would
    # collapse onto it)
    adj = defaultdict(list)
    edges = []
    for l in links:
        a, b = l["a"], l["b"]
        if a == b or light in (a, b):
            continue
        edges.append((a, b, l["c"]))
        adj[a].append(b)
        adj[b].append(a)
    deg = [len(adj[i]) for i in range(n)]

    # start: each item at the mean of its placed neighbours, spreading outwards ring by ring
    frontier = [i for i in range(n) if placed[i]]
    jitter = lambda i, s: (_h(nodes[i]["id"], s) - 0.5) * 2
    for _round in range(40):
        newly = []
        for i in range(n):
            if placed[i]:
                continue
            nb = [j for j in adj[i] if placed[j] and j != light]
            if not nb:
                continue
            k = len(nb)
            spread = 26.0 if nodes[i]["k"] != "person" or i not in background else 34.0
            xs[i] = sum(xs[j] for j in nb) / k + jitter(i, "x") * spread
            ys[i] = sum(ys[j] for j in nb) / k + jitter(i, "y") * spread
            zs[i] = sum(zs[j] for j in nb) / k + jitter(i, "z") * spread
            newly.append(i)
        for i in newly:
            placed[i] = True
        if not newly:
            break
    for i in range(n):  # no path to anything placed: a hashed point in the outer shell
        if not placed[i]:
            u = jitter(i, "u")
            th = _h(nodes[i]["id"], "t") * math.tau
            s = math.sqrt(max(1 - u * u, 0.0))
            r0 = 960.0 + 60.0 * _h(nodes[i]["id"], "r")
            xs[i], ys[i], zs[i] = s * math.cos(th) * r0, u * r0, s * math.sin(th) * r0
            placed[i] = True

    springs = []
    for a, b, cls in edges:
        rest = 20.0 if cls == "kinship" else 30.0
        if nodes[a]["k"] == "story" or nodes[b]["k"] == "story":
            rest = 70.0
        springs.append((a, b, rest, 0.45 / max(1, min(deg[a], deg[b]))))
    back = [i in background for i in range(n)]

    vx, vy, vz = [0.0] * n, [0.0] * n, [0.0] * n
    movable = [i for i in range(n) if not fixed[i]]
    cell2 = CELL * CELL
    for it in range(ITERATIONS):
        alpha = 0.02 ** (it / ITERATIONS)
        for a, b, rest, k in springs:
            dx, dy, dz = xs[b] - xs[a], ys[b] - ys[a], zs[b] - zs[a]
            d = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
            f = (d - rest) / d * alpha * k
            if not fixed[a]:
                w = 1.0 if fixed[b] else 0.5
                vx[a] += dx * f * w; vy[a] += dy * f * w; vz[a] += dz * f * w
            if not fixed[b]:
                w = 1.0 if fixed[a] else 0.5
                vx[b] -= dx * f * w; vy[b] -= dy * f * w; vz[b] -= dz * f * w
        grid = defaultdict(list)
        for i in range(n):
            if i != light:
                grid[(int(xs[i] // CELL), int(ys[i] // CELL), int(zs[i] // CELL))].append(i)
        for (cx, cy, cz), members in grid.items():
            near = []
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    for oz in (-1, 0, 1):
                        cell = grid.get((cx + ox, cy + oy, cz + oz))
                        if cell:
                            near.extend(cell)
            for i in members:
                if fixed[i]:
                    continue
                xi, yi, zi = xs[i], ys[i], zs[i]
                ax = ay = az = 0.0
                for j in near:
                    if j == i:
                        continue
                    dx, dy, dz = xi - xs[j], yi - ys[j], zi - zs[j]
                    d2 = dx * dx + dy * dy + dz * dz
                    if d2 > cell2:
                        continue
                    if d2 < 0.25:
                        dx, dy, dz, d2 = jitter(i, "cx"), jitter(i, "cy"), jitter(i, "cz"), 1.0
                    d = math.sqrt(d2)
                    f = 60.0 * alpha / d2
                    if d < 2 * COLL:
                        f += (2 * COLL - d) / d * 0.25
                    ax += dx * f; ay += dy * f; az += dz * f
                vx[i] += ax; vy[i] += ay; vz[i] += az
        for i in movable:
            r = math.sqrt(xs[i] ** 2 + ys[i] ** 2 + zs[i] ** 2) or 1e-6
            f = 0.0
            if r < R_CLEAR:
                f = (R_CLEAR - r) / r * 0.5
            elif r > R_MAX:
                f = (R_MAX - r) / r * 0.4
            elif back[i]:
                f = (R_BACK - r) / r * 0.04 * alpha
            vx[i] = (vx[i] + xs[i] * f) * 0.55
            vy[i] = (vy[i] + ys[i] * f) * 0.55
            vz[i] = (vz[i] + zs[i] * f) * 0.55
            xs[i] += vx[i]; ys[i] += vy[i]; zs[i] += vz[i]

    pos = []
    for i in range(n):
        pos += [_r(xs[i]), _r(ys[i]), _r(zs[i])]
    return {"pos": pos, "ecliptic": ecliptic}
