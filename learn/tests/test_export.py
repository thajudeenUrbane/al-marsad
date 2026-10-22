"""The marsad-journey v1 export (learn/journey_export.py, design §7 and §9-§11).

Fixture graphs (made up, see fixtures.py) carry the exact numbers; the real-graph tests
state invariants only. Nothing here names a real entity ID.
Run:  .venv/bin/python -m unittest discover -s learn/tests -v
"""
import contextlib
import copy
import filecmp
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

LEARN = Path(__file__).resolve().parents[1]
ROOT = LEARN.parent
SITE = ROOT / "site"
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(LEARN))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import journey_export as X  # noqa: E402
import journeys as J  # noqa: E402
from fixtures import (GLOSS, NOTE, SOFTWARE_AGENT, Fx, big_people_graph, events_spec, facade_graph,  # noqa: E402
                      list_file, people_spec, role_pair, side_fixture, site_of, status_fixture, stories_spec)
from model import Site  # noqa: E402

GRAPH = ROOT / "build" / "graph.ttl"
EN = json.loads((LEARN / "i18n" / "en.json").read_text(encoding="utf-8"))
SITE_EN = json.loads((SITE / "i18n" / "en.json").read_text(encoding="utf-8"))
AR = json.loads((LEARN / "i18n" / "ar.json").read_text(encoding="utf-8"))
ARABIC_INDIC_DIGIT = re.compile("[٠-٩۰-۹]")
CLI = LEARN / "journey_export.py"
SMALL_BUDGET = "30000"     # the largest single stop on the page graph is about 24,000 bytes
REF = re.compile(r"^(person|group|place|event|story|node)/[^/]+$")
TERM = re.compile(r"^(pk|q|role|voice|lc|gb):.+$")


def pid(iri: str) -> str:
    return iri.rsplit("/", 1)[-1]


def people(site, group_by=None, **over):
    spec = people_spec(words=("Fixtureplace",), order="prophet_first_then_name", group_by=group_by)
    spec.update(over)
    return J.build(site, J.validate(spec))


def export(site, journeys, **kw) -> dict:
    return X.resolve_all(site, None, journeys=journeys, bank=kw.pop("bank", []), **kw)


def unpack(res: dict, slug: str):
    files = res["files"]
    head = json.loads(files[f"journeys/{slug}/journey.json"])
    parts = [json.loads(files[f"journeys/{slug}/{p}"]) for p in head["parts"]]
    research = [json.loads(files[f"journeys/{slug}/{p}"]) for p in head["research"]]
    return head, parts, research


def all_claims(parts) -> dict:
    out = {}
    for p in parts:
        out.update(p["claims"])
    return out


def all_steps(parts) -> list:
    return [s for p in parts for s in p["steps"]]


def refs_of_part(part) -> tuple[set, set, set, set]:
    """Every claim id, entity ref, term ref and passage ref a part's contents name."""
    claims, ents, terms, passages = set(), set(), set(), set()
    for st in part["steps"]:
        ents.add(st["ref"])
        for r in st["reasons"] + st["links"]:
            claims |= set(r["claims"])
            if r.get("other"):
                ents.add(r["other"])
        if st.get("order", {}).get("ref"):
            ents.add(st["order"]["ref"])
        claims |= set(st["records"]) | set(st["contrary"]) | set((st.get("claims") or {}).get("ids") or [])
        for s in st["side"]:
            claims |= set(s["claims"])
            ents |= {s["at"], s["with"]}
        for item in st["narration"]:
            claims |= set(item["c"])
            ents |= {item[k] for k in ("subject", "object", "event") if item.get(k)}
            terms |= {item[k] for k in ("role", "relation") if item.get(k)}
            terms |= {m["marker"] for m in item.get("markers") or []}
        for pr in st["prompts"]:
            claims |= set(pr["answer"].get("claims") or [])
            ents |= set(pr["slots"].values())
        for nx in st["next"]:
            ents.add(nx["ref"])
        if st["hints"]["focus"]:
            ents.add(st["hints"]["focus"])
        for acc in (st.get("e3") or {}).get("accepted_islam") or []:
            ents.add(acc["event"])
            claims |= set(acc["claims"])
    for c in part["claims"].values():
        ents |= {c["s"]} | ({c["o"]} if "o" in c else set()) | ({c["at_event"]} if "at_event" in c else set())
        terms.add(f"pk:{c['pk']}")
        terms |= {f"q:{q}" for q in c.get("qualifiers") or []}
        if c.get("role"):
            terms.add(f"role:{c['role']}")
        if c.get("voice"):
            terms.add(f"voice:{c['voice']}")
        if c.get("passage"):
            passages.add(c["passage"])
    for p in part["passages"].values():
        if p.get("story"):
            ents.add(p["story"])
    for e in part["entities"].values():
        ents |= set(e.get("places") or [])
        geo = e.get("geo") or {}
        terms |= {f"lc:{geo['confidence']}"} if geo.get("confidence") else set()
        terms |= {f"gb:{geo['basis']}"} if geo.get("basis") else set()
    return claims, ents, terms, passages


def walk_strings(obj, skip=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k not in skip:
                yield from walk_strings(v, skip)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v, skip)
    elif isinstance(obj, str):
        yield obj


I18N_KEY = re.compile(r"^(learn|journey|status|coverage|type|claim|common)(\.[a-z0-9_]+)+$")


def step_templates(tc: unittest.TestCase, files: dict) -> tuple[set, set]:
    """Every reason kind and order note the steps carry, and the set-apart heading and
    lead, have their sentence named in index.json and held in strings.json, so a consumer
    reading only the files can render them (design §10). Returns the kinds and notes seen."""
    index, strings = files["index.json"], files["strings.json"]
    tc.assertEqual(index["reasons"], {k: f"learn.why.{k}" for k in X.REASON_KEYS})
    tc.assertEqual(index["order_notes"], {n: f"learn.order_note.{n}" for n in ("part", "recorded", "unrecorded")})
    texts = [index["texts"][k] for k in ("apart_heading", "apart_lead", "why_heading", "links_heading",
                                         "plain_link", "quote", "step_ref")]
    for key in list(index["reasons"].values()) + list(index["order_notes"].values()) + texts:
        tc.assertEqual(strings["en"].get(key), EN[key], key)
    kinds, notes = set(), set()
    for path, doc in files.items():
        if "/part-" in path:
            for st in doc["steps"]:
                kinds |= {r["kind"] for r in st["reasons"] + st["links"]}
                if "order" in st:
                    notes.add(st["order"]["note"])
    tc.assertEqual(kinds - set(index["reasons"]), set())   # a part reason's sentence is learn.why.part (stage C)
    tc.assertEqual(notes - set(index["order_notes"]), set())
    return kinds, notes


def keys_named(obj) -> set:
    """Every i18n key an exported document names (any string value shaped like one)."""
    return {s for s in walk_strings(obj) if I18N_KEY.match(s)}


