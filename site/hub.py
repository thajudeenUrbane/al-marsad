"""The views of the graph that other builders write into site/dist, and how the home
page (the hub) finds them.

Each view is a folder of site/dist that a builder of its own writes and owns:

    observatory/  site/observatory/build_observatory.py   the interactive graph
    lifelines/    site/lifelines/build_lifelines.py       parallel life lines
    timeline/     site/interactive/build_interactive.py   timeline   (one builder,
    map/          site/interactive/build_interactive.py   map         two folders)
    learn/        learn/build_learn.py                     learning paths and practice
    ask/          ask/build_ask.py                         ask the graph

The home page links a view only if its folder holds an index.html when the hub pages
are written. site/build.py never deletes these folders, so either order works:

    1. the view builders, then site/build.py; or
    2. site/build.py, the view builders, then `site/build.py --hub`, which rewrites only
       the pages that list views (home, study, research) from what is now in site/dist.

scripts/check_all.sh runs order 2 and then site/check_hub.py. Adding a view: one line
in VIEWS, and its name and description in site/i18n/en.json (hub.view.<folder>.*).
"""
from __future__ import annotations

from pathlib import Path

# (folder, door): the door is where the home page offers it besides the list of views.
VIEWS: tuple[tuple[str, str], ...] = (
    ("observatory", "discover"),
    ("timeline", "study"),
    ("lifelines", "study"),
    ("map", "study"),
    ("learn", "study"),
    ("ask", "research"),
)
DOORS = ("discover", "study", "research")
KEEP = frozenset(folder for folder, _ in VIEWS)   # site/build.py leaves these folders alone


def built(out: Path) -> list[str]:
    """The views whose folder in `out` holds an index.html, in VIEWS order."""
    return [folder for folder, _ in VIEWS if (Path(out) / folder / "index.html").is_file()]


def door_of(folder: str) -> str:
    return dict(VIEWS)[folder]
