"""Calendar arithmetic for the Lifelines view. Pure functions, no graph access.

Every date is handled as a closed range of Julian Day Numbers (whole days), because a
recorded date is a range: "570 CE" is every day of that year, never 1 January.

Conventions, each stated where it is shown on the page:
  * CE dates are Julian-calendar dates, as is usual for this period. The graph's stored
    bounds follow this (17 Ramadan 2 AH is stored as 13 March 624, the Julian date the
    tabular conversion gives). A value recorded in the proleptic Gregorian calendar is
    converted through the day number, so it lands on the same axis.
  * Hijri conversion uses the tabular (arithmetical) Islamic calendar, civil epoch
    (1 Muharram 1 AH = 16 July 622 Julian), the method the graph's own conversions name.
    Real month starts followed sighting and may differ by a day or two.
  * Years before the Hijra are counted back in lunar years: 1 BH is the lunar year that
    ended on 15 July 622. This is a computed count, not a calendar anyone used then.
  * A lunar year is 10631/30 = 354.3667 days (the tabular mean); a solar year is
    365.2425 days. Ages are differences of day numbers divided by one of these.
"""
from __future__ import annotations

import math
import re

LUNAR_YEAR_DAYS = 10631 / 30          # 354.3667
SOLAR_YEAR_DAYS = 365.2425
HIJRA_EPOCH_JDN = 1948440             # 1 Muharram 1 AH (tabular, civil) = 16 July 622 Julian

UNITS = {"lunar": LUNAR_YEAR_DAYS, "solar": SOLAR_YEAR_DAYS}


# ---------------------------------------------------------------- Julian / Gregorian
def jdn_from_julian(y: int, m: int, d: int) -> int:
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - 32083


def jdn_from_gregorian(y: int, m: int, d: int) -> int:
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def julian_from_jdn(j: int) -> tuple[int, int, int]:
    c = j + 32082
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = d - 4800 + m // 10
    return year, month, day


def gregorian_from_jdn(j: int) -> tuple[int, int, int]:
    a = j + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return year, month, day


def _month_len(y: int, m: int, cal: str) -> int:
    nxt = (y + 1, 1) if m == 12 else (y, m + 1)
    f = jdn_from_gregorian if cal == "gregorian" else jdn_from_julian
    return f(nxt[0], nxt[1], 1) - f(y, m, 1)


# ---------------------------------------------------------------- tabular Hijri
def jdn_from_hijri(y: int, m: int, d: int) -> int:
    return (d + math.ceil(29.5 * (m - 1)) + (y - 1) * 354
            + math.floor((3 + 11 * y) / 30) + HIJRA_EPOCH_JDN - 1)


def hijri_from_jdn(j: int) -> tuple[int, int, int]:
    """Tabular Hijri date of a day number. Year 0 is 1 BH, year -1 is 2 BH, and so on."""
    y = math.floor((30 * (j - HIJRA_EPOCH_JDN) + 10646) / 10631)
    m = min(12, math.ceil((j - (29 + jdn_from_hijri(y, 1, 1))) / 29.5) + 1)
    m = max(1, m)
    d = j - jdn_from_hijri(y, m, 1) + 1
    return y, m, d


def hijri_year_start(y: int) -> int:
    return jdn_from_hijri(y, 1, 1)


# ---------------------------------------------------------------- ranges from recorded values
PRECISIONS = ("day", "month", "year", "decade", "century")
# Drawn on the axis. A century-wide value is honest but, drawn, it reads as a life of 100 years'
# uncertainty and ages such as "8-114"; it is listed in words instead and the end stays open.
DRAWN_PRECISIONS = ("day", "month", "year", "decade")
WIKIDATA_PRECISION = {11: "day", 10: "month", 9: "year", 8: "decade", 7: "century"}
_ISO = re.compile(r"^\s*([+-]?)(\d{1,6})-(\d{1,2})-(\d{1,2})")


def parse_iso(value: str) -> tuple[int, int, int] | None:
    """(year, month, day) from an ISO-like value; month/day 00 (Wikidata) become 1."""
    m = _ISO.match(value or "")
    if not m:
        return None
    sign = -1 if m.group(1) == "-" else 1
    return sign * int(m.group(2)), max(1, int(m.group(3))), max(1, int(m.group(4)))


def range_for(y: int, m: int, d: int, precision: str, calendar: str = "julian") -> tuple[int, int] | None:
    """Closed day-number range a recorded value covers at its precision.
    A year-precision value is the whole year, never one day. Precision coarser than a
    century is not drawn (returns None)."""
    f = jdn_from_gregorian if calendar == "gregorian" else jdn_from_julian
    if precision == "day":
        j = f(y, m, d)
        return j, j
    if precision == "month":
        return f(y, m, 1), f(y, m, 1) + _month_len(y, m, calendar) - 1
    if precision == "year":
        return f(y, 1, 1), f(y + 1, 1, 1) - 1
    if precision == "decade":
        y0 = (y // 10) * 10
        return f(y0, 1, 1), f(y0 + 10, 1, 1) - 1
    if precision == "century":
        c = math.ceil(y / 100)
        return f((c - 1) * 100 + 1, 1, 1), f(c * 100 + 1, 1, 1) - 1
    return None


def jdn_from_iso_bound(value: str) -> int | None:
    """A graph bound (xsd:dateTime) as a day number. Graph bounds are Julian dates."""
    ymd = parse_iso(value)
    return jdn_from_julian(*ymd) if ymd else None


# ---------------------------------------------------------------- ages
def age_range(birth: tuple[int, int], at: tuple[int, int], unit: str) -> tuple[float, float]:
    """Age at a moment, in years of `unit`, as a range: the earliest possible moment
    minus the latest possible birth, to the latest possible moment minus the earliest
    possible birth. Nothing is narrowed."""
    n = UNITS[unit]
    return (at[0] - birth[1]) / n, (at[1] - birth[0]) / n


def completed_years(lo: float, hi: float) -> tuple[int, int]:
    """Completed years over an age range (how sources usually count an age)."""
    return math.floor(lo + 1e-9), math.floor(hi + 1e-9)


def span_days_to_years(days: float, unit: str) -> float:
    return days / UNITS[unit]


# ---------------------------------------------------------------- text helpers
def hijri_year_label(y: int, ah: str, bh: str) -> str:
    return f"{y} {ah}" if y >= 1 else f"{1 - y} {bh}"


def hijri_years_text(lo: int, hi: int, ah: str, bh: str) -> str:
    """'53–52 BH', '1 BH – 1 AH', '11 AH' for the Hijri years a day range touches."""
    a, b = hijri_from_jdn(lo)[0], hijri_from_jdn(hi)[0]
    if a == b:
        return hijri_year_label(a, ah, bh)
    if a >= 1 and b >= 1:
        return f"{a}–{b} {ah}"
    if a < 1 and b < 1:
        return f"{1 - a}–{1 - b} {bh}"
    return f"{hijri_year_label(a, ah, bh)} – {hijri_year_label(b, ah, bh)}"
