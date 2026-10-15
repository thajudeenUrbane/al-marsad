"""The earlier prototypes (the Hijrah demo, generation-1 and 50 Stories), copied into
site/dist/experiments/ so the Experiments page can link them. The originals in demo/,
generation-1/ and stories-50/ are read, never changed.

Each copy is the committed page as built, with three changes and nothing else:
  1. it is wrapped in a full document (the originals are fragments: a host adds the
     doctype and the head when it publishes them);
  2. its web-font links are taken out, so the site makes no request to another server
     (the pages fall back to the fonts of the device); any other outside load is a build
     error, never shipped;
  3. a note at the top says it is an earlier prototype and links back, and the licence
     footer of the site comes last.
site/check_html.py checks the Experiments page itself like any other page, and only the
weight and outside loads of the copies (they keep their own structure).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = "experiments"
# (folder under experiments/, source folder in the repository, pages, i18n stem)
PROTOTYPES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    ("hijrah-demo", "demo", ("index.html",), "demo"),
    ("generation-1", "generation-1", ("index.html", "at-scale.html", "wider-network.html"), "generation1"),
    ("stories-50", "stories-50", ("index.html",), "stories50"),
)
STYLESHEET = "assets/archive.css"

_FONT_LINK = re.compile(r'[ \t]*<link\b[^>]*\bhref="https?://fonts\.(?:googleapis|gstatic)\.com[^"]*"[^>]*>[ \t]*\n?', re.I)
_HEAD_PART = re.compile(r'\s*(?:<!--.*?-->|<title>.*?</title>|<link\b[^>]*>|<meta\b[^>]*>'
                        r'|<style\b[^>]*>.*?</style>|<script\b[^>]*>.*?</script>)', re.S | re.I)


def is_copy(rel: str) -> bool:
    """True for a copied prototype page (experiments/<folder>/...), not the Experiments page."""
    parts = rel.split("/")
    return len(parts) >= 3 and parts[0] == FOLDER


def strip_web_fonts(text: str) -> str:
    return _FONT_LINK.sub("", text)


def wrap(fragment: str, *, lang: str, base: str, note: str, footer: str) -> str:
    """A full document around a prototype fragment: its title, links, meta, styles and
    scripts at the start become the head; the rest is the body, after the note."""
    if re.match(r"\s*<!doctype", fragment, re.I) or re.search(r"<body\b", fragment, re.I):
        raise ValueError("expected a fragment without doctype or body")
    pos = 0
    while (m := _HEAD_PART.match(fragment, pos)):
        pos = m.end()
    head, body = fragment[:pos].strip(), fragment[pos:].strip()
    return (f'<!doctype html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n{head}\n'
            f'<link rel="stylesheet" href="{base}{STYLESHEET}">\n</head>\n<body>\n{note}\n{body}\n{footer}\n</body>\n</html>\n')


def outside_loads(page: str) -> list[str]:
    """Resources the page would load from another server (check_budget's own reading)."""
    import check_budget
    refs = check_budget.Refs()
    refs.feed(page)
    return [url for _, url in refs.loads if check_budget.is_external(url)]


def copy_all(out: Path, note_for, footer_for, lang: str = "en") -> list[str]:
    """Writes every prototype page into out/experiments/<folder>/. note_for(folder, depth)
    and footer_for(base) give the HTML of the note and the footer. Returns the pages written."""
    written = []
    for folder, source, pages, _ in PROTOTYPES:
        for name in pages:
            src = ROOT / source / name
            base = "../../"
            page = wrap(strip_web_fonts(src.read_text(encoding="utf-8")), lang=lang, base=base,
                        note=note_for(folder, base), footer=footer_for(base))
            bad = outside_loads(page)
            if bad:
                raise ValueError(f"{src}: would load from another server: {', '.join(bad)}")
            dest = out / FOLDER / folder / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(page, encoding="utf-8")
            written.append(dest.relative_to(out).as_posix())
    return written
