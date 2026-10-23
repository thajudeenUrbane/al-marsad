#!/usr/bin/env python3
"""
Build the control condition: a plain reading page for each half of the Hijrah journey.

    python3 lab/pilot-1/build_reading_page.py

Writes lab/pilot-1/reading-A.html (Half 1, chapters 1-5) and reading-B.html (Half 2, chapters 6-10).

Same claims, same order, same citations as the Hijrah Night page (taken from its built data):
for each chapter, the section headings, the claims "Recorded in the text", the chains of
narration (drawn from the chain claims, as on the page) and the family links. Left out on purpose: the terrain and map, the light, the stars,
guess-first, every quiz (check, dispute, ordering), the "Think" prompts and progress saving.
The honesty cues are kept as plain words: each claim says it is AI-extracted and unreviewed,
stops with no reviewed location say so, and where the text gives two reports both are listed
as they come. No script runs on the page.
"""
from __future__ import annotations

from html import escape as esc
from pathlib import Path

from world_data import HALVES, load

HERE = Path(__file__).resolve().parent
FILES = {1: "reading-A.html", 2: "reading-B.html"}

CSS = """
:root{--bg:#fbfaf7;--ink:#1f1d1a;--muted:#6a645b;--rule:#e4dfd6;--card:#ffffff;--accent:#7a5a1e}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17161a;--ink:#ece8e1;--muted:#a7a097;--rule:#34312c;--card:#1f1e22;--accent:#d9b36a}}
:root[data-theme="dark"]{--bg:#17161a;--ink:#ece8e1;--muted:#a7a097;--rule:#34312c;--card:#1f1e22;--accent:#d9b36a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:18px/1.6 Georgia,"Iowan Old Style","Times New Roman",serif}
main{max-width:42rem;margin:0 auto;padding:2rem 16px 4rem}
header p{color:var(--muted)}
h1{font-size:1.9rem;line-height:1.2;margin:.2rem 0 1rem}
h2{font-size:1.4rem;margin:3rem 0 .2rem;padding-top:1.2rem;border-top:1px solid var(--rule)}
h3{font:600 .8rem/1.4 system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:1.6rem 0 .4rem}
.eyebrow{font:600 .8rem/1.4 system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;color:var(--accent)}
ul.claims{list-style:none;padding:0;margin:0}
ul.claims li{padding:.55rem 0;border-bottom:1px solid var(--rule)}
.cite{display:block;font:.8rem/1.4 system-ui,sans-serif;color:var(--muted)}
.note{font-style:italic;color:var(--muted)}
.chain{background:var(--card);border:1px solid var(--rule);border-radius:6px;padding:.6rem .9rem;margin:.4rem 0}
.chain ol{margin:.2rem 0 0 1.2rem;padding:0}
details{margin-top:1rem}summary{cursor:pointer;color:var(--accent)}
.sections{font:.85rem/1.5 system-ui,sans-serif;color:var(--muted)}
.prov{font-size:.9rem;color:var(--muted);margin-top:1.4rem}
footer{margin-top:3rem;padding-top:1rem;border-top:1px solid var(--rule);color:var(--muted)}
"""


def claim_li(c: dict, unplaced: set[str]) -> str:
    sec = c["sec"][1:].lstrip("0")
    extra = ""
    if c["id"] in unplaced:
        extra = ' <span class="note">(named in the text; no reviewed location yet)</span>'
    return (f'<li>{esc(c["g"])}{extra}<span class="cite">Ibn Hishām, {esc(c["cite"].split(";")[0])} · §{sec}'
            f' · proposed (AI-extracted, not yet reviewed)</span></li>')


def main() -> None:
    data = load()
    unplaced = {r["claim"] for r in data["route"] if r.get("claim") and not r["placed"]}
    for h, rng in HALVES.items():
        chs = [data["chapters"][n] for n in rng]
        n_claims = sum(len(ch["story"]) + len(ch["chainClaims"]) + len(ch["family"]) for ch in chs)
        body = []
        for n, ch in zip(rng, chs):
            body.append(f'<section><div class="eyebrow">Chapter {n + 1} of 10</div><h2>{esc(ch["title"])}</h2>')
            body.append(f'<h3>Recorded in the text · {len(ch["story"])} claims</h3>'
                        f'<ul class="claims">{"".join(claim_li(c, unplaced) for c in ch["story"])}</ul>')
            if ch["chains"]:
                body.append("<h3>Chains of narration</h3>")
                for cn in ch["chains"]:
                    body.append(f'<div class="chain"><span class="cite">{esc(cn["sec"])} · the book\'s narrator first, '
                                f'the eyewitness last</span><ol>{"".join(f"<li>{esc(x)}</li>" for x in cn["names"])}</ol></div>')
            if ch["family"]:
                body.append(f'<details><summary>Family links named in these sections ({len(ch["family"])})</summary>'
                            f'<ul class="claims">{"".join(claim_li(c, unplaced) for c in ch["family"])}</ul></details>')
            secs = "".join(f'<div>{esc(s["key"])} · {esc(s["cite"])}<br>{esc(s["label"])} '
                           f'<i>(section heading written by AI)</i></div>' for s in ch["sections"])
            body.append(f'<h3>Sections used</h3><div class="sections">{secs}</div></section>')
        first, last = rng[0] + 1, rng[-1] + 1
        page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hijrah Reading {"AB"[h - 1]}</title><style>{CSS}</style></head>
<body><main>
<header><div class="eyebrow">The Hijrah · chapters {first}–{last}</div>
<h1>The Hijrah, part {h}</h1>
<p>Read at your own pace. Every line below comes from Ibn Hishām's <i>al-Sīra al-Nabawiyya</i>, with its volume and page.
When the text gives two reports about the same thing, both are listed.</p></header>
{"".join(body)}
<p class="prov">From Ibn Hishām's <i>al-Sīra al-Nabawiyya</i>. Each line is an English gloss of a claim extracted by AI from the Arabic;
none has been reviewed by a scholar yet. {n_claims} claims on this page.</p>
<footer>You have reached the end of this part.</footer>
</main></body></html>
"""
        (HERE / FILES[h]).write_text(page, encoding="utf-8")
        print(f"wrote {FILES[h]}: chapters {first}-{last}, {n_claims} claims")


if __name__ == "__main__":
    main()
