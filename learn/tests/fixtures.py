"""Small fixture graphs for the learn tests. Every name and ID here is made up for the
tests ("Person A", "fxEventB"); nothing is taken from the corpus. The one label rule a
fixture has to meet is the Prophet's: site/display.py finds him by a label that starts
"The Prophet Muhammad", so the fixture Prophet carries such a label, with "(fixture)"."""
from __future__ import annotations

import json
import tempfile
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
    "rel_fought_alongside": "fought alongside", "rel_fought_against": "fought against",
    "rel_died_during": "died during", "rel_opposed": "opposed",
}
STATUSES = ("proposed", "under_review", "accepted", "rejected", "superseded")
PROPHET = "The Prophet Muhammad (fixture)"


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
        self.ext = 0

    def _id(self, kind: str, pid: str) -> str:
        return f"{ID}{kind}/{pid}"

    def person(self, pid: str, label: str, *more: str) -> str:
        iri = self._id("person", pid)
        labels = ", ".join(lit(x) for x in (label, *more))
        self.out.append(f"<{iri}> a mrs:Person ; rdfs:label {labels} ; mrs:coverageState mrs:cs_stub .")
        return iri

    def prophet(self, pid: str = "fxProphet") -> str:
        return self.person(pid, PROPHET)

    def group(self, pid: str, label: str) -> str:
        iri = self._id("group", pid)
        self.out.append(f"<{iri}> a mrs:Group ; rdfs:label {lit(label)} .")
        return iri

    def place(self, pid: str, label: str) -> str:
        iri = self._id("place", pid)
        self.out.append(f"<{iri}> a mrs:Place ; rdfs:label {lit(label)} .")
        return iri

    def extent(self, owner: str, earliest: str | None, latest: str | None, precision: str = "year",
               anchors: list[tuple[str, str, str | None]] = ()) -> str:
        """A temporal extent on any event or story; dates are YYYY-MM-DD."""
        self.ext += 1
        te = self._id("temporal", f"fxT{self.ext}")
        t = [f"<{te}> a mrs:TemporalExtent", f"mrs:precision mrs:pr_{precision}"]
        if earliest:
            t.append(f'mrs:earliestStart "{earliest}T00:00:00Z"^^xsd:dateTime')
        if latest:
            t.append(f'mrs:latestEnd "{latest}T23:59:59Z"^^xsd:dateTime')
        for rel, target, att in anchors:
            a = f"mrs:allenRelation time:{rel} ; mrs:anchorTarget <{target}>"
            if att:
                a += f" ; mrs:attestedBy <{att}>"
            t.append(f"mrs:relativeAnchor [ a mrs:RelativeAnchor ; {a} ]")
        self.out.append(" ;\n    ".join(t) + " .")
        self.out.append(f"<{owner}> mrs:eventTemporalExtent <{te}> .")
        return te

    def event(self, pid: str, label: str, *, dates: tuple[str, str] | None = None, place: str | None = None,
              anchors: list[tuple[str, str, str | None]] = (), precision: str = "year", more: tuple = ()) -> str:
        """anchors: (allen relation local name, target IRI, attesting claim IRI or None).
        more: further labels."""
        iri = self._id("event", pid)
        labels = ", ".join(lit(x) for x in (label, *more))
        parts = [f"<{iri}> a mrs:Event", f"rdfs:label {labels}", "mrs:coverageState mrs:cs_stub"]
        if place:
            parts.append(f"mrs:eventPlace <{place}>")
        self.out.append(" ;\n    ".join(parts) + " .")
        if dates or anchors:
            self.extent(iri, dates[0] if dates else None, dates[1] if dates else None, precision, anchors)
        return iri

    def participation(self, event: str, who: str, role: str = "role_participant"):
        self.out.append(f"<{event}> mrs:hasParticipation [ a mrs:Participation ; mrs:participant <{who}> ; "
                        f"mrs:participantRole mrs:{role} ] .")

    def citation(self, text: str, work: str | None = None) -> str:
        """A passage with a canonical citation (a work and a locator)."""
        self.n += 1
        iri = self._id("passage", f"fxCite{self.n}")
        part = f" ; dct:isPartOf <{work}>" if work else ""
        self.out.append(f"<{iri}> a mrs:Passage ; mrs:canonicalCitation {lit(text)}{part} .")
        return iri

    def claim(self, subject: str, predicate: str, obj: str, statuses=("proposed",), *, pid: str | None = None,
              role: str | None = None, qualifiers=(), basis: str | None = "Fixture basis.",
              cite: str | None = None, work: str | None = None, at_event: str | None = None) -> str:
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
        if cite:
            parts.append(f"prov:wasDerivedFrom <{self.citation(cite, work)}>")
        if at_event:
            parts.append(f"mrs:atEvent <{at_event}>")
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

    def geometry(self, place: str, point: tuple[float, float] | None = None, confidence: str = "certain",
                 basis: str = "textual"):
        """A geometry state on a place: a WKT point (lon, lat) or none, with its location
        confidence (certain, probable, unlocated, ...) and geometry basis."""
        if not getattr(self, "_geo_vocab", False):
            self._geo_vocab = True
            for c in ("certain", "probable", "approximate", "unlocated"):
                self.out.append(f"mrs:lc_{c} a mrs:LocationConfidence ; skos:prefLabel {lit(c)} .")
            for b in ("textual", "traditional", "inferred"):
                self.out.append(f"mrs:gb_{b} a mrs:GeometryBasis ; skos:prefLabel {lit(b)} .")
        geo = (f' ; mrs:geometry [ a <http://www.opengis.net/ont/geosparql#Geometry> ; '
               f'<http://www.opengis.net/ont/geosparql#asWKT> "POINT({point[0]} {point[1]})" ]') if point else ""
        self.out.append(f"<{place}> mrs:geometryState [ a mrs:GeometryState ; mrs:locationConfidence mrs:lc_{confidence} ; "
                        f"mrs:geometryBasis mrs:gb_{basis}{geo} ] .")

    def ttl(self) -> str:
        return "\n".join(self.out) + "\n"

    def graph(self) -> Graph:
        g = Graph()
        g.parse(data=self.ttl(), format="turtle")
        return g

    def write(self, path: Path) -> Path:
        Path(path).write_text(self.ttl(), encoding="utf-8")
        return Path(path)


