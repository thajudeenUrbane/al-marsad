#!/usr/bin/env python3
"""
Slice 1c: the 50 Stories as Turtle.

    .venv/bin/python ontology/tools/stories50_to_ttl.py           # write ontology/corpus/stories-50.ttl
    .venv/bin/python ontology/tools/stories50_to_ttl.py --check   # exit 1 if the file on disk differs from what this would write

Reads stories-50/source/50-stories.md through the parser in stories-50/build.py
(imported, not copied) and ontology/corpus/identity.csv. Every person and group
is resolved through identity.csv (its `stories50_names` column) and nowhere
else; a name with no row stops the script. Nothing is minted for a person or
group.

What is written (all of it unverified; no status is raised):
  * the maintainer's doc as an mrs:Work, its rev-7 Markdown export as an
    mrs:Witness, the four Parts and fifty stories as mrs:Passage objects that
    carry the prose verbatim (crm:P190_has_symbolic_content);
  * each story as an mrs:Event (the occurrence the story narrates), with title,
    order (skos:notation) and the passage that tells it;
  * each person/group named in a story's "Companions connected to this story"
    list as one mrs:Assertion (predicate rel_participated_in, status proposed,
    coverage stub), with the doc's role text kept verbatim in rdfs:comment;
  * the "(accepted Islam later)" marker kept as the qualifier
    mrsv:q_accepted_islam_later on every link the doc marks with it;
  * a mrs:Person node only for people no other corpus file declares.

IDs of the new objects (events, passages, assertions ...) are minted once with
mint_id.py and then kept in ontology/corpus/stories-50-ids.csv, so re-running
this script never renames an IRI. The 50 story events are also registered in
identity.csv (kind event, confidence exact, as new IDs; not merged with any
other event).
"""

import argparse
import csv
import html
import importlib.util
import re
import sys
from pathlib import Path

import rdflib
from rdflib import RDF, Namespace

ROOT = Path(__file__).resolve().parents[2]
ONT = ROOT / "ontology"
CORPUS = ONT / "corpus"
OUT = CORPUS / "stories-50.ttl"
IDENTITY = CORPUS / "identity.csv"
LEDGER = CORPUS / "stories-50-ids.csv"
OTHER_FILES = [ONT / "examples" / "thawr.ttl", CORPUS / "generation-1.ttl", CORPUS / "seed-incidents.ttl"]
MRS = Namespace("https://w3id.org/marsad/core#")
BASE = "https://w3id.org/marsad/id/"
RECORDED = "2026-10-15T00:00:00Z"
COLUMNS = ["kind", "canonical_id", "preferred_name_en", "name_ar", "variant_ids",
           "stories50_names", "source_files", "confidence", "note"]
KIND_ORDER = ["person", "place", "event", "group"]
SCHEME = "as written in the 50 Stories doc (plain ASCII, no diacritics; no scheme applied)"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


s50 = load("stories50_build", ROOT / "stories-50" / "build.py")
mint = load("mint_id", ROOT / "ontology" / "tools" / "mint_id.py")


def lit(s, lang="en"):
    """A Turtle string literal (long form only when the text has quotes, backslashes or newlines)."""
    if not re.search(r'["\\\n]', s):
        return f'"{s}"' + (f"@{lang}" if lang else "")
    s = s.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    if s.endswith('"'):
        s = s[:-1] + '\\"'
    return f'"""{s}"""' + (f"@{lang}" if lang else "")


def raw(inline_html):
    """Undo build.inline(): back to the doc's own Markdown text."""
    s = re.sub(r"<b>(.+?)</b>", r"**\1**", inline_html)
    s = re.sub(r"<i>(.+?)</i>", r"*\1*", s)
    return html.unescape(s)


