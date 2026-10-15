#!/usr/bin/env python3
"""
Build the first-generation demo's data from the ontology — a derived
projection, not a copy. Mirrors demo/build.py's discipline: nothing in
the rendered page is typed in by hand; everything comes from SPARQL
against the real Turtle.

    pip install rdflib
    python generation-1/build.py
"""

import json
import sys
from pathlib import Path

try:
    from rdflib import Graph
except ImportError:
    sys.exit("Requires rdflib:  pip install rdflib")

ROOT = Path(__file__).resolve().parent.parent
ONT = ROOT / "ontology"
CORE_SOURCES = [ONT / "marsad.ttl", ONT / "relations.ttl", ONT / "corpus" / "generation-1.ttl"]
SEED_FILE = ONT / "corpus" / "seed-incidents.ttl"
SEED_SOURCES = CORE_SOURCES + [SEED_FILE]

# generation-1.ttl's own compilation agent — used to tell "the original 35/6"
# apart from the seed batch's new people/events in the combined seed graph,
# without needing a second SPARQL round-trip.
GEN1_AGENT = "https://w3id.org/marsad/id/agent/C7VpyqaTGtImKPBS8frhTf"

TEMPLATES = [
    (ROOT / "generation-1" / "at-scale.template.html", ROOT / "generation-1" / "at-scale.html"),
]
# index.html ("The First Generation") moved here 18 Sept 2026: it now
# renders the full core+seed network (57 persons / 44 events), not just
# the original curated 35/6 — see README "The wider network" section.
SEED_TEMPLATES = [
    (ROOT / "generation-1" / "index.template.html", ROOT / "generation-1" / "index.html"),
    (ROOT / "generation-1" / "wider-network.template.html", ROOT / "generation-1" / "wider-network.html"),
]
DATA_OUT = ROOT / "generation-1" / "data.json"
SEED_DATA_OUT = ROOT / "generation-1" / "seed-data.json"

