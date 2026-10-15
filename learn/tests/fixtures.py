"""Small fixture graphs for the learn tests. Every name and ID here is made up for the
tests ("Person A", "fxEventB"); nothing is taken from the corpus."""
from __future__ import annotations

from pathlib import Path

from rdflib import Graph

ID = "https://w3id.org/marsad/id/"
PREFIXES = """@prefix mrs:  <https://w3id.org/marsad/core#> .
@prefix mrsv: <https://w3id.org/marsad/vocab/> .
@prefix crm:  <http://www.cidoc-crm.org/cidoc-crm/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix time: <http://www.w3.org/2006/time#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix id:   <https://w3id.org/marsad/id/> .
"""
RELATIONS = {
    "rel_participated_in": "participated in", "rel_led": "led", "rel_present_at": "present at",
    "rel_witnessed": "witnessed", "rel_absent_from": "absent from", "rel_part_of": "part of",
    "rel_father_of": "father of", "rel_preceded": "preceded", "rel_followed": "followed",
}
STATUSES = ("proposed", "under_review", "accepted", "rejected", "superseded")


def lit(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"@en'


class Fx:
    """Builds a small Turtle graph. Methods return the IRI they mint."""

    def __init__(self):
        self.out: list[str] = [PREFIXES]
        for rel, label in RELATIONS.items():
            self.out.append(f"mrs:{rel} a mrs:RelationType ; skos:prefLabel {lit(label)} .")
        for st in STATUSES:
            self.out.append(f"mrs:as_{st} a mrs:AssertionStatus ; skos:prefLabel {lit(st.replace('_', ' '))} .")
        self.out.append(f"mrsv:q_later a mrs:Qualifier ; rdfs:label {lit('marker for the tests')} .")
        self.n = 0

    def _id(self, kind: str, pid: str) -> str:
        return f"{ID}{kind}/{pid}"

    def person(self, pid: str, label: str) -> str:
        iri = self._id("person", pid)
        self.out.append(f"<{iri}> a mrs:Person ; rdfs:label {lit(label)} ; mrs:coverageState mrs:cs_stub .")
        return iri

    def group(self, pid: str, label: str) -> str:
        iri = self._id("group", pid)
        self.out.append(f"<{iri}> a mrs:Group ; rdfs:label {lit(label)} .")
        return iri

    def place(self, pid: str, label: str) -> str:
        iri = self._id("place", pid)
        self.out.append(f"<{iri}> a mrs:Place ; rdfs:label {lit(label)} .")
        return iri

    def event(self, pid: str, label: str, *, dates: tuple[str, str] | None = None, place: str | None = None,
              anchors: list[tuple[str, str, str | None]] = ()) -> str:
        """anchors: (allen relation local name, target IRI, attesting claim IRI or None)."""
        iri = self._id("event", pid)
        parts = [f"<{iri}> a mrs:Event", f"rdfs:label {lit(label)}", "mrs:coverageState mrs:cs_stub"]
        if place:
            parts.append(f"mrs:eventPlace <{place}>")
        if dates or anchors:
            te = self._id("temporal", pid + "T")
            parts.append(f"mrs:eventTemporalExtent <{te}>")
            t = [f"<{te}> a mrs:TemporalExtent", "mrs:precision mrs:pr_year"]
            if dates:
                t.append(f'mrs:earliestStart "{dates[0]}T00:00:00Z"^^xsd:dateTime')
                t.append(f'mrs:latestEnd "{dates[1]}T23:59:59Z"^^xsd:dateTime')
            for rel, target, att in anchors:
                a = f"mrs:allenRelation time:{rel} ; mrs:anchorTarget <{target}>"
                if att:
                    a += f" ; mrs:attestedBy <{att}>"
                t.append(f"mrs:relativeAnchor [ a mrs:RelativeAnchor ; {a} ]")
            self.out.append(" ;\n    ".join(t) + " .")
        self.out.append(" ;\n    ".join(parts) + " .")
        return iri

    def participation(self, event: str, who: str, role: str = "role_participant"):
        self.out.append(f"<{event}> mrs:hasParticipation [ a mrs:Participation ; mrs:participant <{who}> ; "
                        f"mrs:participantRole mrs:{role} ] .")

    def claim(self, subject: str, predicate: str, obj: str, statuses=("proposed",), *, pid: str | None = None,
              role: str | None = None, qualifiers=(), basis: str | None = "Fixture basis.") -> str:
        self.n += 1
        iri = self._id("assertion", pid or f"fxClaim{self.n}")
        parts = [f"<{iri}> a mrs:Assertion", f"mrs:assertionSubject <{subject}>", f"mrs:predicate mrs:{predicate}",
                 f"mrs:assertionObject <{obj}>"]
        for st in statuses:
            parts.append(f"mrs:assertionStatus mrs:as_{st}")
        if role:
            parts.append(f"rdfs:comment {lit(role)}")
        for q in qualifiers:
            parts.append(f"mrs:qualifier mrsv:{q}")
        if basis:
            parts.append(f"mrs:nonReportBasis {lit(basis)}")
        self.out.append(" ;\n    ".join(parts) + " .")
        return iri

    def story_doc(self, pid: str, title: str) -> str:
        iri = self._id("work", pid)
        self.out.append(f"<{iri}> a mrs:Work ; rdfs:label {lit(title)} .")
        return iri

    def story_part(self, pid: str, work: str, label: str, number: int) -> str:
        iri = self._id("passage", pid)
        self.out.append(f"<{iri}> a mrs:Passage ; rdfs:label {lit(label)} ; skos:notation {number} ; dct:isPartOf <{work}> .")
        return iri

    def story(self, pid: str, label: str, number: int, part: str, text: str = "Fixture story text.") -> str:
        ev = self._id("event", pid)
        psg = self._id("passage", pid + "P")
        self.out.append(f"<{ev}> a mrs:Event ; rdfs:label {lit(label)} ; skos:notation {number} ; mrs:coverageState mrs:cs_stub .")
        self.out.append(f"<{psg}> a mrs:Passage ; rdfs:label {lit(label)} ; crm:P67_refers_to <{ev}> ; "
                        f"dct:isPartOf <{part}> ; crm:P190_has_symbolic_content {lit(text)} .")
        return ev

    def ttl(self) -> str:
        return "\n".join(self.out) + "\n"

    def graph(self) -> Graph:
        g = Graph()
        g.parse(data=self.ttl(), format="turtle")
        return g

    def write(self, path: Path) -> Path:
        Path(path).write_text(self.ttl(), encoding="utf-8")
        return Path(path)
