#!/usr/bin/env python3
"""Reader-tier weight budget (docs/05 section 7, docs/13 D1): fails the build.

    .venv/bin/python site/check_budget.py [site/dist]

For every HTML page it adds the page itself and every same-site file the page loads
(stylesheets, scripts, images, fonts and other resources, and what those stylesheets
pull in with url() or @import). A file that a script fetches at run time (the search
index) counts too: the page must name it in a data-fetch attribute, and the script
fetches only what that attribute names. A page over LIMIT bytes fails the check. Any external
URL in the src/href of a stylesheet, script, image or other loaded resource fails the
check too (plain <a href> links to other sites are navigation, not loads, and pass).
KB here means 1,000 bytes, the stricter reading of "300 KB".
Prints the five heaviest pages. Exit status 1 on any failure.
"""
from __future__ import annotations

import posixpath
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

LIMIT = 300_000
LOADING_RELS = {"stylesheet", "icon", "shortcut", "apple-touch-icon", "preload", "modulepreload",
                "prefetch", "manifest", "preconnect", "dns-prefetch", "mask-icon", "alternate"}
# "alternate" links (feeds, translations) are navigation hints, not loads, unless they are stylesheets
LOADING_RELS.discard("alternate")


class Refs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.loads: list[tuple[str, str]] = []   # (tag, url)

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "link" and a.get("href"):
            rels = set(a.get("rel", "").lower().split())
            if rels & LOADING_RELS:
                self.loads.append(("link", a["href"]))
        elif tag == "script" and a.get("src"):
            self.loads.append(("script", a["src"]))
        elif tag in ("img", "source", "video", "audio", "track", "iframe", "embed", "input") and a.get("src"):
            self.loads.append((tag, a["src"]))
        elif tag == "object" and a.get("data"):
            self.loads.append((tag, a["data"]))
        if a.get("data-fetch"):
            self.loads.append(("data-fetch", a["data-fetch"]))
        for key in ("srcset",):
            if a.get(key):
                for part in a[key].split(","):
                    self.loads.append((tag, part.strip().split(" ")[0]))
        if a.get("style"):
            for u in re.findall(r"url\(\s*['\"]?([^)'\"]+)", a["style"]):
                self.loads.append(("style", u))


def is_external(url: str) -> bool:
    u = url.strip()
    return u.startswith("//") or bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", u)) and not u.lower().startswith("data:")


def resolve(page_rel: str, url: str, root: Path) -> Path:
    path = unquote(urlsplit(url).path)
    base = posixpath.dirname(page_rel)
    joined = posixpath.normpath(posixpath.join(base, path)) if not path.startswith("/") else posixpath.normpath(path.lstrip("/"))
    return root / joined


def css_loads(css_text: str) -> list[str]:
    urls = re.findall(r"url\(\s*['\"]?([^)'\"]+?)['\"]?\s*\)", css_text)
    urls += re.findall(r"@import\s+['\"]([^'\"]+)['\"]", css_text)
    return urls


def check(root: Path, limit: int = LIMIT) -> tuple[list[tuple[int, str, int, int]], list[str]]:
    results, problems = [], []
    css_cache: dict[Path, list[str]] = {}
    for page in sorted(root.rglob("*.html")):
        rel = page.relative_to(root).as_posix()
        html_bytes = page.stat().st_size
        parser = Refs()
        parser.feed(page.read_text(encoding="utf-8"))
        seen: dict[Path, int] = {}
        inline = 0
        queue = [(tag, url, rel) for tag, url in parser.loads]
        while queue:
            tag, url, origin = queue.pop()
            if url.lower().startswith("data:"):
                inline += len(url)
                continue
            if is_external(url):
                problems.append(f"{rel}: external URL in {tag}: {url}  (loaded from {origin})")
                continue
            if not urlsplit(url).path:
                continue
            target = resolve(origin, url, root)
            if not target.is_file():
                problems.append(f"{rel}: missing file for {tag}: {url}")
                continue
            if target in seen:
                continue
            seen[target] = target.stat().st_size
            if target.suffix == ".css":
                if target not in css_cache:
                    css_cache[target] = css_loads(target.read_text(encoding="utf-8", errors="replace"))
                trel = target.relative_to(root).as_posix()
                queue.extend(("css", u, trel) for u in css_cache[target])
        total = html_bytes + sum(seen.values()) + inline
        results.append((total, rel, html_bytes, len(seen)))
        if total > limit:
            problems.append(f"{rel}: {total:,} bytes is over the {limit:,} byte budget")
    return results, problems


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent / "dist"
    if not root.is_dir():
        print(f"{root} does not exist; run site/build.py first", file=sys.stderr)
        return 1
    results, problems = check(root)
    if not results:
        print("no HTML pages found", file=sys.stderr)
        return 1
    results.sort(reverse=True)
    print(f"checked {len(results)} pages; budget {LIMIT:,} bytes per page (HTML + same-site CSS/JS/images)")
    print("five heaviest pages:")
    for total, rel, html_bytes, n in results[:5]:
        print(f"  {total:>9,} bytes  {rel}  (html {html_bytes:,} + {n} file{'s' if n != 1 else ''})")
    if problems:
        print(f"\nFAILED: {len(problems)} problem(s)")
        for p in problems[:25]:
            print("  " + p)
        return 1
    print("OK: every page is within budget, no external loads")
    return 0


if __name__ == "__main__":
    sys.exit(main())
