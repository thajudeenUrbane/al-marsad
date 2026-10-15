"""What is drawn for one person's life, and the ages it implies. Pure functions.

A line has, in day numbers (CE axis):
  b = [lo, hi]   the birth range (union of the active sources), or None
  d = [lo, hi]   the death range, or None
  s, e           the stretch the person was certainly alive: from the latest possible
                 birth (or, with no birth, the earliest recorded sign of life) to the
                 earliest possible death (or the latest recorded sign of life)
  open_start / open_end
                 True where the birth / death is not recorded: the line fades out there
                 over a fixed few pixels. The fade is drawn in screen space, never in
                 years, so it cannot be read as a date.

A "recorded sign of life" is a dated event the person took part in: alive at a moment in
[e_lo, e_hi] means certainly alive from e_hi to the death (and from the birth to e_lo).
Nothing between two recorded points is assumed beyond what those points entail.

By age, the birth is 0 by definition and the uncertainty moves to the other end:
  age at a moment in [t_lo, t_hi] = [(t_lo - b_hi), (t_hi - b_lo)] / year length.
"""
from __future__ import annotations

import calendars as cal

UNITS = ("lunar", "solar")


def union(ranges: list[tuple[int, int]]) -> list[int] | None:
    if not ranges:
        return None
    return [min(r[0] for r in ranges), max(r[1] for r in ranges)]


def active_claims(claims, include_review: bool):
    return [c for c in claims if c.drawable and (include_review or not c.review)]


def age_text(lo: float, hi: float, dash: str = "–") -> str:
    a, b = cal.completed_years(max(lo, 0.0), max(hi, 0.0))
    return f"{a}" if a == b else f"{a}{dash}{b}"


def life(claims, event_ranges: list[tuple[int, int]], include_review: bool = False) -> dict | None:
    """Geometry for one person, or None when no sourced birth or death can be placed
    (such a person is listed, never drawn). `event_ranges` are the dated events the
    person took part in."""
    act = active_claims(claims, include_review)
    b = union([(c.lo, c.hi) for c in act if c.kind == "birth"])
    d = union([(c.lo, c.hi) for c in act if c.kind == "death"])
    if b is None and d is None:
        return None
    conflict = []
    if b and d and b[0] > d[1]:
        conflict.append("birth_after_death")
    # events that fit inside what is known of the life
    anchors = []
    for lo, hi in event_ranges:
        if b and hi < b[0]:
            continue                          # wholly before the earliest possible birth
        if d and lo > d[1]:
            continue                          # wholly after the latest possible death
        anchors.append((lo, hi))
    if b:
        s = b[1]
    else:
        s = min([hi for _, hi in anchors] + [d[0]])
    if d:
        e = d[0]
    else:
        e = max([lo for lo, _ in anchors] + [b[1]])
    out = {"b": b, "d": d, "s": s, "e": e, "open_start": b is None, "open_end": d is None,
           "segment": s <= e, "conflict": conflict}
    if b:
        out["age"] = {}
        for u in UNITS:
            n = cal.UNITS[u]
            a = {"e": max(0.0, (e - b[1]) / n)}
            if d:
                a["d"] = [max(0.0, (d[0] - b[1]) / n), (d[1] - b[0]) / n]
            out["age"][u] = a
        if d:
            out["age_at_death"] = {u: age_text(*out["age"][u]["d"]) for u in UNITS}
    return out


def placement(lf: dict, ev_lo: int, ev_hi: int) -> dict:
    """Where an event sits on a person's line, and the computed age there.
    flag: '' (fits), 'before_birth' or 'after_death' (the recorded dates conflict; the
    node is not drawn and the conflict is said in words)."""
    b, d = lf.get("b"), lf.get("d")
    if b and ev_hi < b[0]:
        return {"ok": False, "flag": "before_birth"}
    if d and ev_lo > d[1]:
        return {"ok": False, "flag": "after_death"}
    out = {"ok": True, "flag": ""}
    if b:
        for u in UNITS:
            lo, hi = cal.age_range((b[0], b[1]), (ev_lo, ev_hi), u)
            out[u] = [max(0.0, lo), max(0.0, hi)]
            out[u + "_text"] = age_text(lo, hi)
    return out
