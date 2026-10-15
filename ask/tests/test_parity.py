"""Python and the browser port give the same answers and the same HTML.

ask/static/ask.js is run in Node (ask/tests/parity_runner.cjs) on the same index the
page loads, for every golden question and several hundred more made from the graph's
own names (every shape, spelling variants, time windows, typed-in queries, broken
queries, refusals, odd input). For each, the answer object and the rendered HTML must
be identical. The normaliser and the calendar bounds are compared too, on every entity
name and a list of awkward strings. Skipped when node is not installed.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from common import ASK, engine, golden, have_graph, i18n

NODE = shutil.which("node")
RUNNER = ASK / "tests" / "parity_runner.cjs"
BASE = "../"

ODD = [
    "", "   ", "?", "!!!", "a" * 400, "\U0001F600 who was at badr \U0001F600", "WHO WAS AT BADR",
    "who  was   at\tbadr", "Who was at Badr ﷺ?", "who was at بدر",
    "من كان في بدر", "events between 1 and 5",
    "events between 622 and 630", "what happened in 624", "what happened in 2 AH",
    "what happened between 13 bh and 1 ah", "Who was at the Battle of Badr in 2 AH?",
    "Who was at Makkah between 1 and 8 AH?", "relatives of abu bakr, reviewed only",
    "how many people were at badr, reviewed claims only", "when was the battle of badr, reviewed only",
    "Who was at Route waypoint (unidentified)?", "Who was in the story of Ali and Fatimah?",
    "who was at the Brotherhood of the Muhajirun and Ansar", "who was at badr and uhud and khaybar",
    "Who were the sons of the Prophet?", "Who were Umar's sisters?", "Whom did Ali marry?",
    "Who was the mother of Fatima bint Muhammad?", "Parents of Aisha", "Hudaybiyya", "Badr",
    "What is Badr?", "Who was Bilal?", "information about the Battle of the Trench",
    "Who met Bilal?", "Bilal's connections", "What connects Badr and Uhud?",
    "path between Khadija and Umar", "people connected to both Bilal and Ammar",
    "Which battles took place in Madinah?", "what happened at mecca between 600 and 640 ce",
    "Who was absent at Hudaybiyya?", "Who led the army at Uhud?", "Who commanded the Conquest of Makkah?",
    "Is it true that Bilal was at Badr?", "Did Abu Bakr fight at Uhud?", "Were the Ansar at Badr?",
    "when did the prophet die", "date of the death of Hamza", "what year was the battle of the trench",
    "where was the farewell pilgrimage held", "stories about Abu Bakr", "tell me a story about Bilal",
    "in which stories does Umar appear", "What is the ruling on music?", "Can I eat camel meat?",
    "What does Islam say about charity?", "Explain the verse of light", "Is the hadith of Jibril sahih?",
    "Write me a hadith", "Draw the Prophet", "Draw a map of the Hijra route",
    "Who was the best caliph?", "Top 10 companions", "Who had the most wives?",
    "Was Umar greater than Uthman?", "What might have happened at Thawr?", "Is Abu Talib in hell?",
    "Who was to blame at Jamal?", "Show me the centrality of Abu Bakr",
    "can you tell me who was at the conquest of makkah please", "list the companions at badr",
]

DSL = [
    'participants(event "Battle of Badr")',
    'path(person "Bilāl b. Rabāḥ", person "ʿĀʾisha bint Abī Bakr", max: 1)',
    'events(at: place "Makkah", from: 5 AH, to: 1 AH)', "foo(x)",
    'participants(person "Abū Bakr al-Ṣiddīq")',
    'both(events(at: place "Makkah"), participants(event "Battle of Badr"))',
    'participants(event "Battle of Badr"', 'participants(event "Battle of Badr)', "about(place #NOPE)",
    'path(person "Bilāl b. Rabāḥ", person "Bilāl b. Rabāḥ")', "events()",
    'people(at: place "Badr", from: 2 AH)', 'events(involving: person "Bilāl b. Rabāḥ", from: 600 CE, to: 2100 CE)',
    "events(from: 0 AH, to: 1 AH)", 'relatives(person "Abū Bakr al-Ṣiddīq", tie: cousin)',
    'count(reviewed(people(at: place "Badr")))', 'either(people(at: place "Badr"), people(at: place "Uḥud"))',
    "count(" * 8 + 'people(at: place "Badr")' + ")" * 8, 'about(place "Route waypoint (unidentified)")',
    "\U0001F600(x)", 'participants(event "Battle of Badr", as: leader, as: any)', 'participants(as: leader, event "Battle of Badr")',
    "path(1, 2)", "events(at: 5 AH)", "events(from: 1234567 AH)", 'people(at: place "Badr" from: 1 AH)',
    'events(at: place "al-Madīna", to: 3 AH)', 'events(at: place "al-Madīna", from: 3 AH)',
    'when(person "Ḥamza b. ʿAbd al-Muṭṭalib")', 'where(story "The Battle of Badr")',
    'connected(group "The army of Badr", via: ties)', 'connected(person "Bilāl b. Rabāḥ", via: events)',
    'between(person "Bilāl b. Rabāḥ", place "Makkah")', 'reviewed(when(event "Battle of Badr"))',
]

AWKWARD = [
    "ʿAbd Allāh", "Abdallah", "Ubayd Allah", "Abd-ul-Rahman", "Mecca", "Makkah", "Medina",
    "المدينة", "أُحُد", "الــمدينة",
    "The Prophet ﷺ", "Abu Bakr (RA)", "Muhammad (pbuh)", "a b c", "zero​width",
    "İstanbul", "Straße", "Æsir", "\U0001F600 smile", "Sa’d", "Sa`d", "Sa'd", "Ja'far's",
    "Abū ʿUbayda b. al-Jarrāḥ", "al-Najashi (Aṣḥama), Negus of Abyssinia",
    "Ḥudaybiyya – the treaty", "“quoted”", "  spaced  out  ", "", "ﷺ",
]


def make_questions(eng) -> list[str]:
    E = eng.E
    persons = [e for e in E if e["k"] == "person"][::5]
    places = [e for e in E if e["k"] == "place"]
    events = [e for e in E if e["k"] == "event"][::2]
    stories = [e for e in E if e["k"] == "story"][::4]
    groups = [e for e in E if e["k"] == "group"][::3]
    qs = [c["question"] for c in golden()]
    for e in persons:
        qs += [f"Relatives of {e['n']}", f"Which stories mention {e['l']}?", f"Who is connected to {e['n']}?",
               f"Tell me about {e['l']}", f"When did {e['n']} die?", f"What events was {e['n']} part of?"]
    for e in places:
        qs += [f"What happened at {e['l']}?", f"Who was at {e['n']}?", f"Events in {e['l']} between 1 and 10 AH"]
    for e in events:
        qs += [f"Who took part in {e['l']}?", f"When was {e['n']}?", f"Where did {e['l']} take place?",
               f"Who was absent from {e['l']}?"]
    for e in stories:
        qs.append(f"Who is in the story {e['l']}?")
    for e in groups:
        qs.append(f"Which stories mention {e['l']}?")
    for a, b in zip(persons[::3], persons[1::3]):
        qs.append(f"How is {a['n']} connected to {b['n']}?")
    for a, b in zip(places, places[1:]):
        qs.append(f"Who was at both {a['l']} and {b['l']}?")
    pids = [e["r"].split("/", 1)[1] for e in E if e["k"] == "event"][:3]
    qs += ODD + DSL + [f"participants(event #{p})" for p in pids]
    return qs


@unittest.skipUnless(NODE and have_graph(), "node or build/graph.ttl missing")
class Parity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, str(ASK))
        from ask.build_ask import browser_data, cache_entries, examples_of
        from ask.present import Presenter
        from ask.dsl import year_bounds
        from ask.normalise import name_tokens, text_key
        from ask.translate import answer
        eng, T = engine(), i18n()
        examples = examples_of(cache_entries())
        cls.questions = make_questions(eng)
        cls.names = sorted({e["l"] for e in eng.E} | {e["n"] for e in eng.E}) + AWKWARD
        cls.years = [[n, "ah"] for n in (1, 2, 3, 5, 6, 10, 11, 29, 30, 31, 100, 1446, 1500)] + [[n, "ce"] for n in (500, 622, 2100)]
        pres = Presenter(eng, T, BASE, examples)
        cls.py_answers = []
        for q in cls.questions:
            a = answer(q, eng, T)
            cls.py_answers.append({"answer": json.loads(json.dumps(a)), "html": pres.render(a)})
        cls.py_tokens = [name_tokens(s) for s in cls.names]
        cls.py_keys = [text_key(s) for s in cls.names]
        cls.py_bounds = [list(year_bounds(n, era)) for n, era in cls.years]
        with tempfile.TemporaryDirectory() as d:
            data, inp = Path(d) / "data.json", Path(d) / "input.json"
            data.write_text(json.dumps(browser_data(eng.ix, T, examples), ensure_ascii=False), encoding="utf-8")
            inp.write_text(json.dumps({"questions": cls.questions, "names": cls.names, "years": cls.years, "base": BASE},
                                      ensure_ascii=False), encoding="utf-8")
            run = subprocess.run([NODE, str(RUNNER), str(data), str(inp)], capture_output=True, text=True, timeout=300)
        if run.returncode != 0:
            raise RuntimeError(run.stderr[-2000:])
        cls.js = json.loads(run.stdout)

    def test_enough_questions(self):
        self.assertGreater(len(self.questions), 500)
        outcomes = {a["answer"]["outcome"] for a in self.py_answers}
        self.assertTrue({"answer", "refusal", "unsupported", "ambiguous", "not_found", "invalid", "empty", "too_long"} <= outcomes)

    def test_same_answers(self):
        bad = []
        for q, py, js in zip(self.questions, self.py_answers, self.js["answers"]):
            if "error" in js:
                bad.append((q, js["error"][:300]))
            elif py["answer"] != js["answer"]:
                bad.append((q, "answer differs"))
        self.assertEqual(bad[:5], [])

    def test_same_html(self):
        bad = []
        for q, py, js in zip(self.questions, self.py_answers, self.js["answers"]):
            if js.get("html") != py["html"]:
                h1, h2 = py["html"], js.get("html") or ""
                k = next((i for i in range(min(len(h1), len(h2))) if h1[i] != h2[i]), min(len(h1), len(h2)))
                bad.append((q, h1[max(0, k - 60):k + 60], h2[max(0, k - 60):k + 60]))
        self.assertEqual(bad[:3], [])

    def test_same_normaliser(self):
        self.assertEqual([(s, t) for s, t, j in zip(self.names, self.py_keys, self.js["keys"]) if t != j][:5], [])
        self.assertEqual([(s, t) for s, t, j in zip(self.names, self.py_tokens, self.js["tokens"]) if t != j][:5], [])

    def test_same_calendar(self):
        self.assertEqual(self.py_bounds, self.js["bounds"])


if __name__ == "__main__":
    unittest.main()
