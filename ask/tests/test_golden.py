"""The golden set (ask/golden/questions.jsonl): every question, its expected query and its
expected rows. Entities are named by their recorded label and resolved here, at test
time, so re-minted IDs never break the set. Every line is labelled "pending scholar
check" (docs/13: the golden set must be scholar-checked; this one is not yet).

Run:  .venv/bin/python -m unittest discover -s ask/tests
"""
import unittest

from common import engine, golden, have_graph, i18n

REVIEW = "pending scholar check"
OUTCOMES = {"answer", "refusal", "unsupported", "ambiguous", "not_found", "invalid", "empty", "too_long"}


def rows_of(res: dict) -> list[dict]:
    if res is None:
        return []
    if res["type"] == "count":
        return res["set"]["rows"]
    return res.get("rows", [])


def check(case: dict, eng, T) -> list[str]:
    from ask.translate import answer
    a = answer(case["question"], eng, T)
    exp = case["expect"]
    if a["outcome"] != exp["outcome"]:
        return [f"outcome {a['outcome']!r}, expected {exp['outcome']!r} ({a.get('reason') or a.get('refusal') or a.get('dsl')})"]
    probs = []
    E = eng.E
    if "dsl" in exp and a.get("dsl") != exp["dsl"]:
        probs.append(f"dsl {a.get('dsl')!r}, expected {exp['dsl']!r}")
    res = a.get("result")
    if "rows" in exp:
        got = sorted(E[r["e"]]["l"] for r in rows_of(res))
        if got != sorted(exp["rows"]):
            probs.append(f"rows differ: missing {sorted(set(exp['rows']) - set(got))}, extra {sorted(set(got) - set(exp['rows']))}")
    if "tags" in exp:
        got = {E[r["e"]]["l"]: r.get("tag") for r in rows_of(res)}
        if got != exp["tags"]:
            probs.append(f"tags {got}, expected {exp['tags']}")
    if "absent" in exp:
        got = sorted({E[eng.C[j]["s"]]["l"] for j in res.get("absent", [])})
        if got != sorted(exp["absent"]):
            probs.append(f"absent {got}, expected {exp['absent']}")
    if "count" in exp and res.get("n") != exp["count"]:
        probs.append(f"count {res.get('n')}, expected {exp['count']}")
    if "steps" in exp:
        steps = res["steps"]
        if len(steps) != exp["steps"]:
            probs.append(f"{len(steps)} steps, expected {exp['steps']}")
        cur = res["a"]
        for s in steps:
            c = eng.C[s["c"]]
            if s["a"] != cur or {c["s"], c["o"]} != {s["a"], s["b"]}:
                probs.append(f"step {s} is not a claim joining its two ends")
            cur = s["b"]
        if steps and cur != res["b"]:
            probs.append("the path does not end at the second entity")
    if "dates" in exp and [d["t"] for d in res["dates"]] != exp["dates"]:
        probs.append(f"dates {[d['t'] for d in res['dates']]}, expected {exp['dates']}")
    if "about_n" in exp and res["n"] != exp["about_n"]:
        probs.append(f"about n {res['n']}, expected {exp['about_n']}")
    if "candidates" in exp:
        got = sorted(E[o["e"]]["l"] for o in a["options"])
        if got != sorted(exp["candidates"]):
            probs.append(f"candidates {got}, expected {exp['candidates']}")
        if any(o["dsl"] is None for o in a["options"]):
            probs.append("an ambiguous choice has no query to run")
    for key in ("refusal", "reason", "mention"):
        if key in exp and a.get(key) != exp[key]:
            probs.append(f"{key} {a.get(key)!r}, expected {exp[key]!r}")
    return probs


class GoldenFile(unittest.TestCase):
    def test_lines_are_well_formed(self):
        cases = golden()
        self.assertGreaterEqual(len([c for c in cases if c["expect"]["outcome"] != "refusal"]), 30)
        self.assertGreaterEqual(len([c for c in cases if c["expect"]["outcome"] == "refusal"]), 10)
        ids = [c["id"] for c in cases]
        self.assertEqual(len(ids), len(set(ids)))
        for c in cases:
            with self.subTest(c["id"]):
                self.assertEqual(c["review"], REVIEW)
                self.assertIn(c["expect"]["outcome"], OUTCOMES)
                self.assertTrue(c["question"].strip())
                if c["expect"]["outcome"] == "answer":
                    self.assertIn("dsl", c["expect"])

    def test_every_refusal_class_has_a_case(self):
        from ask.normalise import RULES
        classes = {r["class"] for r in RULES["refusals"]}
        covered = {c["expect"]["refusal"] for c in golden() if c["expect"]["outcome"] == "refusal"}
        self.assertEqual(classes - covered, set())


@unittest.skipUnless(have_graph(), "build/graph.ttl missing")
class GoldenAnswers(unittest.TestCase):
    def test_every_golden_question(self):
        eng, T = engine(), i18n()
        failures = {}
        for case in golden():
            with self.subTest(case["id"], question=case["question"]):
                probs = check(case, eng, T)
                if probs:
                    failures[case["id"]] = probs
                self.assertEqual(probs, [])
        self.assertEqual(failures, {})

    def test_golden_labels_name_one_entity_each(self):
        """Expected rows name entities by label; each label must exist in the graph."""
        eng = engine()
        labels = {e["l"] for e in eng.E}
        for case in golden():
            for label in case["expect"].get("rows", []) + case["expect"].get("absent", []) + case["expect"].get("candidates", []):
                with self.subTest(case["id"], label=label):
                    self.assertIn(label, labels)


if __name__ == "__main__":
    unittest.main()