class Ledger:
    """key -> minted ID, persisted in stories-50-ids.csv so IRIs never change."""

    def __init__(self):
        self.ids = {}
        if LEDGER.exists():
            with LEDGER.open(encoding="utf-8", newline="") as fh:
                self.ids = {r["key"]: r["id"] for r in csv.DictReader(fh)}
        self.taken = mint.taken_payloads()
        self.dirty = False

    def get(self, key, prefix):
        if key not in self.ids:
            self.ids[key] = f"{prefix}:{mint.new_payload(self.taken)}"
            self.dirty = True
        assert self.ids[key].startswith(prefix + ":"), f"{key}: ledger ID {self.ids[key]} is not a {prefix}: ID"
        return self.ids[key]

    def save(self):
        with LEDGER.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["key", "id"])
            for k in sorted(self.ids):
                w.writerow([k, self.ids[k]])


def read_identity():
    with IDENTITY.open(encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        assert rd.fieldnames == COLUMNS, rd.fieldnames
        return list(rd)


def write_identity(rows):
    order = {k: i for i, k in enumerate(KIND_ORDER)}
    rows = sorted(rows, key=lambda r: (order[r["kind"]], r["preferred_name_en"].casefold()))
    with IDENTITY.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def persons_declared_elsewhere():
    """Canonical person CURIEs that another corpus file already declares as mrs:Person."""
    found = set()
    for path in OTHER_FILES:
        g = rdflib.Graph().parse(path, format="turtle")
        for s in g.subjects(RDF.type, MRS.Person):
            seg, payload = str(s)[len(BASE):].split("/", 1)
            found.add(f"per:{payload}")
    return found


def build():
    text = s50.SOURCE.read_text(encoding="utf-8")
    parts, stories, people = s50.parse(text)
    assert len(stories) == 50 and [s["n"] for s in stories] == list(range(1, 51))

    # -- identity: names -> canonical rows, from identity.csv only ------------
    rows = read_identity()
    by_name = {}
    for r in rows:
        if r["kind"] in ("person", "group"):
            for n in r["stories50_names"].split(";"):
                if n:
                    by_name.setdefault(n.casefold(), []).append(r)
    unresolved = []

    def resolve(name, kind):
        hits = [r for r in by_name.get(name.casefold(), []) if r["kind"] == kind]
        if len(hits) != 1:
            unresolved.append((kind, name, len(hits)))
            return None
        return hits[0]

    person_row = {pid: resolve(p["name"], "person") for pid, p in people.by_id.items()}
    group_names = sorted(people.groups, key=str.casefold)
    group_row = {g: resolve(g, "group") for g in group_names}
    if unresolved:
        for kind, name, n in unresolved:
            print(f"NO identity.csv row ({n} matches) for {kind}: {name!r}", file=sys.stderr)
        sys.exit("stopped: add or fix the identity.csv row (do not mint silently); see ontology/tools/mint_id.py")

    # -- links ---------------------------------------------------------------
    lc_groups = {g.casefold(): g for g in group_names}

    def group_of_headless(role_raw):
        hits = [g for g in group_names if g.casefold() in role_raw.casefold()]
        assert len(hits) == 1, f"cannot tell which group this list item names: {role_raw!r} -> {hits}"
        return hits[0]

    links = []  # dicts: story, idx, kind, canonical, role, later
    for s in stories:
        for idx, line in enumerate(s["lines"], 1):
            role = raw(line["role"])
            members = [(k, v) for k, v in line["head"] if k in ("p", "g")]
            # the two bullets with no dash: the bold part is a group and the whole item is the text (bold marks dropped)
            assert role in (text if members else text.replace("**", "")), f"role text not found verbatim in source: {role!r}"
            if not members:
                members = [("g", group_of_headless(role))]
            for kind, val in members:
                if kind == "p":
                    row, k = person_row[val], "person"
                else:
                    val = lc_groups.get(val.casefold(), val)
                    row, k = group_row[val], "group"
                links.append({"story": s["n"], "idx": idx, "kind": k, "canonical": row["canonical_id"],
                              "role": role, "later": line["later"]})

    paras = {}
    src_lines = set(text.splitlines())
    for s in stories:
        ps = [raw(p) for p in s["paras"]]
        for p in ps:
            assert p in src_lines, f"paragraph not found verbatim in source: {p[:60]!r}"
        paras[s["n"]] = "\n\n".join(ps)

    # -- IDs -----------------------------------------------------------------
    led = Ledger()
    ids = {
        "agent": led.get("agent", "agt"), "activity": led.get("activity", "act"),
        "maintainer": led.get("maintainer", "agt"),
        "work": led.get("work", "wrk"), "witness": led.get("witness", "wit"),
    }
    part_id = {i: led.get(f"part:{i}", "psg") for i in range(1, 5)}
    ev_id = {s["n"]: led.get(f"story-event:{s['n']}", "ev") for s in stories}
    psg_id = {s["n"]: led.get(f"story-passage:{s['n']}", "psg") for s in stories}
    for L in links:
        L["id"] = led.get(f"assertion:{L['story']}:{L['idx']}:{L['canonical']}", "ast")

    # -- identity.csv: register the story events -----------------------------
    existing = {r["canonical_id"] for r in rows}
    added = 0
    for s in stories:
        if ev_id[s["n"]] not in existing:
            rows.append({
                "kind": "event", "canonical_id": ev_id[s["n"]], "preferred_name_en": s["title"], "name_ar": "",
                "variant_ids": "", "stories50_names": s["title"], "source_files": "stories-50", "confidence": "exact",
                "note": f"story-unit event minted in slice 1c for story {s['n']} of the 50 Stories doc; NOT identified "
                        "with any seed-incidents/generation-1/thawr event (alignment is a scholar decision)"})
            added += 1
    return {"parts": parts, "stories": stories, "people": people, "rows": rows, "links": links, "paras": paras,
            "person_row": person_row, "group_row": group_row, "ids": ids, "part_id": part_id, "ev_id": ev_id,
            "psg_id": psg_id, "led": led, "added_rows": added}


def curie_ok(c):
    assert re.fullmatch(r"[a-z]+:[A-Za-z0-9]{22}", c), c
    return c


HEADER = """@prefix mrs:  <https://w3id.org/marsad/core#> .
@prefix mrsv: <https://w3id.org/marsad/vocab/> .
@prefix crm:  <http://www.cidoc-crm.org/cidoc-crm/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

@prefix per: <https://w3id.org/marsad/id/person/> .
@prefix grp: <https://w3id.org/marsad/id/group/> .
@prefix ev:  <https://w3id.org/marsad/id/event/> .
@prefix ast: <https://w3id.org/marsad/id/assertion/> .
@prefix agt: <https://w3id.org/marsad/id/agent/> .
@prefix act: <https://w3id.org/marsad/id/activity/> .
@prefix psg: <https://w3id.org/marsad/id/passage/> .
@prefix wit: <https://w3id.org/marsad/id/witness/> .
@prefix wrk: <https://w3id.org/marsad/id/work/> .

#################################################################
#
#  50 STORIES -- the maintainer's doc as Turtle (slice 1c)
#
#  /!\\  UNVERIFIED SECONDARY COMPILATION. NOT SCHOLAR-REVIEWED.
#
#  GENERATED by ontology/tools/stories50_to_ttl.py from
#  stories-50/source/50-stories.md (rev 7, exported 10 October 2026)
#  and ontology/corpus/identity.csv. Do not edit by hand; change the
#  source or the table and re-run the script.
#
#  The doc was written from general knowledge, without live access to
#  the classical sources. Every story and every link below is therefore
#  unverified: every Assertion is assertionStatus = proposed with
#  coverageState = stub, and no adjudicator is recorded. Nothing here
#  is knowledge under docs/06 until a credentialed reviewer says so.
#
#  MODELLING CHOICES
#   - A story is an mrs:Event: the occurrence the story narrates. It is
#     NOT identified with any event in the other corpus files (Badr,
#     Uhud, the Hijra ...); that alignment is a scholar's decision.
#   - The prose is kept verbatim on an mrs:Passage (crm:E33), one per
#     story, inside a Passage per Part, inside the mrs:Work (the doc);
#     the Markdown export is the mrs:Witness. Order and Part number are
#     skos:notation (integers); marsad.ttl has no ordinal property.
#   - Each person/group in a story's "Companions connected to this
#     story" list is one mrs:Assertion, predicate rel_participated_in
#     (the doc's introduction says the lists name each Companion "who
#     took part in it"), with the doc's role text verbatim in
#     rdfs:comment and a mrs:nonReportBasis (no Report exists).
#   - "(accepted Islam later)" is kept as a mrs:qualifier on the link.
#   - People and groups use canonical IDs from identity.csv only. A
#     Person node is declared here only if no other corpus file
#     declares it.
#
#################################################################

"""


def render(d):
    parts, stories, people = d["parts"], d["stories"], d["people"]
    ids, ev_id, psg_id, part_id = d["ids"], d["ev_id"], d["psg_id"], d["part_id"]
    declared = persons_declared_elsewhere()
    out = [HEADER]
    w = out.append

    # agents and the extraction activity
    w(f"""{curie_ok(ids['agent'])}
    a prov:SoftwareAgent ;
    rdfs:label {lit("Conversion of the 50 Stories doc to Turtle (ontology/tools/stories50_to_ttl.py, slice 1c)")} .

{curie_ok(ids['maintainer'])}
    a prov:Person ;
    rdfs:label {lit("Project maintainer, author of the 50 Stories doc (byline as in stories-50/source/50-stories.md)")} .

{curie_ok(ids['activity'])}
    a prov:Activity ;
    prov:startedAtTime "{RECORDED}"^^xsd:dateTime ;
    prov:qualifiedAssociation [
        a prov:Association ;
        prov:agent {ids['agent']} ;
        prov:hadRole mrs:role_extractor ] .
    # NO adjudicator association. Nothing here has been reviewed.

""")

    base = f"""    mrs:coverageState mrs:cs_stub ;
    mrs:createdBy {ids['agent']} ;
    mrs:recordedAt "{RECORDED}"^^xsd:dateTime"""

    # the work, the witness, the parts
    w(f"""{curie_ok(ids['work'])}
    a mrs:Work ;
    rdfs:label {lit("50 Stories of the Prophet Muhammad ﷺ and His Companions")} ;
    rdfs:comment {lit("The maintainer's Claude Doc. An unverified secondary compilation: written from general knowledge, without live access to the classical sources. Names, numbers and attributions are not checked.")} ;
    dct:creator {ids['maintainer']} ;
    dct:hasVersion "rev 7" ;
{base} .

{curie_ok(ids['witness'])}
    a mrs:Witness ;
    rdfs:label {lit("Markdown export of the doc, rev 7, 10 October 2026 (stories-50/source/50-stories.md)")} ;
    dct:isVersionOf {ids['work']} ;
    dct:created "2026-10-10"^^xsd:date ;
{base} .

""")
    for i, p in enumerate(parts, 1):
        w(f"""{curie_ok(part_id[i])}
    a mrs:Passage ;
    rdfs:label {lit(f"Part {i}: {p['title']}")} ;
    mrs:canonicalCitation {lit(f"50 Stories (rev 7), Part {i}", None)} ;
    skos:notation {i} ;
    mrs:inWitness {ids['witness']} ;
    dct:isPartOf {ids['work']} ;
{base} .

""")

    w('''mrsv:q_accepted_islam_later
    a mrs:Qualifier ;
    rdfs:label "accepted Islam later"@en ;
    rdfs:comment """The 50 Stories doc's own marker. Its introduction: "People who opposed Islam at the time of the story but later became Muslim are included, marked *(accepted Islam later)*." Carried on the link as the doc states it; the doc's own wording for each link (for example "by most accounts") stays in that link's rdfs:comment."""@en .

''')

    # groups, then people not declared elsewhere
    used_groups = sorted({L["canonical"] for L in d["links"] if L["kind"] == "group"})
    grow = {r["canonical_id"]: r for r in d["group_row"].values()}
    for gid in used_groups:
        r = grow[gid]
        w(f"""{curie_ok(gid)}
    a mrs:Group ;
    rdfs:label {lit(r['preferred_name_en'])} ;
{base} .

""")
    n_declared = 0
    done = set()
    for pid, p in sorted(people.by_id.items(), key=lambda kv: d["person_row"][kv[0]]["preferred_name_en"].casefold()):
        r = d["person_row"][pid]
        c = r["canonical_id"]
        if c in declared or c in done:
            continue
        done.add(c)
        n_declared += 1
        forms = [p["name"]] + p["aka"]
        nf = " ,\n        ".join(
            f"[ a mrs:ArabicNameForm ; rdfs:label {lit(f)} ; mrs:script \"latn\" ; mrs:transliterationScheme {lit(SCHEME, None)} ]"
            for f in forms)
        w(f"""{curie_ok(c)}
    a mrs:Person ;
    rdfs:label {lit(r['preferred_name_en'])} ;
{base} ;
    mrs:nameForm
        {nf} .

""")

    # stories
    for s in stories:
        n = s["n"]
        part_no = s["part"] + 1
        note = f" ;\n    skos:note {lit(raw(s['note']))}" if s["note"] else ""
        w(f"""{curie_ok(ev_id[n])}
    a mrs:Event ;
    rdfs:label {lit(s['title'])} ;
    skos:notation {n} ;
    crm:P67i_is_referred_to_by {psg_id[n]} ;
{base} .

{curie_ok(psg_id[n])}
    a mrs:Passage ;
    rdfs:label {lit(s['title'])} ;
    mrs:canonicalCitation {lit(f"50 Stories (rev 7), Part {part_no}, story {n}", None)} ;
    skos:notation {n} ;
    mrs:inWitness {ids['witness']} ;
    dct:isPartOf {part_id[part_no]} ;
    crm:P67_refers_to {ev_id[n]} ;
    crm:P190_has_symbolic_content {lit(d['paras'][n])}{note} ;
{base} .

""")

    # assertions
    title = {s["n"]: s["title"] for s in stories}
    for L in d["links"]:
        n = L["story"]
        basis = (f"Companion list of story {n} ('{title[n]}') in the maintainer's 50 Stories doc, rev 7, 10 October 2026: "
                 "an unverified secondary compilation written from general knowledge. No source edition or passage is attached to this link.")
        later = " ;\n    mrs:qualifier mrsv:q_accepted_islam_later" if L["later"] else ""
        w(f"""{curie_ok(L['id'])}
    a mrs:Assertion ;
{base} ;
    mrs:predicate mrs:rel_participated_in ;
    mrs:assertionSubject {L['canonical']} ;
    mrs:assertionObject {ev_id[n]} ;
    mrs:assertionStatus mrs:as_proposed ;
    mrs:nonReportBasis {lit(basis)} ;
    rdfs:comment {lit(L['role'])} ;
    prov:wasDerivedFrom {psg_id[n]} ;
    prov:wasGeneratedBy {ids['activity']}{later} .

""")
    return "".join(out), n_declared


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if stories-50.ttl or the identity rows are out of date")
    args = ap.parse_args()

    d = build()
    ttl, n_declared = render(d)
    if args.check:
        stale = (not OUT.exists() or OUT.read_text(encoding="utf-8") != ttl
                 or d["led"].dirty or d["added_rows"])
        print("stories-50.ttl is stale" if stale else "stories-50.ttl is up to date")
        sys.exit(1 if stale else 0)

    if d["led"].dirty:
        d["led"].save()
    if d["added_rows"]:
        write_identity(d["rows"])
    OUT.write_text(ttl, encoding="utf-8")

    links = d["links"]
    print(f"stories: {len(d['stories'])} events + {len(d['stories'])} passages, {len(d['parts'])} part passages")
    print(f"links:   {len(links)} assertions ({sum(1 for L in links if L['kind'] == 'person')} person, "
          f"{sum(1 for L in links if L['kind'] == 'group')} group), "
          f"{sum(1 for L in links if L['later'])} carry the 'accepted Islam later' qualifier")
    print(f"people:  {len({L['canonical'] for L in links if L['kind'] == 'person'})} referenced, "
          f"{n_declared} declared here (the rest are declared in other corpus files)")
    print(f"groups:  {len({L['canonical'] for L in links if L['kind'] == 'group'})}")
    print(f"ids:     {len(d['led'].ids)} in {LEDGER.relative_to(ROOT)}; {d['added_rows']} story-event rows added to identity.csv")
    print(f"wrote:   {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