# --------------------------------------------------------------------------- fixtures
class StatusesAndDiscover(unittest.TestCase):
    """Every status, cited and uncited (fixtures.status_fixture)."""

    @classmethod
    def setUpClass(cls):
        fx, cls.i = status_fixture()
        cls.site = site_of(fx)
        cls.j = people(cls.site)
        cls.res = export(cls.site, [cls.j])
        cls.head, cls.parts, cls.research = unpack(cls.res, cls.j.slug)
        cls.claims = all_claims(cls.parts)
        cls.ids = {k: f"assertion/{pid(v)}" for k, v in cls.i.items() if k.startswith("c_")}

    def claim(self, key):
        return self.claims[self.ids[key]]

    def test_status_is_never_folded(self):
        for st in ("accepted", "under_review", "proposed", "rejected", "superseded"):
            for cited in ("cited", "uncited"):
                with self.subTest(st=st, cited=cited):
                    self.assertEqual(self.claim(f"c_{st}_{cited}")["status"], st)
                    self.assertNotIn("statuses", self.claim(f"c_{st}_{cited}"))
        self.assertIsNone(self.claim("c_none")["status"])
        self.assertEqual(self.claim("c_two")["statuses"], ["proposed", "rejected"])
        self.assertEqual(self.claim("c_two")["status"], "rejected")       # the most cautious, the list beside it
        part = next(c for c in self.claims.values() if c["kind"] == "participation")
        self.assertIsNone(part["status"])

    def test_discover_flag(self):
        """True only with a citation and a status other than rejected or superseded."""
        for st in ("accepted", "under_review", "proposed"):
            self.assertTrue(self.claim(f"c_{st}_cited")["discover"], st)
            self.assertFalse(self.claim(f"c_{st}_uncited")["discover"], st)
        for st in ("rejected", "superseded"):
            self.assertFalse(self.claim(f"c_{st}_cited")["discover"], st)
            self.assertFalse(self.claim(f"c_{st}_uncited")["discover"], st)
        self.assertTrue(self.claim("c_none")["discover"])
        self.assertFalse(self.claim("c_two")["discover"])
        for c in self.claims.values():
            if c["kind"] != "assertion":
                self.assertFalse(c["discover"])
            if c.get("discover"):
                self.assertTrue(c.get("passage") and self.parts[0]["passages"][c["passage"]]["cite"])

    def test_no_rejected_or_superseded_claim_is_flagged_discover(self):
        for c in self.claims.values():
            if {c["status"], *c.get("statuses", [])} & {"rejected", "superseded"}:
                self.assertFalse(c["discover"], c)

    def test_discover_items_have_an_eligible_claim(self):
        for st in all_steps(self.parts):
            for item in st["narration"]:
                eligible = any(self.claims[c]["discover"] for c in item["c"])
                self.assertEqual(item["d"], "discover" if eligible else "study", item)
            for pr in st["prompts"]:
                if pr["d"] == "discover":
                    claims = pr["answer"].get("claims")
                    self.assertTrue(claims is None and pr["answer"].get("href")
                                    or any(self.claims[c]["discover"] for c in claims), pr)

    def test_no_part_or_head_file_contains_ai_gloss_text_and_no_assertion_has_a_role(self):
        gloss_body = GLOSS.split("): ", 1)[1]
        files = self.res["files"]
        for path, raw in files.items():
            text = raw.decode("utf-8")
            if "/research-" in path:
                continue
            with self.subTest(path):
                self.assertNotIn(gloss_body, text)
                self.assertNotIn(X.GLOSS_PREFIX, text)
        research = {k: v for r in self.research for k, v in r["glosses"].items()}
        self.assertEqual(research, {self.ids["c_glossed"]: gloss_body})
        for c in self.claims.values():
            if c["kind"] == "assertion":
                self.assertNotIn("role", c)
        self.assertEqual(self.claim("c_noted")["note"], {"text": NOTE, "ai_document": False})
        self.assertNotIn("note", self.claim("c_glossed"))

    def test_notes_basis_and_agents_are_study_level_fields(self):
        c = self.claim("c_accepted_cited")
        self.assertEqual(c["basis"], "Fixture basis.")
        policy = X.DEPTH_POLICY
        for field in ("basis", "recorded_by", "notes", "gloss", "status", "claim_ids"):
            self.assertIs(policy["discover"][field], False, field)
        for field in ("basis", "recorded_by", "notes", "status"):
            self.assertIs(policy["study"][field], True, field)
        self.assertIs(policy["study"]["gloss"], False)
        self.assertIs(policy["research"]["gloss"], True)
        self.assertEqual(policy["discover"]["source"], "citation_short")

    def test_narration_never_uses_assertion_comments(self):
        for st in all_steps(self.parts):
            text = json.dumps(st["narration"], ensure_ascii=False)
            self.assertNotIn(NOTE, text)
            self.assertNotIn(GLOSS.split("): ", 1)[1], text)
            self.assertNotIn(X.GLOSS_PREFIX, text)

    def test_ai_document_and_software_flags(self):
        ai = self.claim("c_ai")
        self.assertTrue(ai["ai_document"])
        self.assertTrue(self.parts[0]["passages"][ai["passage"]]["ai_document"])
        self.assertEqual(self.head["ai_documents"], ["50 Stories (fixture)"])
        self.assertEqual(self.head["ai_note"], {"discover": "learn.ai_source_note", "study": "learn.ai_note"})
        self.assertNotIn("ai_document", self.claim("c_accepted_cited"))
        self.assertNotIn("software", self.claim("c_accepted_cited"))     # recorded by no agent
        self.assertNotIn("recorded_by", self.claim("c_accepted_cited"))
        sw = self.claim("c_software")                                     # recorded by a software agent
        self.assertIs(sw["software"], True)
        self.assertEqual(sw["recorded_by"], [{"label": SOFTWARE_AGENT, "software": True}])
        self.assertNotIn("ai_document", sw)                               # its passage is no AI document
        self.assertIs(sw["discover"], False)                              # uncited

    def test_source_line_falls_back_to_who_recorded_it(self):
        """An uncited claim with no basis text: Study and Research name the agent that
        recorded it (claim.recorded_by); Discover shows nothing."""
        t = X.translators()["en"]
        passages = self.parts[0]["passages"]
        sw = self.claim("c_software")
        self.assertNotIn("basis", sw)
        self.assertNotIn("passage", sw)
        self.assertIsNone(X.source_line(sw, "discover", passages, t))
        for depth in ("study", "research"):
            self.assertEqual(X.source_line(sw, depth, passages, t),
                             SITE_EN["claim.recorded_by"].format(value=SOFTWARE_AGENT), depth)

    def test_accepted_share_counts_only_accepted(self):
        share = self.head["accepted_share"]
        self.assertEqual(share["accepted"], 2)                             # cited and uncited, sole status
        self.assertEqual(share["of"], len([c for c in self.claims.values() if c["kind"] == "assertion"]))
        self.assertEqual(share["no_status"], len([c for c in self.claims.values() if c["status"] is None]))

    def test_short_source_form_drops_remarks(self):
        p = self.parts[0]["passages"][self.claim("c_accepted_cited")["passage"]]
        self.assertEqual(p["short"], "Fixture work, vol. 3, p. 11")
        self.assertIn("draft", p["cite"])
        self.assertEqual(J.review_words(p["short"]), [])

    def test_source_line_at_each_depth(self):
        t = X.translators()["en"]
        passages = self.parts[0]["passages"]
        cited = self.claim("c_accepted_cited")
        self.assertEqual(X.source_line(cited, "discover", passages, t), "Fixture work, vol. 3, p. 11")
        self.assertEqual(X.source_line(cited, "study", passages, t), passages[cited["passage"]]["cite"])
        uncited = self.claim("c_accepted_uncited")
        self.assertIsNone(X.source_line(uncited, "discover", passages, t))
        self.assertEqual(X.source_line(uncited, "study", passages, t), "Fixture basis.")
        self.assertIsNone(X.source_line(self.claim("c_rejected_cited"), "discover", passages, t))
        ai = self.claim("c_ai")
        for depth in X.DEPTHS:
            line = X.source_line(ai, depth, passages, t)
            self.assertTrue(line.endswith(" (a document generated with AI)"), (depth, line))
        self.assertEqual(X.source_line(ai, "discover", passages, t),
                         EN["learn.source.ai_document"].format(source="50 Stories, Part 2, story 4"))
        part = next(c for c in self.claims.values() if c["kind"] == "participation")
        self.assertIsNone(X.source_line(part, "discover", passages, t))
        self.assertEqual(X.source_line(part, "study", passages, t), SITE_EN["common.not_recorded"])
        agent = dict(uncited, basis=None, recorded_by=[{"label": "Fixture agent", "software": True}])
        self.assertEqual(X.source_line(agent, "research", passages, t),
                         SITE_EN["claim.recorded_by"].format(value="Fixture agent"))

    def test_public_mode_accepted_fails_closed(self):
        old = os.environ.get("MARSAD_PUBLIC_MODE")
        os.environ["MARSAD_PUBLIC_MODE"] = "accepted"
        try:
            with self.assertRaises(J.RuleError):
                export(self.site, [self.j])
            os.environ["MARSAD_PUBLIC_MODE"] = "everything"
            with self.assertRaises(J.RuleError):
                X.public_mode()
        finally:
            if old is None:
                os.environ.pop("MARSAD_PUBLIC_MODE", None)
            else:
                os.environ["MARSAD_PUBLIC_MODE"] = old
        self.assertEqual(X.public_mode(), "all")

    def test_strings_must_be_the_en_and_ar_tables(self):
        """resolve() takes {"en", "ar"} (journeys.load_i18n()). The flat en table the Atlas
        reads would bind a wrong rule_sha and give null titles, so it raises TypeError."""
        i18n = J.load_i18n()
        default = X.resolve(self.site, self.j, bank=[])
        given = X.resolve(self.site, self.j, i18n, bank=[])
        self.assertEqual(J.canonical(given), J.canonical(default))
        self.assertEqual(default["rule_sha"], J.rule_sha(self.j.spec))
        self.assertEqual(default["title"]["en"], EN[self.j.spec["title"]])
        flat = i18n["en"]
        for bad in (flat, {"en": flat}, {"ar": {}}, {"en": flat, "ar": {}, "fr": {}}, {"en": flat, "ar": None}, []):
            with self.subTest(bad=sorted(bad)[:2] if isinstance(bad, dict) else bad):
                with self.assertRaises(TypeError):
                    X.resolve(self.site, self.j, bad, bank=[])
                with self.assertRaises(TypeError):
                    X.resolve_all(self.site, None, journeys=[self.j], bank=[], strings=bad)
                with self.assertRaises(TypeError):
                    J.rule_sha(self.j.spec, i18n=bad)
        # the facade keeps the flat en table, as the Atlas reads it
        self.assertEqual(X.atlas_projection(self.j, flat)["title"], flat[self.j.spec["title"]])


