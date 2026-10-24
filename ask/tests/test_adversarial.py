"""The adversarial set (ask/golden/adversarial.jsonl): questions written to make the ask
engine do what it must not. Refusals in disguise (other wording, diacritics, fillers),
refusals hidden inside an answerable question, instructions aimed at the translator,
broken or hostile typed-in queries, names that are not in the graph or name several
people, limits, and fair questions that must not be refused.

Rule A2: a model may translate questions only after published adversarial tests. This
set is a first, in-house one, written by the people who built the engine; docs/07 asks
for tests written by people trying to break it, with the results published, and that is
still to come. Today the translator is rule-based; the set guards it too, and
test_parity.py runs every question through the browser port as well, so both engines
hold the same line.

Each line: id, attack, question, expect with one or more of
  outcome   the outcome it must have
  refusal   the refusal class it must name
  in        outcomes it may have
  not       outcomes it must not have
  html_safe the rendered answer must not carry markup from the question

Run:  .venv/bin/python -m unittest discover -s ask/tests
"""
import json
import unittest

from common import ASK, engine, have_graph, i18n

SET = ASK / "golden" / "adversarial.jsonl"
OUTCOMES = {"answer", "refusal", "unsupported", "ambiguous", "not_found", "invalid", "empty", "too_long"}
ATTACKS = {"disguise", "hidden", "injection", "query", "name", "limits", "fair"}


def cases() -> list[dict]:
    return [json.loads(line) for line in SET.read_text(encoding="utf-8").splitlines() if line.strip()]


class Shape(unittest.TestCase):
    def test_lines(self):
        seen = set()
        for c in cases():
            self.assertNotIn(c["id"], seen)
            seen.add(c["id"])
            self.assertIn(c["attack"], ATTACKS, c["id"])
            exp = c["expect"]
            self.assertTrue(set(exp) <= {"outcome", "refusal", "in", "not", "html_safe", "note"}, c["id"])
            for o in [exp.get("outcome")] + exp.get("in", []) + exp.get("not", []):
                self.assertTrue(o is None or o in OUTCOMES, c["id"])

    def test_every_attack_and_class(self):
        cs = cases()
        self.assertEqual({c["attack"] for c in cs}, ATTACKS)
        from ask.normalise import RULES
        classes = {r["class"] for r in RULES["refusals"]}
        named = {c["expect"].get("refusal") for c in cs} - {None}
        self.assertEqual(named, classes, "every refusal class has at least one adversarial question")


@unittest.skipUnless(have_graph(), "build/graph.ttl missing")
class Adversarial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ask.build_ask import cache_entries, examples_of
        from ask.present import Presenter
        cls.eng, cls.T = engine(), i18n()
        cls.pres = Presenter(cls.eng, cls.T, "../", examples_of(cache_entries()))

    def test_holds(self):
        from ask.translate import answer
        probs = []
        for c in cases():
            a = answer(c["question"], self.eng, self.T)
            o, exp = a["outcome"], c["expect"]
            why = a.get("refusal") or a.get("reason") or a.get("dsl") or ""
            if "outcome" in exp and o != exp["outcome"]:
                probs.append(f"{c['id']}: {o} ({why}), expected {exp['outcome']}")
            if "refusal" in exp and a.get("refusal") != exp["refusal"]:
                probs.append(f"{c['id']}: refusal {a.get('refusal')}, expected {exp['refusal']}")
            if "in" in exp and o not in exp["in"]:
                probs.append(f"{c['id']}: {o} ({why}), expected one of {exp['in']}")
            if o in exp.get("not", []):
                probs.append(f"{c['id']}: {o} ({why}) is not allowed")
            if exp.get("html_safe"):
                html = self.pres.render(a).lower()
                for bad in ("<script", "<img"):
                    if bad in html:
                        probs.append(f"{c['id']}: rendered answer carries {bad!r}")
        self.assertEqual(probs, [], "\n".join(probs))


if __name__ == "__main__":
    unittest.main()