PREFIX = """
PREFIX mrs:  <https://w3id.org/marsad/core#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX geo:  <http://www.opengis.net/ont/geosparql#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""


def q(g, query):
    return [
        {str(v): (str(row[v]) if row[v] is not None else None) for v in row.labels}
        for row in g.query(PREFIX + query)
    ]


def build(g):
    d = {}

    d["persons"] = q(g, """
        SELECT ?id ?label ?tabaqa ?coverage ?role WHERE {
            ?id a mrs:Person ; rdfs:label ?label ; mrs:coverageState ?cov .
            ?cov skos:prefLabel ?coverage .
            OPTIONAL { ?id mrs:tabaqa ?tb . ?tb skos:prefLabel ?tabaqa }
            OPTIONAL { ?id mrs:transmitterRole ?tr . ?tr skos:prefLabel ?role }
        } ORDER BY ?label
    """)

    d["deaths"] = q(g, """
        SELECT ?person ?native WHERE {
            ?person a mrs:Person ; mrs:death ?d .
            ?d mrs:eventTemporalExtent ?t . ?t mrs:nativeValue ?native .
        }
    """)

    d["event"] = q(g, """
        SELECT ?id ?label ?placeLabel ?native ?earliestStart WHERE {
            ?id a mrs:Event ; rdfs:label ?label ;
                mrs:eventPlace ?p ; mrs:eventTemporalExtent ?t .
            ?p rdfs:label ?placeLabel .
            ?t mrs:nativeValue ?native .
            OPTIONAL { ?t mrs:earliestStart ?earliestStart }
        } ORDER BY ?earliestStart
    """)

    d["participation"] = q(g, """
        SELECT ?event ?person ?role WHERE {
            ?event a mrs:Event ; mrs:hasParticipation ?part .
            ?part mrs:participant ?person ; mrs:participantRole ?r .
            ?r skos:prefLabel ?role .
        }
    """)

    d["eventAssertions"] = q(g, """
        SELECT ?event ?predicate ?subjectLabel ?basis WHERE {
            ?a a mrs:Assertion ; mrs:predicate ?p ;
               mrs:assertionSubject ?subj ; mrs:assertionObject ?event ;
               mrs:nonReportBasis ?basis .
            ?p skos:prefLabel ?predicate .
            ?subj rdfs:label ?subjectLabel .
            ?event a mrs:Event .
            FILTER (?p != mrs:rel_absent_from)
        }
    """)

    d["absences"] = q(g, """
        SELECT ?subjectLabel ?subject ?event ?basis WHERE {
            ?a a mrs:Assertion ; mrs:predicate mrs:rel_absent_from ;
               mrs:assertionSubject ?subject ; mrs:assertionObject ?event ;
               mrs:nonReportBasis ?basis .
            ?subject rdfs:label ?subjectLabel .
        }
    """)

    d["companionOf"] = q(g, """
        SELECT ?person WHERE {
            ?a a mrs:Assertion ; mrs:predicate mrs:rel_companion_of ;
               mrs:assertionObject ?person .
        }
    """)

    d["kinship"] = q(g, """
        SELECT ?predicate ?subject ?subjectLabel ?object ?objectLabel ?basis WHERE {
            ?a a mrs:Assertion ; mrs:predicate ?p ;
               mrs:assertionSubject ?subject ; mrs:assertionObject ?object ;
               mrs:nonReportBasis ?basis .
            ?p skos:prefLabel ?predicate .
            ?subject rdfs:label ?subjectLabel . ?object rdfs:label ?objectLabel .
            FILTER (?p IN (mrs:rel_father_of, mrs:rel_spouse_of, mrs:rel_sibling_of))
        } ORDER BY ?subjectLabel
    """)

    d["disputes"] = q(g, """
        SELECT ?event ?question ?significance ?claim WHERE {
            ?d a mrs:Dispute ; mrs:disputeSubject ?event ;
               mrs:disputeQuestion ?question ; mrs:disputeSignificance ?sig ;
               mrs:hasPosition ?pos .
            ?sig skos:prefLabel ?significance .
            ?pos mrs:positionClaim ?claim .
            ?event a mrs:Event .
        }
    """)

    d["coverageGap"] = q(g, """
        SELECT ?description ?cause WHERE {
            ?e a mrs:Event ; mrs:coverageGap ?g .
            ?g mrs:gapDescription ?description ; mrs:gapCause ?c .
            ?c skos:prefLabel ?cause .
        }
    """)

    d["allAssertions"] = q(g, """
        SELECT (COUNT(*) AS ?n) WHERE { ?a a mrs:Assertion }
    """)
    d["proposedCount"] = q(g, """
        SELECT (COUNT(*) AS ?n) WHERE { ?a a mrs:Assertion ; mrs:assertionStatus mrs:as_proposed }
    """)

    return d


def build_seed(g):
    """The generation-1 + seed-incidents union graph, projected for the
    'Wider Network' page: every Person/Event across both files, every
    Participation, and every Assertion in its general subject/predicate/
    object form (object may be an Event, a Place, or another Person) — the
    shape the seed batch actually needs, since its incidents aren't all
    person-to-event the way generation-1.ttl's are."""
    d = {}

    d["persons"] = q(g, """
        SELECT ?id ?label ?tabaqa ?coverage ?createdBy WHERE {
            ?id a mrs:Person ; rdfs:label ?label ; mrs:coverageState ?cov ; mrs:createdBy ?createdBy .
            ?cov skos:prefLabel ?coverage .
            OPTIONAL { ?id mrs:tabaqa ?tb . ?tb skos:prefLabel ?tabaqa }
        } ORDER BY ?label
    """)

    d["events"] = q(g, """
        SELECT ?id ?label ?placeLabel ?native ?earliestStart ?createdBy WHERE {
            ?id a mrs:Event ; rdfs:label ?label ; mrs:createdBy ?createdBy ;
                mrs:eventPlace ?p ; mrs:eventTemporalExtent ?t .
            ?p rdfs:label ?placeLabel .
            ?t mrs:nativeValue ?native .
            OPTIONAL { ?t mrs:earliestStart ?earliestStart }
        } ORDER BY ?earliestStart
    """)

    d["participation"] = q(g, """
        SELECT ?event ?person ?role WHERE {
            ?event a mrs:Event ; mrs:hasParticipation ?part .
            ?part mrs:participant ?person ; mrs:participantRole ?r .
            ?r skos:prefLabel ?role .
        }
    """)

    d["assertions"] = q(g, """
        SELECT ?id ?predicate ?subject ?subjectLabel ?object ?objectLabel ?objectType ?basis WHERE {
            ?id a mrs:Assertion ; mrs:predicate ?p ;
                mrs:assertionSubject ?subject ; mrs:assertionObject ?object ;
                mrs:nonReportBasis ?basis .
            ?p skos:prefLabel ?predicate .
            ?subject rdfs:label ?subjectLabel .
            ?object rdfs:label ?objectLabel .
            ?object a ?objectType .
            FILTER (?objectType IN (mrs:Event, mrs:Place, mrs:Person))
        } ORDER BY ?id
    """)

    d["kinship"] = q(g, """
        SELECT ?predicate ?subject ?subjectLabel ?object ?objectLabel ?basis WHERE {
            ?a a mrs:Assertion ; mrs:predicate ?p ;
               mrs:assertionSubject ?subject ; mrs:assertionObject ?object ;
               mrs:nonReportBasis ?basis .
            ?p skos:prefLabel ?predicate .
            ?subject rdfs:label ?subjectLabel . ?object rdfs:label ?objectLabel .
            FILTER (?p IN (mrs:rel_father_of, mrs:rel_spouse_of, mrs:rel_sibling_of))
        } ORDER BY ?subjectLabel
    """)

    d["deaths"] = q(g, """
        SELECT ?person ?native WHERE {
            ?person a mrs:Person ; mrs:death ?d .
            ?d mrs:eventTemporalExtent ?t . ?t mrs:nativeValue ?native .
        }
    """)

    d["disputes"] = q(g, """
        SELECT ?event ?question ?significance ?claim WHERE {
            ?d a mrs:Dispute ; mrs:disputeSubject ?event ;
               mrs:disputeQuestion ?question ; mrs:disputeSignificance ?sig ;
               mrs:hasPosition ?pos .
            ?sig skos:prefLabel ?significance .
            ?pos mrs:positionClaim ?claim .
            ?event a mrs:Event .
        }
    """)

    # Not restricted to mrs:Event here (unlike build()'s core query) — the
    # seed batch's own CoverageGap is linked from the origin Person, not an
    # Event, so a reader can find "what this whole file doesn't cover"
    # regardless of which kind of entity carries the link.
    d["coverageGap"] = q(g, """
        SELECT ?description ?cause WHERE {
            ?e mrs:coverageGap ?g .
            ?g mrs:gapDescription ?description ; mrs:gapCause ?c .
            ?c skos:prefLabel ?cause .
        }
    """)

    d["gen1Agent"] = GEN1_AGENT
    return d