def site_of(fx: Fx):
    """A site/model.py Site read from the fixture graph."""
    from model import Site
    tmp = tempfile.NamedTemporaryFile("w", suffix=".ttl", delete=False, encoding="utf-8")
    tmp.write(fx.ttl())
    tmp.close()
    try:
        return Site(tmp.name)
    finally:
        Path(tmp.name).unlink()


# --------------------------------------------------------------------------- journey specs
def events_spec(words, follow=("parts", "date_anchors"), max_links=2, kinds=("event", "story"), **named) -> dict:
    sel = {"kinds": list(kinds), "words": list(words), **named}
    if not words:
        del sel["words"]
    return {"slug": "fixture-events", "status": "draft", "approved_by": [], "title": "journey.hijrah.title",
            "lead": "journey.hijrah.lead", "door": "study",
            "select": {"type": "events", "named": sel, "follow": list(follow), "max_links": max_links},
            "order": "recorded"}


def people_spec(words=("Fixtureplace",), order="e3", lists="lists/people.json", group_by=None, **named) -> dict:
    sel = {"type": "people",
           "events": {"named": {"kinds": ["event", "story"], "words": list(words), **named}, "follow": ["parts"],
                      "max_links": 1},
           "participation": {"records": True, "claims": ["mrs:rel_participated_in", "mrs:rel_led"]},
           "also_show": ["mrs:rel_absent_from"], "set_apart": ["mrsv:q_later"]}
    if group_by:
        sel["group_by"] = group_by
    spec = {"slug": "fixture-people", "status": "draft", "approved_by": [], "title": "journey.badr.title",
            "lead": "journey.badr.lead", "door": "study", "select": sel, "order": order}
    if order == "e3":
        spec["lists"] = lists
    return spec


def stories_spec(words=("Early",)) -> dict:
    return {"slug": "fixture-stories", "status": "draft", "approved_by": [], "title": "journey.first_believers.title",
            "lead": "journey.first_believers.lead", "door": "discover",
            "select": {"type": "stories", "part": {"words": list(words)}}, "order": "story"}


# --------------------------------------------------------------------------- list files
SOURCE = "Fixture work, vol. 1, p. 2"


def list_file(folder, rashidun, ten, *, status="reviewed", sources=(SOURCE, SOURCE), approve=True,
              name="lists/people.json", sha=None) -> Path:
    """A marsad-lists file in a temporary folder. With approve, both roles approved the
    sha12 of its lists (or `sha`, to make a stale approval). Test fixtures only: no code
    ever writes an approval into learn/lists/."""
    import journeys
    lists = [{"key": "rashidun", "members": list(rashidun), "order": "succession", "source": sources[0]},
             {"key": "ten", "members": list(ten), "order": "as listed in the report", "source": sources[1]}]
    h = sha or journeys.sha12(lists)
    approved = [{"who": "maintainer", "date": "2026-11-02", "sha": h},
                {"who": "review_board", "date": "2026-11-09", "sha": h}] if approve else []
    path = Path(folder) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"format": "marsad-lists", "version": 1, "about": "Fixture lists.", "status": status,
                                "approved_by": approved, "lists": lists}, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    return path


