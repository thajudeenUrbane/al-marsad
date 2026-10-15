"""The Sky's own frame: a three-dimensional layout of the whole graph, computed offline.

The Prophet ﷺ is the fixed origin of the light (docs/01 §5, rule 1). The 50 Stories sit
on a ring around it in reading order, in the plane z = 0. A person whose generation
(ṭabaqa) is recorded is drawn towards a shell for that generation: Companions nearest
the light, then Successors, then their successors (rule 2: distance from the origin is
generational distance and nothing else). Everything else settles by its recorded links
alone. No position depends on how many links an item has, so nothing is placed as a
rank (docs/04 §3, docs/06 §7).

Deterministic, like frames.py: each item starts at a point derived from a hash of its
ID (adding an item moves no other item's starting point), the iteration order and
constants are fixed, and every coordinate is rounded to one decimal.
"""
from __future__ import annotations

import math

from frames import _h01, _r
from obsdata import TABAQA_ORDER

R_STORY = 560.0   # the ring of the 50 Stories
SHELL = {"sahabi": 190.0, "tabii": 330.0, "tabi_al_tabiin": 430.0}
R_FREE = 300.0    # starting radius of an item with no generation shell
R_MAX = 470.0     # nothing but the story ring sits further out than this
ITERATIONS = 300
CUTOFF2 = 320.0 ** 2

assert set(SHELL) == set(TABAQA_ORDER), "one shell per recorded generation"


def sky_frame(data, light: int | None) -> dict:
    """{"pos3": [x, y, z, ...], "region": {i: region}, "shells": {...}, "ring": R}."""
    nodes = data.nodes
    n = len(nodes)
    deg = [0] * n
    edges = []
    for l in data.links:
        a, b = l["a"], l["b"]
        if a == b:
            continue
        edges.append((a, b))
        deg[a] += 1
        deg[b] += 1
    stories = sorted((i for i in range(n) if nodes[i]["k"] == "story"),
                     key=lambda i: (nodes[i].get("no", 10 ** 6), nodes[i]["id"]))

    xs, ys, zs = [0.0] * n, [0.0] * n, [0.0] * n
    fixed = [False] * n
    target = [None] * n
    for i, nd in enumerate(nodes):
        target[i] = SHELL.get(nd.get("tbk")) if nd["k"] == "person" else None
        u = _h01(nd["id"], "sky-u") * 2 - 1
        th = _h01(nd["id"], "sky-t") * math.tau
        s = math.sqrt(1 - u * u)
        r0 = target[i] or R_FREE
        xs[i], ys[i], zs[i] = s * math.cos(th) * r0, s * math.sin(th) * r0, u * r0
    for k, i in enumerate(stories):
        a = -math.pi / 2 + k / len(stories) * math.tau
        xs[i], ys[i], zs[i] = math.cos(a) * R_STORY, math.sin(a) * R_STORY, 0.0
        fixed[i] = True
    if light is not None:
        xs[light] = ys[light] = zs[light] = 0.0
        fixed[light] = True

    # springs: rest length longer towards the story ring; stiffness shared out by degree
    springs = []
    for a, b in edges:
        rest = 120.0 if (nodes[a]["k"] == "story" or nodes[b]["k"] == "story") else 46.0
        springs.append((a, b, rest, 0.5 / min(deg[a], deg[b]), deg[a] / (deg[a] + deg[b])))
    charge = [-46.0] * n
    if light is not None:
        charge[light] = -600.0  # keeps clear space around the light
    coll = 9.0

    vx, vy, vz = [0.0] * n, [0.0] * n, [0.0] * n
    rng = range(n)
    for t in range(ITERATIONS):
        alpha = 0.001 ** (t / ITERATIONS)
        for a, b, rest, k, bias in springs:
            dx, dy, dz = xs[b] - xs[a], ys[b] - ys[a], zs[b] - zs[a]
            d = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
            f = (d - rest) / d * alpha * k
            fb, fa = f * bias, f * (1 - bias)
            vx[b] -= dx * fb; vy[b] -= dy * fb; vz[b] -= dz * fb
            vx[a] += dx * fa; vy[a] += dy * fa; vz[a] += dz * fa
        for i in rng:
            xi, yi, zi, qi = xs[i], ys[i], zs[i], charge[i]
            ax = ay = az = 0.0
            for j in range(i + 1, n):
                dx, dy, dz = xs[j] - xi, ys[j] - yi, zs[j] - zi
                d2 = dx * dx + dy * dy + dz * dz
                if d2 > CUTOFF2:
                    continue
                if d2 < 1.0:
                    d2 = 1.0
                fj, fi = charge[j] * alpha / d2, qi * alpha / d2
                if d2 < 4 * coll * coll:  # too close: push apart, so no two marks sit on one point
                    m = (2 * coll - math.sqrt(d2)) / math.sqrt(d2) * 0.35
                    fj -= m; fi -= m
                ax += dx * fj; ay += dy * fj; az += dz * fj
                vx[j] -= dx * fi; vy[j] -= dy * fi; vz[j] -= dz * fi
            vx[i] += ax; vy[i] += ay; vz[i] += az
        for i in rng:
            if fixed[i]:
                vx[i] = vy[i] = vz[i] = 0.0
                continue
            r = math.sqrt(xs[i] ** 2 + ys[i] ** 2 + zs[i] ** 2) or 1e-6
            goal = target[i]
            if goal is not None:
                f = (goal - r) * 0.6 * alpha / r
            elif r > R_MAX:
                f = (R_MAX - r) * 0.4 * alpha / r
            else:
                f = 0.0
            vx[i] = (vx[i] + xs[i] * f) * 0.6
            vy[i] = (vy[i] + ys[i] * f) * 0.6
            vz[i] = (vz[i] + zs[i] * f) * 0.6
            xs[i] += vx[i]; ys[i] += vy[i]; zs[i] += vz[i]

    pos3 = []
    region = {}
    for i in range(n):
        pos3 += [_r(xs[i]), _r(ys[i]), _r(zs[i])]
        if i == light:
            region[i] = "light"
        elif nodes[i]["k"] == "story":
            region[i] = "ring"
        elif deg[i] == 0:
            region[i] = "unlinked"
        elif target[i] is not None:
            region[i] = "shell"
        else:
            region[i] = "free"
    return {"pos3": pos3, "region": [region[i] for i in range(n)], "shells": SHELL, "ring": R_STORY}