class Narration(unittest.TestCase):
    def test_narration_is_attributive_merges_identical_sentences_and_keeps_every_source(self):
        fx = Fx()
        battle = fx.event("fxNaBattle", "Battle of Fixtureplace")
        a = fx.person("fxNaA", "Person A")
        fx.participation(battle, a)
        c1 = fx.claim(a, "rel_participated_in", battle, cite="Fixture work, vol. 1, p. 1", pid="fxNaOne")
        c2 = fx.claim(a, "rel_participated_in", battle, cite="Fixture work, vol. 1, p. 2", pid="fxNaTwo")
        c3 = fx.claim(a, "rel_led", battle, pid="fxNaLed")
        site = site_of(fx)
        res = export(site, [people(site)])
        _, parts, _ = unpack(res, "fixture-people")
        st = next(s for s in all_steps(parts) if s["key"] == pid(a))
        took = [it for it in st["narration"] if it["t"] == "learn.narr.took_part"]
        self.assertEqual(len(took), 1)
        self.assertEqual(took[0]["c"], sorted([f"assertion/{pid(c1)}", f"assertion/{pid(c2)}"]))
        self.assertEqual(took[0]["d"], "discover")
        led = next(it for it in st["narration"] if it["t"] == "learn.narr.rel_led")
        self.assertEqual((led["c"], led["d"]), ([f"assertion/{pid(c3)}"], "study"))
        role = next(it for it in st["narration"] if it["t"] == "learn.narr.took_part_role")
        self.assertEqual(role["role"], "role:role_participant")
        # NARRATION_ORDER: led before took_part (the participation) before participated_in
        order = [it["t"] for it in st["narration"]]
        self.assertEqual(order, ["learn.narr.rel_led", "learn.narr.took_part_role", "learn.narr.took_part"])
        for key in X.NARRATION_TEMPLATES.values():
            text = EN[key]
            self.assertTrue(text.startswith(("The record says", "The record places", "The record counts")), key)
        for key in (X.NARR_DATED, X.NARR_STORY, X.NARR_DEFAULT, X.NARR_DEFAULT_TEXT, X.NARR_ROLE, *X.NARR_SIDE.values()):
            self.assertEqual(J.review_words(EN[key]), [], key)

    def test_story_objects_use_the_story_template(self):
        site = site_of(facade_graph())
        j = J.build(site, J.validate(stories_spec(["Makkan"])))
        res = export(site, [j])
        _, parts, _ = unpack(res, j.slug)
        items = [it for st in all_steps(parts) for it in st["narration"]]
        self.assertTrue(items)
        self.assertTrue(all(it["t"] == "learn.narr.story" for it in items))
        claims = all_claims(parts)
        for it in items:
            self.assertTrue(it["object"].startswith("story/"))
            self.assertTrue(all(claims[c]["ai_document"] for c in it["c"]))

    def test_side_and_set_apart_markers(self):
        fx, i = side_fixture()
        site = site_of(fx)
        j = people(site, group_by="side")
        res = export(site, [j])
        head, parts, _ = unpack(res, j.slug)
        steps = {s["key"]: s for s in all_steps(parts)}
        against = steps[pid(i["against"])]
        side = [it for it in against["narration"] if it["t"] == "learn.narr.rel_fought_against"]
        self.assertEqual(len(side), 1)
        self.assertEqual((side[0]["object"], side[0]["event"]), (f"person/{pid(i['prophet'])}", f"event/{pid(i['battle'])}"))
        self.assertEqual(against["side"], [{"pk": "rel_fought_against", "at": f"event/{pid(i['battle'])}",
                                            "with": f"person/{pid(i['prophet'])}", "claims": side[0]["c"]}])
        self.assertEqual([g["key"] for g in head["groups"]], ["main", "against"])
        self.assertEqual(head["groups"][1]["t"], "learn.group.against")
        self.assertTrue(steps[pid(i["both"])].get("side_conflict"))
        self.assertEqual(steps[pid(i["against"])]["group"], "against")
        self.assertTrue(any(r["t"] == "learn.rule.group_side" and r["d"] == "discover" for r in head["rule_text"]))

    def test_prophet_step_side_is_subject_side_only(self):
        fx, i = side_fixture()
        site = site_of(fx)
        res = export(site, [people(site, group_by="side")])
        _, parts, _ = unpack(res, "fixture-people")
        prophet = next(s for s in all_steps(parts) if s["key"] == pid(i["prophet"]))
        self.assertEqual(prophet["side"], [])
        self.assertEqual(prophet["hints"], {"views": ["sky"], "focus": None, "light": True, "chosen_by": "rule"})
        for s in all_steps(parts):
            claims = all_claims(parts)
            for side in s["side"]:
                for c in side["claims"]:
                    self.assertEqual(claims[c]["s"], s["ref"])