def reviewed_list_file(folder, rashidun, ten, **kw) -> Path:
    return list_file(folder, rashidun, ten, **kw)


# --------------------------------------------------------------------------- fixture graphs
def tiers_fixture() -> tuple[Fx, dict]:
    """One battle; the Prophet; four people for the rāshidūn tier (listed in an order that
    is not A to Z), two more of the ten, and four others with different link counts."""
    fx = Fx()
    ids = {"battle": fx.event("fxBattle", "Battle of Fixtureplace"), "elsewhere": fx.event("fxElse", "Another event"),
           "prophet": fx.prophet()}
    people = {"r1": "Person Delta", "r2": "Person Alpha", "r3": "Person Charlie", "r4": "Person Bravo",
              "t5": "Person Zulu", "t6": "Person Echo",
              "o1": "Person Kilo", "o2": "Person Lima", "o3": "Person Juliet", "o4": "Person Mike"}
    for k, label in people.items():
        ids[k] = fx.person(f"fxP{k}", label)
        fx.participation(ids["battle"], ids[k])
    fx.participation(ids["battle"], ids["prophet"], "role_leader")
    extra = {"o1": 3, "o2": 1, "o3": 3, "o4": 0, "r1": 0, "t6": 5}   # more records about them
    for k, n in extra.items():
        for i in range(n):
            fx.claim(ids[k], "rel_participated_in", ids["elsewhere"], ("proposed",))
    ids["rashidun"] = [people[k] for k in ("r1", "r2", "r3", "r4")]
    ids["ten"] = ids["rashidun"] + [people["t5"], people["t6"]]
    return fx, ids


def side_fixture() -> tuple[Fx, dict]:
    """A battle at which people are recorded on a side: alongside or against the Prophet,
    both, uncited, rejected, at another event, against someone else, and a later convert."""
    fx = Fx()
    i = {"battle": fx.event("fxBattle", "Battle of Fixtureplace"), "other": fx.event("fxOther", "Raid of Elsewhere"),
         "prophet": fx.prophet()}
    cite = "Fixture work, vol. 2, p. 7"
    names = {"along": "Person Along", "against": "Person Against", "both": "Person Both", "uncited": "Person Uncited",
             "rejected": "Person Rejected", "elsewhere": "Person Elsewhere", "notprophet": "Person Notprophet",
             "convert": "Person Convert", "object": "Person Object", "opposer": "Person Opposer"}
    for k, label in names.items():
        i[k] = fx.person(f"fxS{k}", label)
        fx.participation(i["battle"], i[k])
    fx.participation(i["battle"], i["prophet"], "role_leader")
    B, P = i["battle"], i["prophet"]
    fx.claim(i["along"], "rel_fought_alongside", P, cite=cite, at_event=B)
    fx.claim(i["against"], "rel_fought_against", P, cite=cite, at_event=B)
    fx.claim(i["both"], "rel_fought_against", P, cite=cite, at_event=B)
    fx.claim(i["both"], "rel_fought_alongside", P, cite=cite, at_event=B)
    fx.claim(i["uncited"], "rel_fought_against", P, at_event=B)
    fx.claim(i["rejected"], "rel_fought_against", P, ("proposed", "rejected"), cite=cite, at_event=B)
    fx.claim(i["elsewhere"], "rel_fought_against", P, cite=cite, at_event=i["other"])
    fx.claim(i["notprophet"], "rel_fought_against", i["along"], cite=cite, at_event=B)
    fx.claim(i["convert"], "rel_fought_against", P, cite=cite, at_event=B)
    fx.claim(i["convert"], "rel_participated_in", i["other"], qualifiers=["q_later"], cite=cite)
    fx.claim(P, "rel_fought_against", i["object"], cite=cite, at_event=B)   # the person is only the object
    fx.claim(i["opposer"], "rel_opposed", P, cite=cite)                     # outside the anchors, no side
    fx.claim(i["opposer"], "rel_fought_against", P, cite=cite, at_event=i["other"])
    return fx, i