def main():
    g = Graph()
    for f in CORE_SOURCES:
        if not f.exists():
            sys.exit(f"missing: {f}")
        g.parse(f, format="turtle")
    print(f"parsed {len(g)} triples from {len(CORE_SOURCES)} files (core)")

    data = build(g)
    for k, v in data.items():
        print(f"  {k:<16} {len(v)}")

    DATA_OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {DATA_OUT.relative_to(ROOT)}")

    marker = "/*__GRAPH_DATA__*/"
    payload = json.dumps(data, ensure_ascii=False)
    for template, out in TEMPLATES:
        if not template.exists():
            print(f"(skip — no template at {template.relative_to(ROOT)})")
            continue
        html = template.read_text(encoding="utf-8")
        if marker not in html:
            sys.exit(f"{template.relative_to(ROOT)} is missing the {marker} marker")
        out.write_text(html.replace(marker, payload), encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)}")

    if SEED_FILE.exists():
        g2 = Graph()
        for f in SEED_SOURCES:
            g2.parse(f, format="turtle")
        print(f"\nparsed {len(g2)} triples from {len(SEED_SOURCES)} files (core + seed)")

        seed_data = build_seed(g2)
        for k, v in seed_data.items():
            if isinstance(v, list):
                print(f"  {k:<16} {len(v)}")

        SEED_DATA_OUT.write_text(json.dumps(seed_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {SEED_DATA_OUT.relative_to(ROOT)}")

        seed_marker = "/*__SEED_DATA__*/"
        seed_payload = json.dumps(seed_data, ensure_ascii=False)
        for template, out in SEED_TEMPLATES:
            if not template.exists():
                print(f"(skip — no template at {template.relative_to(ROOT)})")
                continue
            html = template.read_text(encoding="utf-8")
            if seed_marker not in html:
                sys.exit(f"{template.relative_to(ROOT)} is missing the {seed_marker} marker")
            out.write_text(html.replace(seed_marker, seed_payload), encoding="utf-8")
            print(f"wrote {out.relative_to(ROOT)}")
    else:
        print("\n(skip seed layer — no ontology/corpus/seed-incidents.ttl yet)")


if __name__ == "__main__":
    main()
