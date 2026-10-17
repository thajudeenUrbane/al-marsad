#!/usr/bin/env python3
"""
Measure the full-book pass's error rate (slice 11a, maintainer F4): a sample for an editor.

    .venv/bin/python ingest/audit_sample.py sample   # write ingest/claims/ibn-hisham-full-audit-sample.json
    .venv/bin/python ingest/audit_sample.py sheet    # write ingest/cache/audit.html (local: it quotes the text)
    .venv/bin/python ingest/audit_sample.py report   # the error rate from ingest/claims/ibn-hisham-full-audit-results.csv

The sample is about 400 claims, drawn with a fixed seed and stratified by relation: each
relation gets a share in proportion to its size, and at least MIN_PER claims (or all of
them, if it has fewer), so rare relations such as "killed" are measured too. The overall
rate weights each relation by its size, so the over-sampled rare ones do not distort it.

The editor opens the local sheet, reads each claim beside its Arabic words, marks it
right / wrong / unsure with a note, and saves the CSV it offers as
ingest/claims/ibn-hisham-full-audit-results.csv (claim, verdict, note, checked_on; no
names). `report` gives the rate per relation and overall with 95% intervals (Wilson),
ready to publish (maintainer F4). A relation with a high rate is re-extracted, not
patched by hand. The sample file holds IDs only; the sheet stays in the gitignored cache.
"""

import argparse
import csv
import html
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ibn_hisham as ih  # noqa: E402
import sira_derive as sd  # noqa: E402

SAMPLE = ih.CLAIMS_DIR / "ibn-hisham-full-audit-sample.json"
RESULTS = ih.CLAIMS_DIR / "ibn-hisham-full-audit-results.csv"
SHEET = ih.CACHE / "audit.html"
SEED = 20261017
TOTAL = 400
MIN_PER = 5


def sample():
    _, _, claims = sd.load()
    side = [json.loads(x) for x in sd.OUT.open(encoding="utf-8")]
    claims = claims + [r for r in side if r["t"] == "side"]
    by = defaultdict(list)
    for c in claims:
        by[c["predicate"]].append(c["id"])
    n = sum(len(v) for v in by.values())
    rng = random.Random(SEED)
    # every relation gets MIN_PER (or all it has); the rest of TOTAL is shared in proportion to size
    take = {p: min(len(v), MIN_PER) for p, v in by.items()}
    left = TOTAL - sum(take.values())
    room = {p: len(v) - take[p] for p, v in by.items()}
    share = {p: left * room[p] / max(1, sum(room.values())) for p in by}
    for p in by:
        take[p] += int(share[p])
    for p in sorted(by, key=lambda p: (-(share[p] - int(share[p])), p))[:TOTAL - sum(take.values())]:
        take[p] += 1
    picked, strata = [], {}
    for p in sorted(by):
        ids = sorted(by[p])
        k = min(len(ids), take[p])
        strata[p] = {"claims": len(ids), "sampled": k}
        picked += [{"claim": i, "predicate": p} for i in sorted(rng.sample(ids, k))]
    return {"seed": SEED, "claims": n, "sampled": len(picked), "strata": strata, "sample": picked}


