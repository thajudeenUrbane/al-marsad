#!/usr/bin/env python3
"""Learning paths and practice (slices 6 and 7, learn-v2), built on top of the reader tier.

    .venv/bin/python learn/build_learn.py [--graph build/graph.ttl] [--site site/dist]
                                          [--step-budget N] [--part-budget N]

Run it after site/build.py (which rebuilds site/dist/ from scratch, learn/ included).
It writes site/dist/learn/ and nothing else: a journey index, each journey in
learn/journeys/ at three depths (Discover, Study and Research, design §8), the practice
page with its question bank (bank.json), two small assets (learn.css, learn.js), and the
marsad-journey export in data/ (learn/FORMAT.md, written by learn/journey_export.py),
whose pages.json lists every page. The reader pages are rendered from that export. A
journey's door depth is learn/{slug}/, its other depths learn/{slug}/{depth}/; a depth
whose step HTML is over --step-budget bytes (220,000) is cut into pages .../p{k}/.
It reads build/graph.ttl through site/model.py, so every step links to the page the
reader tier built for that entity, and reuses site/display.py for names and dates and
the site's stylesheet for the look.

No page needs JavaScript. learn.js only adds "done" boxes that keep progress in this
browser (localStorage), shared by every page and depth of a journey; without it, or
without storage, every page is complete.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SITE = ROOT / "site"
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(HERE))

from model import Site  # noqa: E402

import journey_export  # noqa: E402
import journeys  # noqa: E402
import practice  # noqa: E402
from render_learn import STEP_HTML_BUDGET, LearnRenderer, Strings  # noqa: E402

MARKER = ".al-marsad-learn"


def build(graph: Path, site_dist: Path, quiet: bool = False, journeys_dir: Path | None = None,
          part_budget: int = journey_export.PART_BUDGET, step_budget: int = STEP_HTML_BUDGET) -> dict:
    # Public mode 'accepted' is a RuleError here, before anything is written or removed, so
    # no page that shows other statuses is left behind (design §8, fail-closed).
    journey_export.check_public_mode()
    if not graph.exists():
        sys.exit(f"{graph} not found: run ontology/build_graph.py and site/build.py first")
    if not (site_dist / "assets" / "site.css").is_file():
        sys.exit(f"{site_dist} has no reader-tier site: run site/build.py first")
    site = Site(graph)
    strings = Strings(HERE / "i18n" / "en.json", SITE / "i18n" / "en.json")
    specs = journeys.load_specs(journeys_dir or HERE / "journeys")
    built = journeys.build_all(site, specs)
    missing = sorted({f"{st.entity.kind}/{st.entity.pid}/" for j in built for st in j.steps + j.set_apart
                      if not (site_dist / st.entity.kind / st.entity.pid / "index.html").is_file()})
    if missing:
        sys.exit(f"{site_dist} is older than the graph ({len(missing)} step pages missing, e.g. {missing[0]}): "
                 "run site/build.py again")
    bank = practice.bank(site.g)
    counts = practice.status_counts(site.g)
    r = LearnRenderer(site, strings, HERE / "templates")

    out = site_dist / "learn"
    if out.exists():
        if any(out.iterdir()) and not (out / MARKER).exists():
            sys.exit(f"{out} exists and was not made by learn/build_learn.py; refusing to delete it")
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    (out / MARKER).write_text("made by learn/build_learn.py; safe to delete and rebuild\n", encoding="utf-8")
    for name in ("learn.css", "learn.js"):
        shutil.copyfile(HERE / "static" / name, out / "assets" / name)

    def write(rel: str, content: str):
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    # the marsad-journey export (design §10), with the reader's own page cuts: the pages
    # below are rendered from the same resolved journeys, so every stop URL in it is a page here
    export = journey_export.resolve_all(site, out / "data", journeys=built, bank=bank, graph_file=graph,
                                        part_budget=part_budget, step_budget=step_budget, renderer=r)
    docs, plans = export["journeys"], export["plans"]
    entries = {e["slug"]: e for e in export["index"]["journeys"]}
    for j in built:
        for path, page in r.journey_pages(j, docs, plans[j.slug], entries[j.slug]).items():
            write(f"{path[len('learn/'):]}index.html", page)
    pages = r.practice_pages(bank, counts)
    for rel, content in pages.items():
        write(rel, content)
    write("practice/bank.json", json.dumps({"questions": bank}, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    write("index.html", r.at("discover").index_page(built, len(bank), export["index"]["journeys"]))

    rule_shas = {s["slug"]: journeys.rule_sha(s) for s in specs}   # what an approval must name (design §3.5)
    summary = {"journeys": {j.slug: {"steps": len(j.steps), "apart": len(j.set_apart), "draft": j.is_draft,
                                     "rule_sha": rule_shas[j.slug], "content_sha": entries[j.slug]["content_sha"],
                                     "parts": entries[j.slug]["parts"],
                                     "pages": {d: len(plans[j.slug][d]) for d in journey_export.DEPTHS}}
                            for j in built},
               "questions": len(bank), "practice_pages": len(pages), "claims": counts,
               "export": {"files": len(export["files"]), "digest": export["digest"], "facade": export["facade"]}}
    if not quiet:
        print(f"built learn/ into {out}")
        for j in built:
            extra = f" (+{len(j.set_apart)} apart)" if j.set_apart else ""
            n = summary["journeys"][j.slug]["pages"]
            print(f"  {j.slug}: {len(j.steps)} steps{extra}, {'draft' if j.is_draft else 'approved'}, "
                  f"rule_sha {rule_shas[j.slug]}, content_sha {entries[j.slug]['content_sha']}")
            print(f"    pages: discover {n['discover']}, study {n['study']}, research {n['research']} "
                  f"(door {j.spec['door']}); data parts {entries[j.slug]['parts']}")
            if j.lists:
                print(f"    list file {j.lists['file']}: {j.lists['state']}, sha {j.lists['sha']}, "
                      f"order {j.order_applied}")
        print(f"  practice: {len(bank)} questions from accepted claims "
              f"({counts.get('accepted', 0)} accepted of {sum(counts.values())} claims)")
        print(f"  export: learn/data, {len(built)} journeys, {len(export['files'])} files, digest {export['digest']}")
        print(f"  atlas facade ({export['index']['graph']['file']}) {export['facade']}: "
              "if this changed, rebuild atlas/index.html")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graph", default=str(ROOT / "build" / "graph.ttl"))
    ap.add_argument("--site", default=str(SITE / "dist"))
    ap.add_argument("--step-budget", type=int, default=STEP_HTML_BUDGET,
                    help="bytes of step HTML per reader page (default %(default)s)")
    ap.add_argument("--part-budget", type=int, default=journey_export.PART_BUDGET,
                    help="bytes per export part and research file (default %(default)s)")
    a = ap.parse_args(argv)
    build(Path(a.graph), Path(a.site), part_budget=a.part_budget, step_budget=a.step_budget)
    return 0


if __name__ == "__main__":
    sys.exit(main())
