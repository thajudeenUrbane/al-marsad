#!/usr/bin/env python3
"""The home page links every view that was built, and only those (site/hub.py).

    .venv/bin/python site/check_hub.py [site/dist]

Run it after the view builders and `site/build.py --hub`. Fails (exit 1) when a view
folder in site/dist holds an index.html that the home page does not link (a builder ran
after the hub pages were written: run `site/build.py --hub` again), when the home page
links a view that is not there, or when the hub pages (home, Study, Research) fail the
HTML checks or the page budget.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_budget  # noqa: E402
import check_html  # noqa: E402
import hub  # noqa: E402

HUB_PAGES = ("index.html", "study/index.html", "research/index.html")
# the Arabic copy lists the same views (English only for now), linked from the site root
LANGUAGES = (("", ""), ("ar/", "../"))   # (folder, the way up to the site root from its home page)


def check(root: Path) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    built = hub.built(root)
    for folder, up in LANGUAGES:
        home = root / folder / "index.html"
        if not home.is_file():
            return [], [f"{home} is missing: run site/build.py"]
        m = re.search(r'<ul class="hub-list" data-views="([^"]*)">(.*?)</ul>', home.read_text(encoding="utf-8"), re.S)
        if not m:
            return [], [f"the home page {folder or 'en'} has no hub list"]
        listed = m.group(1).split()
        for v in built:
            if v not in listed or f'href="{up}{v}/"' not in m.group(2):
                problems.append(f"{v}/ is built but the home page {folder}does not link it: run site/build.py --hub")
        for v in listed:
            if v not in built:
                problems.append(f"the home page {folder}links {v}/, which has no index.html")
    all_ids = check_html.collect_ids(root)
    for rel in [f + h for f, _ in LANGUAGES for h in HUB_PAGES]:
        page = root / rel
        if not page.is_file():
            problems.append(f"{rel} is missing")
            continue
        problems += check_html.check_page(root, page, all_ids)
    results, budget = check_budget.check(root)
    problems += [p for p in budget if p.split(":")[0] in [f + h for f, _ in LANGUAGES for h in HUB_PAGES]]
    return built, problems


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else HERE / "dist"
    built, problems = check(root)
    print(f"views built: {', '.join(built) or 'none'}")
    if problems:
        print(f"FAILED: {len(problems)} problem(s)")
        for p in problems[:30]:
            print("  " + p)
        return 1
    print("OK: the home page links every view that was built, and the hub pages pass the HTML and budget checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