def acceptance_fixture() -> tuple[Fx, dict]:
    """Acceptance-of-Islam events, dated and undated, with cited and uncited records."""
    fx = Fx()
    i = {"ev_a": fx.event("fxAccA", "Person A's acceptance of Islam", dates=("0610-01-01", "0610-12-31")),
         "ev_b": fx.event("fxAccB", "Person B's acceptance of Islam", dates=("0610-01-01", "0610-12-31")),
         "ev_c": fx.event("fxAccC", "Person C's acceptance of Islam", dates=("0615-01-01", "0615-12-31")),
         "ev_list": fx.event("fxAccList", "The early acceptance of Islam (fixture list)"),
         "ev_other": fx.event("fxAccOther", "Another acceptance of Islam (fixture)"),
         "ev_no": fx.event("fxAccNo", "Islam of acceptance, words out of order")}
    for k in "ABCDEFGHJ":
        i[k] = fx.person(f"fxAcc{k}", f"Person {k}")
    cite = "Fixture work, vol. 1, p. 9"
    fx.claim(i["A"], "rel_participated_in", i["ev_a"], cite=cite)
    fx.claim(i["B"], "rel_participated_in", i["ev_b"], cite=cite)
    fx.claim(i["C"], "rel_participated_in", i["ev_c"], cite=cite)
    fx.claim(i["C"], "rel_participated_in", i["ev_list"], cite=cite)          # dated wins over undated
    fx.claim(i["D"], "rel_participated_in", i["ev_list"], cite=cite)
    fx.claim(i["E"], "rel_participated_in", i["ev_other"], cite=cite)
    fx.claim(i["F"], "rel_participated_in", i["ev_a"])                         # no citation
    fx.participation(i["ev_a"], i["G"])                                        # a participation has no citation
    fx.claim(i["J"], "rel_participated_in", i["ev_no"], cite=cite)             # not the phrase
    return fx, i


def facade_graph() -> Fx:
    """Made-up events, people and stories worded like the shipped journeys (Hijra, Badr,
    a Makkan part), for engine tests and the facade lock: events with parts and date
    anchors, a battle with participations, side claims and an expedition left out by
    not_words, and a story document whose first part is Makkan."""
    fx = Fx()
    place = fx.place("fxFacPlace", "Place A")
    whole = fx.event("fxFacHijra", "The Hijra of fixture town", dates=("0622-01-01", "0622-12-31"), place=place)
    leave = fx.event("fxFacLeave", "Leaving fixture town")
    arrive = fx.event("fxFacArrive", "Arriving at fixture city", dates=("0622-01-01", "0622-12-31"))
    att = f"{ID}assertion/fxFacAnchor"
    rest = fx.event("fxFacRest", "Resting in a fixture cave", anchors=[("after", leave, att), ("before", arrive, att)])
    fx.claim(leave, "rel_part_of", whole, pid="fxFacPartLeave", cite="Fixture work, vol. 1, p. 3")
    fx.claim(rest, "rel_part_of", whole, pid="fxFacPartRest")
    prophet = fx.prophet("fxFacProphet")
    fx.claim(prophet, "rel_present_at", place, pid="fxFacAnchor")
    battle = fx.event("fxFacBadr", "Battle of Badr (fixture)", dates=("0624-01-01", "0624-12-31"))
    expedition = fx.event("fxFacBadrExp", "The expedition of Badr (fixture)")
    cite = "Fixture work, vol. 2, p. 5"
    fx.participation(battle, prophet, "role_leader")
    for k, label in (("A", "Person A"), ("B", "Person B"), ("C", "Person C"), ("D", "Person D")):
        who = fx.person(f"fxFac{k}", label)
        fx.participation(battle, who)
        fx.claim(who, "rel_fought_alongside" if k in "AB" else "rel_fought_against", prophet, cite=cite,
                 at_event=battle)
    late = fx.person("fxFacE", "Person E")
    fx.claim(late, "rel_participated_in", battle, qualifiers=["q_later"], cite=cite)
    gone = fx.person("fxFacF", "Person F")
    fx.participation(expedition, gone)
    work = fx.story_doc("fxFacWork", "50 Stories (fixture)")
    p1 = fx.story_part("fxFacPart1", work, "Part 1: The Makkan fixture days", 1)
    p2 = fx.story_part("fxFacPart2", work, "Part 2: Later fixture days", 2)
    s1 = fx.story("fxFacStory1", "The first fixture story", 1, p1)
    s2 = fx.story("fxFacStory2", "The second fixture story", 2, p1)
    fx.story("fxFacStory3", "The third fixture story", 3, p2)
    fx.claim(prophet, "rel_participated_in", s1, role="named in the story", cite="50 Stories (fixture), Part 1, story 1",
             work=work)
    fx.claim(late, "rel_participated_in", s2, cite="50 Stories (fixture), Part 1, story 2", work=work)
    return fx


