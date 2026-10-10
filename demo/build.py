#!/usr/bin/env python3
"""
Build the demo's data from the ontology — a derived projection, not a copy.

    pip install rdflib
    python demo/build.py

Reads the real Turtle files, runs SPARQL against them, and injects the result
into demo/index.template.html to produce demo/index.html.

This matters. If the demo hardcoded its data in JavaScript it would be lying
about the architecture it claims to demonstrate: the whole design says the
renderer may only show what the evidence layer publishes. So the renderer
here consumes a rebuildable projection of the canonical Turtle, exactly as
L4 -> L6 does in docs/01 §6. Change the Turtle, re-run this, and the demo
changes. Nothing is drawn that is not in the graph.
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
SOURCES = [ONT / "marsad.ttl", ONT / "relations.ttl", ONT / "examples" / "thawr.ttl"]
TEMPLATE = ROOT / "demo" / "index.template.html"
OUT = ROOT / "demo" / "index.html"
DATA_OUT = ROOT / "demo" / "data.json"

PREFIX = """
PREFIX mrs:  <https://w3id.org/marsad/core#>
PREFIX mrsv: <https://w3id.org/marsad/vocab/>
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
    data = {}

    data["persons"] = q(g, """
        SELECT ?id ?label ?tabaqa ?coverage ?role WHERE {
            ?id a mrs:Person ; rdfs:label ?label ; mrs:coverageState ?cov .
            ?cov skos:prefLabel ?coverage .
            OPTIONAL { ?id mrs:tabaqa ?tb . ?tb skos:prefLabel ?tabaqa }
            OPTIONAL { ?id mrs:transmitterRole ?tr . ?tr skos:prefLabel ?role }
        } ORDER BY ?label
    """)

    data["chain"] = q(g, """
        SELECT ?chain ?chainLabel ?collector ?terminal WHERE {
            ?chain a mrs:TransmissionChain ; rdfs:label ?chainLabel .
            OPTIONAL { ?chain mrs:collector ?collector }
            OPTIONAL { ?chain mrs:terminalNarrator ?terminal }
        }
    """)

    # Continuity is deliberately absent in the source. The query asks for it
    # anyway, so the demo can show an EMPTY field rather than omitting the row.
    data["continuity"] = q(g, """
        SELECT ?chain ?continuity WHERE {
            ?chain a mrs:TransmissionChain .
            OPTIONAL { ?chain mrs:continuity ?c . ?c skos:prefLabel ?continuity }
        }
    """)

    data["links"] = q(g, """
        SELECT ?order ?from ?fromLabel ?to ?toLabel ?mode ?result ?basis WHERE {
            ?chain a mrs:TransmissionChain ; mrs:hasLink ?link .
            ?link mrs:linkOrder ?order ;
                  mrs:fromNarrator ?from ; mrs:toNarrator ?to ;
                  mrs:transmissionMode ?m .
            ?m skos:prefLabel ?mode .
            ?from rdfs:label ?fromLabel .
            ?to rdfs:label ?toLabel .
            OPTIONAL {
                ?link mrs:contactCheck ?cc .
                ?cc mrs:checkResult ?r ; mrs:checkBasis ?b .
                ?r skos:prefLabel ?result . ?b skos:prefLabel ?basis
            }
        } ORDER BY ?order
    """)

    data["report"] = q(g, """
        SELECT ?id ?label ?genre ?ascription ?citation ?sourceNative
               ?sourceStart ?sourceEnd WHERE {
            ?id a mrs:Hadith ; rdfs:label ?label ;
                mrs:reportGenre ?g2 ; mrs:terminalAscription ?a2 ;
                mrs:locatedIn ?psg ; mrs:sourceDate ?sd .
            ?g2 skos:prefLabel ?genre .
            ?a2 skos:prefLabel ?ascription .
            ?psg mrs:canonicalCitation ?citation .
            ?sd mrs:nativeValue ?sourceNative .
            OPTIONAL { ?sd mrs:earliestStart ?sourceStart }
            OPTIONAL { ?sd mrs:latestEnd ?sourceEnd }
        }
    """)

    data["evaluation"] = q(g, """
        SELECT ?evaluatorLabel ?grade ?tradition ?justification ?citation WHERE {
            ?e a mrs:Evaluation ;
               mrs:evaluator ?ev ; mrs:grade ?gr ;
               mrs:tradition ?tr ; mrs:locatedIn ?psg .
            ?ev rdfs:label ?evaluatorLabel .
            ?gr skos:prefLabel ?grade .
            ?tr skos:prefLabel ?tradition .
            ?psg mrs:canonicalCitation ?citation .
            OPTIONAL { ?e mrs:justification ?justification }
        }
    """)

    data["event"] = q(g, """
        SELECT ?id ?label ?placeLabel ?native ?precision ?basis WHERE {
            ?id a mrs:Event ; rdfs:label ?label ;
                mrs:eventPlace ?p ; mrs:eventTemporalExtent ?t .
            ?p rdfs:label ?placeLabel .
            ?t mrs:nativeValue ?native ; mrs:precision ?pr ; mrs:temporalBasis ?b .
            ?pr skos:prefLabel ?precision .
            ?b skos:prefLabel ?basis .
        }
    """)

    data["participants"] = q(g, """
        SELECT ?personLabel ?role WHERE {
            ?ev a mrs:Event ; mrs:eventPlace ?p ; mrs:hasParticipation ?part .
            ?part mrs:participant ?person ; mrs:participantRole ?r .
            ?person rdfs:label ?personLabel .
            ?r skos:prefLabel ?role .
        }
    """)

    data["anchors"] = q(g, """
        SELECT ?relation ?targetLabel WHERE {
            ?ev a mrs:Event ; mrs:eventTemporalExtent ?t .
            ?t mrs:relativeAnchor ?a .
            ?a mrs:allenRelation ?relation ; mrs:anchorTarget ?target .
            OPTIONAL { ?target rdfs:label ?targetLabel }
        }
    """)

    data["places"] = q(g, """
        SELECT ?id ?label ?type ?wkt ?confidence ?basis WHERE {
            ?id a mrs:Place ; rdfs:label ?label ; mrs:placeType ?pt .
            ?pt skos:prefLabel ?type .
            OPTIONAL {
                ?id mrs:geometryState ?gs .
                ?gs mrs:locationConfidence ?lc ; mrs:geometryBasis ?gb .
                ?lc skos:prefLabel ?confidence .
                ?gb skos:prefLabel ?basis .
                OPTIONAL { ?gs mrs:geometry ?geom . ?geom geo:asWKT ?wkt }
            }
        } ORDER BY ?label
    """)

    data["namePhases"] = q(g, """
        SELECT ?place ?name WHERE {
            ?place a mrs:Place ; mrs:namePhase ?np .
            ?np mrs:phaseName ?name .
        }
    """)

    data["segments"] = q(g, """
        SELECT ?order ?fromLabel ?toLabel ?confidence ?mode ?wkt WHERE {
            ?r a mrs:Route ; mrs:hasSegment ?s .
            ?s mrs:segmentOrder ?order ;
               mrs:segmentFrom ?from ; mrs:segmentTo ?to ;
               mrs:segmentConfidence ?c .
            ?c skos:prefLabel ?confidence .
            ?from rdfs:label ?fromLabel .
            ?to rdfs:label ?toLabel .
            OPTIONAL { ?s mrs:travelMode ?m . ?m skos:prefLabel ?mode }
            OPTIONAL { ?s mrs:segmentGeometry ?geom . ?geom geo:asWKT ?wkt }
        } ORDER BY ?order
    """)

    data["disputes"] = q(g, """
        SELECT ?id ?label ?question ?significance ?status WHERE {
            ?id a mrs:Dispute ; mrs:disputeQuestion ?question ;
                mrs:disputeSignificance ?sig ; mrs:disputeStatus ?st .
            ?sig skos:prefLabel ?significance .
            ?st skos:prefLabel ?status .
            OPTIONAL { ?id rdfs:label ?label }
        }
    """)

    data["positions"] = q(g, """
        SELECT ?dispute ?claim WHERE {
            ?dispute a mrs:Dispute ; mrs:hasPosition ?p .
            ?p mrs:positionClaim ?claim .
        }
    """)

    data["assertion"] = q(g, """
        SELECT ?id ?predicate ?subjectLabel ?objectLabel ?status
               ?agentLabel ?agentType ?role WHERE {
            ?id a mrs:Assertion ;
                mrs:predicate ?pred ; mrs:assertionStatus ?st ;
                mrs:assertionSubject ?subj ; mrs:assertionObject ?obj ;
                prov:wasGeneratedBy ?act .
            ?pred skos:prefLabel ?predicate .
            ?st skos:prefLabel ?status .
            ?subj rdfs:label ?subjectLabel .
            ?obj rdfs:label ?objectLabel .
            ?act prov:qualifiedAssociation ?assoc .
            ?assoc prov:agent ?agent ; prov:hadRole ?r .
            ?r skos:prefLabel ?role .
            ?agent rdfs:label ?agentLabel ; a ?agentType .
            FILTER (?agentType IN (prov:SoftwareAgent, prov:Person))
        }
    """)

    # Did anybody adjudicate? The demo shows the answer either way.
    data["adjudicated"] = q(g, """
        SELECT ?role WHERE {
            ?a a mrs:Assertion ; prov:wasGeneratedBy ?act .
            ?act prov:qualifiedAssociation ?assoc .
            ?assoc prov:hadRole mrs:role_adjudicator .
            ?assoc prov:hadRole ?r . ?r skos:prefLabel ?role .
        }
    """)

    return data


def main():
    g = Graph()
    for f in SOURCES:
        if not f.exists():
            sys.exit(f"missing: {f}")
        g.parse(f, format="turtle")
    print(f"parsed {len(g)} triples from {len(SOURCES)} files")

    data = build(g)
    for k, v in data.items():
        print(f"  {k:<14} {len(v)}")

    DATA_OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {DATA_OUT.relative_to(ROOT)}")

    if TEMPLATE.exists():
        html = TEMPLATE.read_text(encoding="utf-8")
        marker = "/*__GRAPH_DATA__*/"
        if marker not in html:
            sys.exit(f"template is missing the {marker} marker")
        html = html.replace(marker, json.dumps(data, ensure_ascii=False))
        OUT.write_text(html, encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}")
    else:
        print("(no template yet — data only)")


if __name__ == "__main__":
    main()