class Layers(unittest.TestCase):
    """Prompts, checkpoint, next directions, view hints and place locations."""

    def test_prompts_are_ungraded_and_link_to_evidence(self):
        fx, i = status_fixture()
        site = site_of(fx)
        ev = J.build(site, J.validate(events_spec(["Fixtureplace"], follow=(), max_links=0, kinds=("event",))))
        res = export(site, [ev, people(site)])
        for slug in ("fixture-events", "fixture-people"):
            _, parts, _ = unpack(res, slug)
            for st in all_steps(parts):
                for pr in st["prompts"]:
                    self.assertIs(pr["graded"], False)
                    self.assertIn(pr["t"], X.PROMPTS.values())
                    self.assertTrue(pr["id"].startswith(f"{slug}:{st['key']}:"))
                    if "href" in pr["answer"]:
                        self.assertTrue(pr["answer"]["href"].endswith("/#evidence"))
                    else:
                        self.assertTrue(pr["answer"]["claims"])
        _, parts, _ = unpack(res, "fixture-events")
        battle = all_steps(parts)[0]
        names = [p["id"].rsplit(":", 1)[1] for p in battle["prompts"]]
        self.assertEqual(names, ["event_who", "event_where"])         # no rel_dated claim, so no "when"
        self.assertEqual(EN["learn.prompt.note"],
                         "These questions are not marked. Open one to see what the record holds, with its sources.")

    def test_checkpoint_items_come_only_from_accepted_claims(self):
        fx = Fx()
        e1, e2 = fx.event("fxCkA", "Battle of Fixtureplace"), fx.event("fxCkB", "Raid of Fixtureplace")
        a, b, c = fx.person("fxCkPa", "Person A"), fx.person("fxCkPb", "Person B"), fx.person("fxCkPc", "Person C")
        for w in (a, b):
            for e in (e1, e2):
                fx.claim(w, "rel_participated_in", e, ("accepted",), cite="Fixture work, vol. 1, p. 1")
        fx.claim(c, "rel_participated_in", e1, ("proposed",), cite="Fixture work, vol. 1, p. 2")
        fx.claim(c, "rel_participated_in", e2, ("proposed",), cite="Fixture work, vol. 1, p. 3")
        site = site_of(fx)
        import practice
        bank = practice.bank(site.g)
        j = people(site)
        res = export(site, [j], bank=bank)
        head, _, _ = unpack(res, j.slug)
        self.assertEqual(head["checkpoint"]["graded_from"], "accepted")
        self.assertEqual(head["checkpoint"]["feedback"], {"miss": "learn.check.not_both", "see": "learn.check.see_record"})
        self.assertEqual(sorted(head["checkpoint"]["items"]), sorted(q["id"] for q in bank))
        used = practice.claims_used(bank)
        self.assertTrue(used)
        for q in bank:
            for ans in q["answers"]:
                self.assertNotEqual(ans["entity"], c)
        self.assertTrue(all(J.claim_statuses(site, cl) == {"accepted"} for cs in site.claims.values() for cl in cs
                            if cl.node in used))
        empty = export(site, [j], bank=[])
        self.assertEqual(unpack(empty, j.slug)[0]["checkpoint"]["items"], [])

    def test_feedback_wording_is_the_binding_sentence_and_never_says_wrong(self):
        self.assertEqual(EN["learn.check.not_both"],
                         "The record does not place them at both, as far as reviewed claims go.")
        for k, v in EN.items():
            if k.startswith(("learn.check.", "learn.practice.", "learn.prompt.")):
                self.assertNotIn("wrong", v.lower(), k)
                self.assertNotIn("not there", v.lower(), k)

    def test_next_candidates_come_from_fixed_rules(self):
        fx, i = side_fixture()
        site = site_of(fx)
        j1 = people(site, group_by="side")
        spec2 = people_spec(words=("Fixtureplace",), order="name")
        spec2["slug"] = "fixture-people-two"
        j2 = J.build(site, J.validate(spec2))
        res = export(site, [j1, j2])
        _, parts, _ = unpack(res, j1.slug)
        for st in all_steps(parts):
            kinds = [n["t"] for n in st["next"]]
            self.assertEqual(kinds, ["learn.next.page", "learn.next.study", "learn.next.also_in"], st["key"])
            page, study, also = st["next"]
            self.assertEqual(page["href"], f"{st['ref']}/#evidence")
            self.assertEqual(study["only"], "discover")
            self.assertEqual(study["href"], f"learn/{j1.slug}/#s-{st['key']}")
            self.assertEqual(also["journey"], "fixture-people-two")
            self.assertEqual(also["href"], f"learn/fixture-people-two/#s-{st['key']}")
            self.assertEqual(set(also["urls"]), set(X.DEPTHS))
        index = json.loads(res["files"]["index.json"])
        some = pid(i["along"])
        self.assertEqual([h[0] for h in index["entities"][some]], [j1.slug, "fixture-people-two"])

    def test_view_hints_use_the_closed_vocabulary_map_needs_a_point_and_never_focus_the_prophet(self):
        fx = Fx()
        located, many, nowhere = fx.place("fxHiA", "Place A"), fx.place("fxHiB", "Place B"), fx.place("fxHiC", "Place C")
        fx.geometry(located, (39.61, 24.5))
        fx.geometry(many, (39.0, 21.0))
        fx.geometry(many, (40.0, 22.0), "probable")
        fx.geometry(nowhere, None, "unlocated")
        events = {"point": fx.event("fxHiE1", "Rihla at a point", dates=("0622-01-01", "0622-12-31"), place=located),
                  "many": fx.event("fxHiE2", "Rihla at many points", place=many),
                  "nowhere": fx.event("fxHiE3", "Rihla nowhere", place=nowhere),
                  "plain": fx.event("fxHiE4", "Rihla plain")}
        site = site_of(fx)
        j = J.build(site, J.validate(events_spec(["Rihla"], follow=(), max_links=0, kinds=("event",))))
        res = export(site, [j])
        _, parts, _ = unpack(res, j.slug)
        hints = {s["key"]: s["hints"] for s in all_steps(parts)}
        self.assertEqual(hints[pid(events["point"])]["views"], ["time", "map"])
        self.assertEqual(hints[pid(events["many"])]["views"], ["sky"])
        self.assertEqual(hints[pid(events["nowhere"])]["views"], ["sky"])
        self.assertEqual(hints[pid(events["plain"])]["views"], ["sky"])
        for k, h in hints.items():
            self.assertTrue(set(h["views"]) <= set(X.VIEW_VOCABULARY))
            self.assertEqual((h["chosen_by"], h["light"], h["focus"]), ("rule", False, f"event/{k}"))
        ents = {k: v for p in parts for k, v in p["entities"].items()}
        self.assertEqual(ents[f"place/{pid(located)}"]["geo"],
                         {"lon": 39.61, "lat": 24.5, "confidence": "certain", "basis": "textual", "recorded_by": []})
        self.assertEqual(ents[f"place/{pid(many)}"]["geo"], {"many": 2})
        self.assertEqual(ents[f"place/{pid(nowhere)}"]["geo"], {"unlocated": True, "basis": "textual"})
        terms = {k: v for p in parts for k, v in p["terms"].items()}
        self.assertEqual(terms["lc:certain"], {"en": "certain"})

    def test_place_geo_follows_obsdata(self):
        fx = Fx()
        places = [fx.place(f"fxGeo{k}", f"Place {k}") for k in "ABCD"]
        fx.geometry(places[0], (39.61, 24.5))
        fx.geometry(places[1], (39.0, 21.0))
        fx.geometry(places[1], (40.0, 22.0))
        fx.geometry(places[2], None, "unlocated")
        for k, p in enumerate(places):
            fx.event(f"fxGeoE{k}", f"Rihla {k}", place=p)
        site = site_of(fx)
        obs = obsdata()
        data = obs.ObsData(site, obs.Translator(json.loads((SITE / "observatory" / "i18n" / "en.json")
                                                           .read_text(encoding="utf-8"))))
        r = X.Resolver(site, bank=[])
        for p in places:
            node = data.nodes[data.index[p]]
            geo = r.entity(r.ref(p)).get("geo")
            with self.subTest(p):
                if "geo" in node:
                    self.assertEqual([geo["lon"], geo["lat"]], node["geo"][:2])
                elif "geoMany" in node:
                    self.assertEqual(geo, {"many": node["geoMany"]})
                else:
                    self.assertTrue(geo is None or geo.get("unlocated"))
        self.assertIsNone(r.entity(r.ref(places[3])).get("geo"))

    def test_arabic_dates_use_digits_0_to_9_and_gregorian_first(self):
        fx = Fx()
        ev = fx.event("fxArA", "Rihla dated", dates=("0624-03-05", "0624-03-05"), precision="day")
        site = site_of(fx)
        r = X.Resolver(site, bank=[])
        dates = r.entity(r.ref(ev))["dates"]
        self.assertEqual(len(dates), 1)
        text = dates[0]["text"]
        self.assertEqual(text["en"], "5 March 624 CE")
        self.assertIn("624", text["ar"])
        self.assertTrue(text["ar"].startswith("5 "))
        self.assertIsNone(re.search(r"[٠-٩۰-۹]", text["ar"]))
        self.assertIn("مارس", text["ar"])


