#!/usr/bin/env python3
"""Well-formedness and accessibility checks on the generated pages.

    .venv/bin/python site/check_html.py [site/dist]

Uses only the standard library's html.parser. For every page: tags open and close in
order (no unclosed or stray tags), one <html lang>, a <title>, exactly one <h1>, no
skipped heading levels, no link inside a link, the landmarks (header, nav, main, footer), a skip link that
points at an existing #main, unique ids, working #fragment links, internal links that
resolve to a generated file, lang="ar" elements that carry dir="rtl", and the licence
footer. The Arabic copy under ar/ must be <html lang="ar" dir="rtl">, and every page that
has a twin in the other language (the same path with or without ar/) must name both in
hreflang alternates that resolve. Exit status 1 on any problem.
"""
from __future__ import annotations

import posixpath
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiments  # noqa: E402

# The copied prototypes (experiments/<folder>/, site/experiments.py) keep their own
# structure: they are checked for well-formed tags, lang, title, unique ids, working links
# and the licence footer, but not for the reader pages' layout rules below.
LAYOUT_RULES = ("expected one <h1>", "heading level jumps", "landmark", "the first link must be a skip link")

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param",
        "source", "track", "wbr"}
LICENCE_HOSTS = ("LICENSING.md", "creativecommons.org/licenses/by-sa/4.0", "gnu.org/licenses/agpl-3.0")


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.errors: list[str] = []
        self.ids: list[str] = []
        self.links: list[str] = []
        self.headings: list[int] = []
        self.tags: dict[str, int] = {}
        self.html_lang = None
        self.html_dir = None
        self.alternates: dict[str, str] = {}
        self.title = ""
        self._in_title = False
        self.first_link: str | None = None
        self._open_a = 0
        self.footer_hrefs: list[str] = []
        self._footer_depth = 0

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        line = self.getpos()[0]
        self.tags[tag] = self.tags.get(tag, 0) + 1
        if tag == "html":
            self.html_lang = a.get("lang")
            self.html_dir = a.get("dir")
        if tag == "link" and "alternate" in a.get("rel", "").split() and a.get("hreflang"):
            self.alternates[a["hreflang"]] = a.get("href", "")
        if tag == "title":
            self._in_title = True
        if "id" in a:
            self.ids.append(a["id"])
        if a.get("lang", "").lower().startswith("ar") and a.get("dir") != "rtl":
            self.errors.append(f"line {line}: <{tag} lang=ar> without dir=rtl")
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append(int(tag[1]))
        if tag == "a":
            if self._open_a:
                self.errors.append(f"line {line}: a link inside a link")
            self._open_a += 1
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
            if self.first_link is None:
                self.first_link = a["href"]
            if self._footer_depth:
                self.footer_hrefs.append(a["href"])
        if tag == "footer":
            self._footer_depth += 1
        if tag not in VOID:
            self.stack.append((tag, line))

    def handle_startendtag(self, tag, attrs):
        if tag in VOID:
            self.handle_starttag(tag, attrs)
        else:
            self.errors.append(f"line {self.getpos()[0]}: self-closing <{tag}/> on a non-void element")

    def handle_endtag(self, tag):
        line = self.getpos()[0]
        if tag in VOID:
            return
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._open_a:
            self._open_a -= 1
        if tag == "footer":
            self._footer_depth -= 1
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
            return
        names = [t for t, _ in self.stack]
        if tag in names:
            while self.stack and self.stack[-1][0] != tag:
                t, l = self.stack.pop()
                self.errors.append(f"line {l}: <{t}> is never closed (closed by </{tag}> on line {line})")
            self.stack.pop()
        else:
            self.errors.append(f"line {line}: stray </{tag}>")

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def check_page(root: Path, path: Path, all_ids: dict[str, set[str]]) -> list[str]:
    rel = path.relative_to(root).as_posix()
    p = Page()
    p.feed(path.read_text(encoding="utf-8"))
    p.close()
    errs = list(p.errors)
    for t, l in p.stack:
        errs.append(f"line {l}: <{t}> is never closed")
    if not p.html_lang:
        errs.append("<html> has no lang")
    in_ar = rel.startswith("ar/")
    if in_ar and (p.html_lang != "ar" or p.html_dir != "rtl"):
        errs.append(f'the Arabic copy must be <html lang="ar" dir="rtl">, found lang={p.html_lang} dir={p.html_dir}')
    if not in_ar and p.html_dir == "rtl":
        errs.append("a page outside ar/ is right to left")
    twin = rel[3:] if in_ar else "ar/" + rel
    if (root / twin).is_file() and not experiments.is_copy(rel):
        for lang in ("en", "ar"):
            if lang not in p.alternates:
                errs.append(f"has a twin in the other language ({twin}) but no hreflang={lang} alternate")
        p.links.extend(p.alternates.values())
    elif in_ar:
        errs.append(f"an Arabic page with no English twin at {twin}")
    if not p.title.strip():
        errs.append("empty or missing <title>")
    if p.tags.get("h1", 0) != 1:
        errs.append(f"expected one <h1>, found {p.tags.get('h1', 0)}")
    prev = 0
    for h in p.headings:
        if prev and h > prev + 1:
            errs.append(f"heading level jumps from h{prev} to h{h}")
        prev = h
    for landmark in ("header", "nav", "main", "footer"):
        if not p.tags.get(landmark):
            errs.append(f"no <{landmark}> landmark")
    if p.first_link != "#main" or "main" not in p.ids:
        errs.append("the first link must be a skip link to an existing #main")
    seen = set()
    for i in p.ids:
        if i in seen:
            errs.append(f"duplicate id {i!r}")
        seen.add(i)
    ids = set(p.ids)
    for href in p.links:
        parts = urlsplit(href)
        if parts.scheme or href.startswith("//"):
            continue
        if not parts.path:
            if parts.fragment and parts.fragment not in ids:
                errs.append(f"link to missing #{parts.fragment}")
            continue
        raw = unquote(parts.path)
        if raw.startswith("/"):  # root-absolute link: resolve from the site root
            target = posixpath.normpath(raw.lstrip("/") or ".")
            target = "" if target == "." else target
        else:
            target = posixpath.normpath(posixpath.join(posixpath.dirname(rel), raw))
        if raw.endswith("/"):
            target = (target + "/index.html").lstrip("/")
        f = root / target
        if not f.is_file():
            errs.append(f"broken link {href!r}")
        elif parts.fragment and f.suffix == ".html":
            if f.relative_to(root).as_posix() not in all_ids:
                pass
            elif parts.fragment not in all_ids[f.relative_to(root).as_posix()]:
                errs.append(f"link {href!r} points at a missing anchor")
    for needle in LICENCE_HOSTS:
        if not any(needle in h for h in p.footer_hrefs):
            errs.append(f"the footer has no licence link to {needle}")
    if experiments.is_copy(rel):
        errs = [e for e in errs if not any(r in e for r in LAYOUT_RULES)]
    return [f"{rel}: {e}" for e in errs]


def collect_ids(root: Path) -> dict[str, set[str]]:
    out = {}
    for path in root.rglob("*.html"):
        p = Page()
        p.feed(path.read_text(encoding="utf-8"))
        out[path.relative_to(root).as_posix()] = set(p.ids)
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent / "dist"
    pages = sorted(root.rglob("*.html"))
    if not pages:
        print("no HTML pages found", file=sys.stderr)
        return 1
    all_ids = collect_ids(root)
    errors: list[str] = []
    for path in pages:
        errors.extend(check_page(root, path, all_ids))
    print(f"checked {len(pages)} pages")
    if errors:
        print(f"FAILED: {len(errors)} problem(s)")
        for e in errors[:30]:
            print("  " + e)
        return 1
    print("OK: all pages are well formed, one h1, landmarks, skip link, unique ids, links resolve, licence footer present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