GLOSS = "AI gloss (proposed; machine-written, not reviewed, not a translation): a fixture gloss sentence."
NOTE = "a fixture note from the document itself."


def status_fixture() -> tuple[Fx, dict]:
    """A battle with claims of every status, cited and uncited, one with two statuses,
    one with an AI gloss and one with a plain comment, a participation (no status), a
    place link, a dated event and a 50 Stories record (an AI-generated document)."""
    fx = Fx()
    i = {"place": fx.place("fxStPlace", "Place of Fixtureplace"), "prophet": fx.prophet("fxStProphet")}
    i["battle"] = fx.event("fxStBattle", "Battle of Fixtureplace", dates=("0624-03-01", "0624-03-31"),
                           place=i["place"], precision="month")
    cite = "Fixture work (fixture ed., Fixturetown 2000; draft), vol. 3, p. 11; Fixture lines 1–2"
    fx.participation(i["battle"], i["prophet"], "role_leader")
    for st in ("accepted", "under_review", "proposed", "rejected", "superseded"):
        for cited in (True, False):
            k = f"{st}_{'cited' if cited else 'uncited'}"
            i[k] = fx.person(f"fxSt{st.replace('_', '')}{'C' if cited else 'U'}",
                              f"Person {st.replace('_', ' ')} {'cited' if cited else 'uncited'}")
            i[f"c_{k}"] = fx.claim(i[k], "rel_participated_in", i["battle"], (st,), cite=cite if cited else None,
                                   pid=f"fxStClaim{st.replace('_', '')}{'C' if cited else 'U'}")
    i["none"] = fx.person("fxStNone", "Person nostatus")
    i["c_none"] = fx.claim(i["none"], "rel_participated_in", i["battle"], (), cite=cite, pid="fxStClaimNone")
    i["two"] = fx.person("fxStTwo", "Person twostatus")
    i["c_two"] = fx.claim(i["two"], "rel_participated_in", i["battle"], ("proposed", "rejected"), cite=cite,
                          pid="fxStClaimTwo")
    i["glossed"] = fx.person("fxStGlossed", "Person glossed")
    i["c_glossed"] = fx.claim(i["glossed"], "rel_participated_in", i["battle"], cite=cite, role=GLOSS, pid="fxStClaimGloss")
    i["noted"] = fx.person("fxStNoted", "Person noted")
    i["c_noted"] = fx.claim(i["noted"], "rel_participated_in", i["battle"], cite=cite, role=NOTE, pid="fxStClaimNote")
    i["plain"] = fx.person("fxStPlain", "Person plain")
    fx.participation(i["battle"], i["plain"])
    work = fx.story_doc("fxStWork", "50 Stories (fixture)")
    i["c_ai"] = fx.claim(i["plain"], "rel_led", i["battle"], cite="50 Stories (fixture, rev 1), Part 2, story 4",
                         work=work, pid="fxStClaimAi")
    return fx, i


def role_pair(role: str = "role_participant") -> Fx:
    """A battle with three participations; the second person's role is `role`."""
    fx = Fx()
    battle = fx.event("fxRoBattle", "Battle of Fixtureplace")
    fx.participation(battle, fx.prophet("fxRoProphet"), "role_leader")
    fx.participation(battle, fx.person("fxRoA", "Person A"))
    fx.participation(battle, fx.person("fxRoB", "Person B"), role)
    fx.claim(fx.person("fxRoC", "Person C"), "rel_participated_in", battle, cite="Fixture work, vol. 1, p. 4")
    return fx


def big_people_graph(n: int = 600, note_words: int = 40) -> tuple[Fx, dict]:
    """A battle with n people, each with a cited claim carrying a long note, for the
    part-budget tests."""
    fx = Fx()
    battle = fx.event("fxBigBattle", "Battle of Fixtureplace")
    fx.participation(battle, fx.prophet("fxBigProphet"), "role_leader")
    note = " ".join(["fixture"] * note_words)
    people = []
    for k in range(n):
        who = fx.person(f"fxBig{k:04d}", f"Person {k:04d}")
        fx.participation(battle, who)
        fx.claim(who, "rel_participated_in", battle, cite=f"Fixture work, vol. 1, p. {k + 1}", role=note)
        people.append(who)
    return fx, {"battle": battle, "people": people}