def sheet():
    if not SAMPLE.exists():
        sys.exit("no sample yet: run `ingest/audit_sample.py sample`")
    s = json.loads(SAMPLE.read_text(encoding="utf-8"))
    raw, passages, claims = sd.load()
    side = {r["id"]: r for r in (json.loads(x) for x in sd.OUT.open(encoding="utf-8")) if r["t"] == "side"}
    by_id = {c["id"]: c for c in claims}
    by_id.update(side)
    pmap = {p["id"]: p for p in passages}
    rows = []
    for k, item in enumerate(s["sample"], 1):
        c = by_id[item["claim"]]
        p = pmap[c["passage"]]
        t = raw[p["start"]:p["end"]]
        a, b = c["span"]
        name = lambda x: x.get("name", "") if isinstance(x, dict) else ""  # noqa: E731
        rows.append(
            f'<tr data-id="{c["id"]}"><td>{k}</td><td>{html.escape(name(c["subject"]))}<br><b>{c["predicate"][4:]}</b><br>'
            f'{html.escape(name(c["object"]))}<div class="g">{html.escape(c.get("gloss", ""))}</div></td>'
            f'<td dir="rtl" lang="ar">…{html.escape(ih.clean(t[max(0, a - 220):a]))} '
            f'<mark>{html.escape(ih.clean(t[a:b]))}</mark> {html.escape(ih.clean(t[b:b + 160]))}…'
            f'<div class="g">{p["key"]}</div></td>'
            '<td><select><option value="">?</option><option>right</option><option>wrong</option><option>unsure</option>'
            '</select><input placeholder="note"></td></tr>')
    page = f"""<!doctype html><meta charset="utf-8"><title>Audit sample: full-book pass</title>
<style>body{{font:15px system-ui;margin:16px}}table{{border-collapse:collapse}}td{{border-top:1px solid #ccc;vertical-align:top;padding:6px}}
td[dir=rtl]{{font:18px/1.7 "Noto Naskh Arabic",serif;max-width:46em}}mark{{background:#fe6}}.g{{color:#666;font-size:12px}}
input{{width:12em}}button{{font-size:15px;margin:8px 0}}</style>
<h1>Audit sample ({s['sampled']} of {s['claims']} claims, seed {s['seed']})</h1>
<p>For each claim: is it what the highlighted Arabic words say? Mark right, wrong or unsure, with a note for wrong or unsure.
Your marks stay in this browser. When done, save the CSV and put it at ingest/claims/ibn-hisham-full-audit-results.csv.</p>
<button id="save">Save results as CSV</button>
<table>{''.join(rows)}</table>
<script>
const K="marsad-audit-"+{json.dumps(str(s['seed']))};
let st={{}};try{{st=JSON.parse(localStorage.getItem(K)||"{{}}")}}catch(e){{}}
document.querySelectorAll("tr[data-id]").forEach(tr=>{{const id=tr.dataset.id,sel=tr.querySelector("select"),inp=tr.querySelector("input");
 if(st[id]){{sel.value=st[id].v||"";inp.value=st[id].n||""}}
 const save=()=>{{st[id]={{v:sel.value,n:inp.value}};try{{localStorage.setItem(K,JSON.stringify(st))}}catch(e){{}}}};
 sel.onchange=save;inp.oninput=save}});
document.getElementById("save").onclick=()=>{{const q=x=>'"'+String(x).replace(/"/g,'""')+'"';
 let out="claim,verdict,note,checked_on\\n";const d=new Date().toISOString().slice(0,10);
 document.querySelectorAll("tr[data-id]").forEach(tr=>{{const v=tr.querySelector("select").value;if(v)out+=[tr.dataset.id,v,q(tr.querySelector("input").value),d].join(",")+"\\n"}});
 const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([out],{{type:"text/csv"}}));a.download="ibn-hisham-full-audit-results.csv";a.click()}};
</script>"""
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    SHEET.write_text(page, encoding="utf-8")
    print(f"wrote {SHEET.relative_to(ih.ROOT)} ({len(rows)} claims): open it in a browser")


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def report():
    s = json.loads(SAMPLE.read_text(encoding="utf-8"))
    if not RESULTS.exists():
        sys.exit(f"no results yet: the editor saves {RESULTS.relative_to(ih.ROOT)} from the sheet")
    verdict = {r["claim"]: r["verdict"] for r in csv.DictReader(RESULTS.open(encoding="utf-8"))}
    pred = {i["claim"]: i["predicate"] for i in s["sample"]}
    done, wrong = Counter(), Counter()
    for cid, v in verdict.items():
        if cid in pred and v in ("right", "wrong"):
            done[pred[cid]] += 1
            wrong[pred[cid]] += v == "wrong"
    est, weight = 0.0, 0
    print(f"{'relation':28} {'checked':>7} {'wrong':>5}  rate   95% interval")
    for p, st in sorted(s["strata"].items(), key=lambda kv: -kv[1]["claims"]):
        n, k = done[p], wrong[p]
        lo, hi = wilson(k, n)
        if n:
            est += st["claims"] * (k / n)
            weight += st["claims"]
        print(f"{p[4:]:28} {n:7} {k:5}  {(k / n if n else 0):5.1%}  {lo:5.1%}-{hi:5.1%}")
    n, k = sum(done.values()), sum(wrong.values())
    print(f"\nchecked {n} of {s['sampled']} sampled ({sum(1 for v in verdict.values() if v == 'unsure')} unsure, left out)")
    covered = f"{weight / s['claims']:.0%} of all claims, by the relations checked so far"
    print(f"overall, weighted by relation size: {(est / weight if weight else 0):.1%} wrong ({covered}); "
          f"unweighted {k}/{n}, 95% {wilson(k, n)[0]:.1%}-{wilson(k, n)[1]:.1%}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["sample", "sheet", "report"])
    a = ap.parse_args()
    if a.cmd == "sample":
        s = sample()
        SAMPLE.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {SAMPLE.relative_to(ih.ROOT)}: {s['sampled']} of {s['claims']} claims in {len(s['strata'])} relations")
    elif a.cmd == "sheet":
        sheet()
    else:
        report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