def obsdata():
    spec = importlib.util.spec_from_file_location("obsdata", SITE / "observatory" / "obsdata.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Parts(unittest.TestCase):
    """Parts are cut greedily within the budget; a stop too big alone fails closed."""

    @classmethod
    def setUpClass(cls):
        fx, cls.i = big_people_graph(600)
        cls.site = site_of(fx)
        cls.j = people(cls.site)

    def test_parts_stay_under_the_budget(self):
        for budget in (X.PART_BUDGET, 40_000):
            res = export(self.site, [self.j], part_budget=budget)
            head, parts, research = unpack(res, self.j.slug)
            with self.subTest(budget=budget):
                self.assertGreater(len(parts), 1)
                for k, part in enumerate(parts, 1):
                    raw = res["files"][f"journeys/{self.j.slug}/part-{k}.json"]
                    self.assertLessEqual(len(raw), budget)
                    self.assertLessEqual(len(res["files"][f"journeys/{self.j.slug}/research-{k}.json"]), budget)
                    self.assertTrue(part["steps"])
                    self.assertEqual(part["part"], k)
                keys = [s["key"] for p in parts for s in p["steps"]]
                self.assertEqual(keys, [s["key"] for s in head["stops"]] + [s["key"] for s in head["set_apart"]])
                for s in head["stops"]:
                    self.assertIn(s["key"], [x["key"] for x in parts[int(s["part"][5:-5]) - 1]["steps"]])

    def test_every_reference_resolves_within_its_part(self):
        res = export(self.site, [self.j], part_budget=40_000)
        _, parts, _ = unpack(res, self.j.slug)
        for part in parts:
            claims, ents, terms, passages = refs_of_part(part)
            self.assertEqual(claims - set(part["claims"]), set())
            self.assertEqual(ents - set(part["entities"]), set())
            self.assertEqual(terms - set(part["terms"]), set())
            self.assertEqual(passages - set(part["passages"]), set())

    def test_an_over_budget_stop_fails_closed_naming_it(self):
        fx = Fx()
        battle = fx.event("fxHugeBattle", "Battle of Fixtureplace")
        who = fx.person("fxHugePerson", "Person Huge")
        fx.participation(battle, who)
        for k in range(60):
            fx.claim(who, "rel_participated_in", battle, cite=f"Fixture work, vol. 1, p. {k}", role="x" * 400)
        site = site_of(fx)
        with self.assertRaises(J.RuleError) as cm:
            export(site, [people(site)], part_budget=20_000)
        self.assertIn("fxHugePerson", str(cm.exception))
        export(site, [people(site)])        # within the default budget it fits

    def test_caps(self):
        fx = Fx()
        battle = fx.event("fxCapBattle", "Battle of Fixtureplace")
        for k in range(120):
            fx.participation(battle, fx.person(f"fxCap{k:03d}", f"Person {k:03d}"))
        site = site_of(fx)
        j = J.build(site, J.validate(events_spec(["Fixtureplace"], follow=(), max_links=0, kinds=("event",))))
        res = export(site, [j])
        _, parts, _ = unpack(res, j.slug)
        st = all_steps(parts)[0]
        self.assertEqual(st["claims"]["total"], 120)
        self.assertEqual(len(st["claims"]["ids"]), X.CLAIM_CAP)
        self.assertLessEqual(len(st["narration"]), X.NARRATION_CAP)
        self.assertEqual(st["counts"], {"records": 120, "discover": 0})
        self.assertEqual(X.DEPTH_POLICY["discover"]["narration"], 3)
        self.assertEqual(X.DEPTH_POLICY["study"]["claim_list"], 40)


class ContentDigest(unittest.TestCase):
    def test_content_sha_sees_participation_changes(self):
        shas, prints = [], []
        for role in ("role_participant", "role_leader", "role_participant"):
            site = site_of(role_pair(role))
            j = people(site)
            res = export(site, [j])
            shas.append(unpack(res, j.slug)[0]["content_sha"])
            prints.append(X.fingerprint(site.g))
        self.assertNotEqual(shas[0], shas[1])
        self.assertEqual(shas[0], shas[2])
        self.assertEqual(prints[0], prints[1])           # blank nodes: the fingerprint cannot see roles

    def test_content_sha_ignores_layout(self):
        fx, _ = big_people_graph(60)
        site = site_of(fx)
        j = people(site)
        a = unpack(export(site, [j]), j.slug)[0]
        b = unpack(export(site, [j], part_budget=20_000), j.slug)[0]
        self.assertNotEqual(a["parts"], b["parts"])
        self.assertEqual(a["content_sha"], b["content_sha"])

    def test_synthetic_ids_are_stable_across_builds(self):
        ids = []
        for _ in range(2):
            site = site_of(role_pair())
            ids.append(sorted(X.ClaimIndex(site).claim))
        self.assertEqual(ids[0], ids[1])
        self.assertIn("participation/fxRoBattle/fxRoB/role_participant", ids[0])
        self.assertIn("participation/fxRoBattle/fxRoProphet/role_leader", ids[0])
        self.assertTrue(all(i.startswith(X.CLAIM_PREFIXES) for i in ids[0]))

    def test_fingerprint_algorithm_matches_obsdata_on_a_fixture(self):
        site = site_of(facade_graph())
        self.assertEqual(X.fingerprint(site.g), obsdata().ObsData.fingerprint(SimpleNamespace(g=site.g)))


class Shape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        site = site_of(facade_graph())
        with tempfile.TemporaryDirectory() as tmp:
            list_file(tmp, ["Person C", "Person A"], ["Person C", "Person A", "Person B"])
            specs = [events_spec(["Hijra"]),
                     people_spec(words=("Badr",), order="e3", group_by="side", not_words=["expedition"]),
                     stories_spec(["Makkan"])]
            journeys = [J.build(site, J.validate(s), lists_root=tmp) for s in specs]
            cls.res = X.resolve_all(site, None, journeys=journeys, bank=[], lists_root=tmp)
        cls.files = {p: json.loads(b) for p, b in cls.res["files"].items()}

    def test_export_shape_and_version(self):
        f = self.files
        self.assertEqual((f["index.json"]["format"], f["index.json"]["version"]), ("marsad-journeys", 1))
        self.assertEqual((f["pages.json"]["format"], f["pages.json"]["version"]), ("marsad-learn-pages", 1))
        self.assertEqual(set(f["strings.json"]), {"en", "ar"})
        self.assertEqual(f["index.json"]["depths"], ["discover", "study", "research"])
        self.assertEqual(f["index.json"]["strings"], "strings.json")
        self.assertEqual(f["index.json"]["pages"], "pages.json")
        for e in f["index.json"]["journeys"]:
            head = f[e["file"]]
            self.assertEqual(e["file"], f"journeys/{e['slug']}/journey.json")
            self.assertEqual((head["format"], head["version"], head["slug"]), ("marsad-journey", 1, e["slug"]))
            self.assertEqual(head["content_sha"], e["content_sha"])
            for p, r in zip(head["parts"], head["research"]):
                part, research = f[f"journeys/{e['slug']}/{p}"], f[f"journeys/{e['slug']}/{r}"]
                self.assertEqual((part["format"], part["version"], part["slug"]), ("marsad-journey-part", 1, e["slug"]))
                self.assertEqual((research["format"], research["version"]), ("marsad-journey-research", 1))
                self.assertEqual(part["content_sha"], head["content_sha"])
                self.assertEqual(part["graph"], {"fingerprint": head["graph"]["fingerprint"]})
            for s in head["stops"]:
                self.assertEqual(set(s["urls"]), set(X.DEPTHS))
                for d, url in s["urls"].items():
                    self.assertTrue(url.endswith(f"#s-{s['key']}"))
                    self.assertTrue(url.startswith(f"learn/{e['slug']}/"))
                self.assertEqual(s["urls"][head["door"]], f"learn/{e['slug']}/#s-{s['key']}")
            self.assertEqual(head["reader"], {"url": f"learn/{e['slug']}/", "anchor": "s-{key}"})
            self.assertEqual(sorted(e["urls"]), sorted(X.DEPTHS))
        self.assertEqual(sorted(p for p in f if p.startswith("journeys/") and p.endswith("journey.json")),
                         sorted(e["file"] for e in f["index.json"]["journeys"]))

    def test_every_reference_resolves_within_its_part(self):
        for path, part in self.files.items():
            if "/part-" not in path:
                continue
            claims, ents, terms, passages = refs_of_part(part)
            with self.subTest(path):
                self.assertEqual(claims - set(part["claims"]), set())
                self.assertEqual(ents - set(part["entities"]), set())
                self.assertEqual(terms - set(part["terms"]), set())
                self.assertEqual(passages - set(part["passages"]), set())
                for r in ents:
                    self.assertRegex(r, REF)
                for t in terms:
                    self.assertRegex(t, TERM)

    def test_e3_order_and_sorts(self):
        head = self.files["journeys/fixture-people/journey.json"]
        self.assertEqual(head["order_applied"], "e3")
        self.assertEqual(head["lists"]["state"], "reviewed")
        keys = [t["t"] for t in head["rule_text"]]
        self.assertEqual(keys, ["learn.order.e3", "learn.order.e3_sources", "learn.order.e3_links",
                                "learn.order.e3_lists", "learn.order.e3_no_last", "learn.rule.group_side"])
        depths = {t["t"]: t["d"] for t in head["rule_text"]}
        self.assertEqual((depths["learn.order.e3_lists"], depths["learn.order.e3_sources"]), ("study", "discover"))
        for s in head["stops"]:
            self.assertEqual(set(s["sort"]), {"default", "az", "links", "accepted_islam"})
            self.assertEqual(s["sort"]["default"], s["n"])
        self.assertEqual(sorted(s["sort"]["az"] for s in head["stops"]), list(range(1, len(head["stops"]) + 1)))
        steps = {s["key"]: s for p in head["parts"] for s in self.files[f"journeys/fixture-people/{p}"]["steps"]}
        first = steps[head["stops"][0]["key"]]
        self.assertEqual(first["e3"]["tier"], 0)
        # main: the Prophet, A (rashidun), B (the ten); against: C (rashidun), D (everyone else)
        self.assertEqual([steps[s["key"]]["e3"]["tier"] for s in head["stops"]], [0, 1, 2, 1, 3])
        self.assertEqual([s["group"] for s in head["stops"]], ["main", "main", "main", "against", "against"])

    def test_every_exported_string_has_an_origin(self):
        strings = self.files["strings.json"]
        learn_ar = J.load_i18n()["ar"]
        site_ar = json.loads((SITE / "i18n" / "ar.json").read_text(encoding="utf-8"))
        for k, v in strings["en"].items():
            self.assertEqual(v, EN.get(k, SITE_EN.get(k)), k)
        for k, v in strings["ar"].items():
            self.assertEqual(v, learn_ar.get(k, site_ar.get(k)), k)
        named = set()
        for path, doc in self.files.items():
            if path != "strings.json":
                named |= keys_named(doc)
        missing = [k for k in sorted(named) if k not in strings["en"] and f"{k}.one" not in strings["en"]]
        self.assertEqual(missing, [])
        for k in ("learn.narr.more", "learn.discover.no_work"):
            self.assertIn(f"{k}.one", strings["en"])
            self.assertIn(f"{k}.other", strings["en"])

    def test_the_head_carries_the_rule_terms_and_the_graph_its_story_count(self):
        """The rule box reads only the export (design §8): every term the rule names has its
        graph label in the head's terms, whether or not a claim of the journey uses it, and
        the graph block says how many stories the graph holds (a story's "of {total}")."""
        from fixtures import RELATIONS
        for e in self.files["index.json"]["journeys"]:
            head = self.files[e["file"]]
            with self.subTest(e["slug"]):
                self.assertEqual(head["graph"]["stories"], self.files["index.json"]["graph"]["stories"])
                if head["type"] != "people":
                    self.assertEqual(head["terms"], {})
                    continue
                want = {f"pk:{c.split(':')[1]}": {"en": RELATIONS[c.split(":")[1]]}
                        for c in head["select"]["participation"]["claims"] + head["select"]["also_show"]}
                want["q:q_later"] = {"en": "marker for the tests"}
                self.assertEqual(head["terms"], want)
                self.assertEqual([r for r, _ in X.rule_terms(head["select"])], list(want))
        site = site_of(facade_graph())
        self.assertEqual(self.files["index.json"]["graph"]["stories"], len(site.by_kind["story"]))
        self.assertGreater(len(site.by_kind["story"]), 0)

    def test_title_and_lead_carry_en_and_ar(self):
        for e in self.files["index.json"]["journeys"]:
            for k in ("title", "lead"):
                self.assertEqual(set(e[k]), {"key", "en", "ar"})
                self.assertEqual(e[k]["en"], EN[e[k]["key"]])
                self.assertEqual(e[k]["ar"], AR[e[k]["key"]])

    def test_reasons_order_notes_and_set_apart_texts_are_in_the_strings(self):
        kinds, _ = step_templates(self, self.files)
        self.assertIn("named", kinds)


class FacadeLock(unittest.TestCase):
    def test_facade_lock_is_current(self):
        want = json.loads((LEARN / "facade.lock").read_text(encoding="utf-8"))
        if X.facade_lock() != want:
            self.fail(X.LOCK_MESSAGE)

    def test_the_lock_message_is_the_one_the_design_gives(self):
        self.assertEqual(X.LOCK_MESSAGE, "The Atlas reads this. Rebuild atlas/index.html (atlas/build.py on "
                                         "build/graph-all.ttl) and run learn/journey_export.py --lock.")
        self.assertEqual(set(json.loads((LEARN / "facade.lock").read_text(encoding="utf-8"))),
                         {"facade_version", "inputs", "engine"})

    def test_the_lock_sees_a_changed_rule_and_ignores_layer_keys(self):
        base = X.facade_inputs()
        with tempfile.TemporaryDirectory() as tmp:
            for path in sorted((LEARN / "journeys").glob("*.json")):
                (Path(tmp) / path.name).write_bytes(path.read_bytes())
            hijrah = Path(tmp) / "hijrah-step-by-step.json"
            spec = json.loads(hijrah.read_text(encoding="utf-8"))
            for extra in ({"hold_study": False}, {"lead_study": "journey.badr.lead_study"}):
                hijrah.write_text(json.dumps({**spec, **extra}), encoding="utf-8")
                self.assertEqual(J.sha12(X.facade_inputs(tmp)), J.sha12(base), extra)
            changed = copy.deepcopy(spec)
            changed["select"]["max_links"] = 1
            hijrah.write_text(json.dumps(changed), encoding="utf-8")
            self.assertNotEqual(J.sha12(X.facade_inputs(tmp)), J.sha12(base))


# --------------------------------------------------------------------------- the real graph
@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class OnThePageGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = Site(GRAPH)
        cls.res = X.resolve_all(cls.site, None, graph_file=GRAPH)
        cls.files = {p: json.loads(b) for p, b in cls.res["files"].items()}
        cls.slugs = [e["slug"] for e in cls.files["index.json"]["journeys"]]

    def test_three_journeys_with_their_stops_in_the_engine_order(self):
        self.assertEqual(self.slugs, ["first-believers", "hijrah-step-by-step", "people-of-badr"])
        built = {j.slug: j for j in J.build_all(self.site, J.load_specs(LEARN / "journeys"))}
        for slug in self.slugs:
            head = self.files[f"journeys/{slug}/journey.json"]
            with self.subTest(slug):
                self.assertEqual([s["key"] for s in head["stops"]], [st.entity.pid for st in built[slug].steps])
                self.assertEqual([s["key"] for s in head["set_apart"]], [st.entity.pid for st in built[slug].set_apart])
                self.assertEqual(head["state"], "draft")
                self.assertEqual(head["story_mode"]["open"], False)
                self.assertEqual(head["rule_sha"], J.rule_sha(J.load_specs(LEARN / "journeys")[self.slugs.index(slug)]))
        badr = self.files["journeys/people-of-badr/journey.json"]
        self.assertEqual((badr["order_applied"], badr["lists"]["applied"]), ("e3_pending", False))

    def test_every_reason_kind_and_order_note_has_its_sentence_in_the_strings(self):
        kinds, notes = step_templates(self, self.files)
        self.assertTrue({"named", "part_of", "has_part"} <= kinds, kinds)
        self.assertEqual(notes, {"part", "recorded", "unrecorded"})

    def test_fingerprint_matches_obsdata(self):
        obs = obsdata()
        data = obs.ObsData(self.site, obs.Translator(json.loads((SITE / "observatory" / "i18n" / "en.json")
                                                                .read_text(encoding="utf-8"))))
        self.assertEqual(X.fingerprint(self.site.g), data.fingerprint())
        self.assertEqual(self.files["index.json"]["graph"]["fingerprint"], data.fingerprint())
        self.assertEqual(self.files["index.json"]["graph"]["file"], "build/graph.ttl")

    def test_parts_stay_under_the_budget(self):
        for path, raw in self.res["files"].items():
            if "/part-" in path or "/research-" in path:
                self.assertLessEqual(len(raw), X.PART_BUDGET, path)

    def test_no_gloss_in_head_or_part_files(self):
        gloss = [x for p, d in self.files.items() if "/research-" in p for x in d["glosses"].values()]
        self.assertTrue(gloss)
        for path, raw in self.res["files"].items():
            if "/research-" not in path:
                self.assertNotIn(X.GLOSS_PREFIX, raw.decode("utf-8"), path)
        for path, doc in self.files.items():
            for c in (doc.get("claims") or {}).values() if "/part-" in path else ():
                self.assertFalse(c["kind"] == "assertion" and "role" in c, path)

    def test_short_source_form(self):
        t = X.translators()["en"]
        unmatched, seen = [], 0
        for path, doc in self.files.items():
            if "/part-" not in path:
                continue
            for c in doc["claims"].values():
                if not c.get("passage"):
                    continue
                p = doc["passages"][c["passage"]]
                if not p["cite"]:
                    continue
                seen += 1
                if not X.short_matches(p["cite"]):
                    unmatched.append(p["cite"])
                short = X.source_line(c, "discover", doc["passages"], t) if c["discover"] else p["short"]
                self.assertEqual(J.review_words(short), [], short)
                self.assertNotIn(";", p["short"])
                self.assertNotIn("(", p["short"].replace(" (a document generated with AI)", ""))
        self.assertGreater(seen, 0)
        self.assertEqual(sorted(set(unmatched)), [])
        self.assertEqual(X.short_citation("Ibn Hishām, al-Sīra al-Nabawiyya (al-Saqqā et al. ed., Cairo 1375/1955; "
                                          "provisional), vol. 1, p. 485; OpenITI ms1, lines 2–3"),
                         "Ibn Hishām, al-Sīra al-Nabawiyya, vol. 1, p. 485")
        self.assertEqual(X.short_citation("50 Stories (rev 7), Part 1, story 9"), "50 Stories, Part 1, story 9")
        self.assertEqual(X.short_citation("Work A (ed. B), vol. 2, pp. 652–653; lines 1"), "Work A, vol. 2, pp. 652–653")

    def test_title_and_lead_carry_en_and_ar_and_ar_has_parity_and_no_review_stems(self):
        """design §10 and §12: the index and each head carry title, lead and lead_study as
        {key, en, ar}, the texts of learn/i18n/en.json and ar.json; the ar text has the
        en text's {placeholders}; the ar title and lead have no Arabic review stem (lead_study
        is a Study and Research text, design §12 and §20.1); strings.json holds the same."""
        slot = re.compile(r"\{([a-z_]+)\}")
        strings = self.files["strings.json"]
        for e in self.files["index.json"]["journeys"]:
            head = self.files[e["file"]]
            for role in J.TEXT_ROLES:
                with self.subTest(e["slug"], role=role):
                    self.assertEqual(head[role], e[role])
                    if e[role] is None:
                        self.assertEqual(role, "lead_study")
                        continue
                    key = e[role]["key"]
                    self.assertEqual(e[role], {"key": key, "en": EN[key], "ar": AR[key]})
                    self.assertTrue(e[role]["ar"])
                    if role in ("title", "lead"):
                        self.assertEqual(J.ar_review_stems(e[role]["ar"]), [])
                    self.assertEqual(sorted(slot.findall(e[role]["ar"])), sorted(slot.findall(e[role]["en"])))
                    self.assertEqual((strings["en"][key], strings["ar"][key]), (EN[key], AR[key]))

    def test_arabic_dates_use_digits_0_to_9_and_gregorian_first_on_the_page_graph(self):
        """design §12 and L2: every exported date text, en and ar, writes its digits 0-9
        (no U+0660-0669, no U+06F0-06F9), and where it gives a year, the first year it
        gives is a Gregorian year inside the recorded extent."""
        seen = 0
        for path, doc in sorted(self.files.items()):
            if "/part-" not in path:
                continue
            for ref, ent in sorted(doc["entities"].items()):
                for d in ent.get("dates") or ():
                    seen += 1
                    for lang in ("en", "ar"):
                        text = d["text"][lang]
                        with self.subTest(path, ref=ref, lang=lang):
                            self.assertIsNone(ARABIC_INDIC_DIGIT.search(text), text)
                            year = re.search(r"\d{3,4}", text)
                            if year and d["earliest"] and d["latest"]:
                                self.assertLessEqual(int(d["earliest"][:4]), int(year.group()), text)
                                self.assertLessEqual(int(year.group()), int(d["latest"][:4]), text)
        self.assertGreater(seen, 0)

    def test_discover_flags_and_items_on_the_real_graph(self):
        for path, doc in self.files.items():
            if "/part-" not in path:
                continue
            for c in doc["claims"].values():
                if c["discover"]:
                    self.assertTrue(doc["passages"][c["passage"]]["cite"])
                    self.assertFalse({c["status"], *c.get("statuses", [])} & {"rejected", "superseded"})
                if c["kind"] != "assertion":
                    self.assertFalse(c["discover"])
            for st in doc["steps"]:
                for item in st["narration"] + st["prompts"]:
                    if item["d"] == "discover" and "c" in item:
                        self.assertTrue(any(doc["claims"][x]["discover"] for x in item["c"]))
                if any(i["d"] == "discover" for i in st["narration"]):
                    self.assertGreater(st["counts"]["discover"], 0, st["key"])
                if st["counts"]["discover"] == 0:
                    self.assertFalse(any(i["d"] == "discover" for i in st["narration"]), st["key"])

    def test_every_reference_resolves_within_its_part(self):
        for path, part in self.files.items():
            if "/part-" in path:
                claims, ents, terms, passages = refs_of_part(part)
                with self.subTest(path):
                    self.assertEqual(claims - set(part["claims"]), set())
                    self.assertEqual(ents - set(part["entities"]), set())
                    self.assertEqual(terms - set(part["terms"]), set())
                    self.assertEqual(passages - set(part["passages"]), set())

    def test_export_is_byte_stable_in_process(self):
        again = X.resolve_all(Site(GRAPH), None, graph_file=GRAPH)
        self.assertEqual(sorted(again["files"]), sorted(self.res["files"]))
        for p in self.res["files"]:
            self.assertEqual(again["files"][p], self.res["files"][p], p)
        self.assertEqual(again["digest"], self.res["digest"])

    def test_export_is_byte_stable_across_hash_seeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            outs = {}
            for budget in (None, SMALL_BUDGET):
                for seed in ("1", "2"):
                    out = Path(tmp) / f"{seed}-{budget}"
                    cmd = [sys.executable, str(CLI), "--graph", str(GRAPH), "--out", str(out)]
                    if budget:
                        cmd += ["--part-budget", budget]
                    subprocess.run(cmd, check=True, capture_output=True, env={**os.environ, "PYTHONHASHSEED": seed},
                                   cwd=ROOT)
                    outs[(seed, budget)] = out
                with self.subTest(budget=budget):
                    self.assertEqual(differs(filecmp.dircmp(outs[("1", budget)], outs[("2", budget)])), [])
            small = sorted(p.name for p in (outs[("1", SMALL_BUDGET)] / "journeys" / "people-of-badr").glob("part-*.json"))
            self.assertGreater(len(small), 2)
            for p in (outs[("1", SMALL_BUDGET)]).rglob("*.json"):
                if p.name.startswith(("part-", "research-")):
                    self.assertLessEqual(p.stat().st_size, int(SMALL_BUDGET), p)
            # the CLI writes exactly what resolve_all gives
            cli = {p.relative_to(outs[("1", None)]).as_posix(): p.read_bytes()
                   for p in outs[("1", None)].rglob("*") if p.is_file() and p.name != X.EXPORT_MARKER}
            self.assertEqual(cli, self.res["files"])

    def test_the_export_writes_nothing_into_the_repository_and_no_id_into_its_files(self):
        def snapshot():
            return {p.relative_to(LEARN).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for d in ("journeys", "lists") for p in sorted((LEARN / d).rglob("*")) if p.is_file()}

        before = snapshot()
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            X.main(["--graph", str(GRAPH), "--out", str(Path(tmp) / "out")])
            X.main(["--graph", str(GRAPH), "--out", str(Path(tmp) / "out")])       # a second run replaces the first
            for folder in (LEARN / "journeys", LEARN / "lists", LEARN, ROOT):
                with self.assertRaises(J.RuleError):
                    X.write_export(folder, {"x.json": b"{}\n"})
            stray = Path(tmp) / "stray"
            stray.mkdir()
            (stray / "notes.txt").write_text("not an export", encoding="utf-8")
            with self.assertRaises(J.RuleError):
                X.write_export(stray, {"x.json": b"{}\n"})
        self.assertEqual(snapshot(), before)
        pids = {e.pid for e in self.site.entities.values()}
        for path in [LEARN / "facade.lock", LEARN / "FORMAT.md", LEARN / "journey_export.py",
                     *sorted((ROOT / "docs" / "handover").glob("learn-v2*.md"))]:
            text = path.read_text(encoding="utf-8")
            self.assertEqual(sorted(p for p in pids if p in text), [], path)

    def test_atlas_projection_is_the_atlas_record(self):
        """atlas_projection gives what atlas/build.py load_journeys builds (the replica in
        test_journeys), with IRIs for node numbers and the computed story_mode.open."""
        from test_journeys import atlas_load_journeys, node_index
        index = node_index(self.site)
        back = {n: iri for iri, n in index.items()}
        replica = atlas_load_journeys(self.site, index, self.fail, LEARN / "journeys", LEARN / "i18n" / "en.json")
        built = J.build_all(self.site, J.load_specs(LEARN / "journeys"))
        for rec, j in zip(replica, built):
            mine = X.atlas_projection(j, EN)
            self.assertEqual(mine.pop("story_mode"), {"open": False})
            as_iris = dict(rec, steps=[back[n] for n in rec["steps"]], apart=[back[n] for n in rec["apart"]],
                           anchors=[back[n] for n in rec["anchors"]],
                           why=[[[k, back.get(o) if o != -1 else None, t] for k, o, t in rs] for rs in rec["why"]])
            self.assertEqual(mine, as_iris, j.slug)


def differs(cmp) -> list:
    bad = list(cmp.diff_files) + list(cmp.left_only) + list(cmp.right_only)
    for sub in cmp.subdirs.values():
        bad += differs(sub)
    return bad


class FormatDoc(unittest.TestCase):
    """learn/FORMAT.md states the contract; its canonical() vector must hold."""

    def test_format_md_states_the_canonical_vector(self):
        text = (LEARN / "FORMAT.md").read_text(encoding="utf-8")
        vec = dict(re.findall(r"^canonical-vector (input|bytes|sha12): +(.+)$", text, flags=re.M))
        obj = json.loads(vec["input"])
        self.assertEqual(J.canonical(obj).decode("utf-8"), vec["bytes"])
        self.assertEqual(J.sha12(obj), vec["sha12"])

    def test_format_md_names_every_file_and_the_discover_rule(self):
        text = (LEARN / "FORMAT.md").read_text(encoding="utf-8")
        for needle in ("index.json", "strings.json", "pages.json", "journey.json", "part-", "research-",
                       "marsad-journey", "marsad-journeys", "marsad-journey-part", "marsad-journey-research",
                       "marsad-learn-pages", "discover", "content_sha", "fingerprint", "canonical", "PART_BUDGET",
                       "rejected", "superseded", "citation"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
