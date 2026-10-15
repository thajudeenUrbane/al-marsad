"""
Tests for the review pages (slice 3b): review/build_pages.py and what it writes.

    .venv/bin/python -m unittest discover -s review/tests

The pages are built into a temporary folder from a queue built on the repository's corpus
(read only; identity questions included so their cards are built too). Nothing is
picked by a hard-coded ID. The browser behaviour and the round trip into the importer are
checked by review/check_pages.py (Playwright), a separate step of scripts/check_all.sh.
"""

import ast
import csv
import html
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEW = HERE.parent
ROOT = REVIEW.parent
sys.path.insert(0, str(REVIEW))
sys.path.insert(0, str(ROOT / "site"))
import build_pages as bp  # noqa: E402
import build_queue  # noqa: E402
import common as c  # noqa: E402
import check_budget  # noqa: E402  (site/)
import check_html  # noqa: E402  (site/)

KEY = re.compile(r"^[a-z_]+(\.[a-z0-9_]+)+$")
SOURCES = [REVIEW / "build_pages.py", REVIEW / "check_pages.py", REVIEW / "check_pages.cjs", REVIEW / "i18n" / "en.json",
           *sorted((REVIEW / "static").glob("*")), *sorted((REVIEW / "templates").glob("*"))]


def built(out: Path, queue: dict, **kw) -> dict:
    bp.build(queue, out, **kw)
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(out.glob("*.html"))}


class ReviewPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="marsad-review-pages-test-"))
        cls.tree = c.Tree(ROOT / "ontology")
        cls.queue = build_queue.build(cls.tree, {"needs-review", "probable"}, 50)
        cls.pages = built(cls.tmp / "a", cls.queue)
        cls.batches = cls.queue["claims"] + cls.queue["identity"]
        cls.units = [u for b in cls.batches for u in b["units"]]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def cards(self, text):
        return re.findall(r'<li class="card" id="c(\d+)"[^>]*data-target="([^"]+)" data-kind="(\w+)" data-cite="([01])"', text)

    # ---- content -------------------------------------------------------------------------------
    def test_one_page_per_batch_and_every_unit_once(self):
        self.assertTrue(self.queue["identity"], "the test queue has identity questions")
        self.assertEqual(set(self.pages), {bp.page_file(b["batch"]) for b in self.batches} | {"index.html"})
        targets = [t for name, text in self.pages.items() for _, t, _, _ in self.cards(text)]
        self.assertEqual(len(targets), len(set(targets)))
        self.assertEqual(sorted(targets), sorted(u["id"] for u in self.units))
        index = self.pages["index.html"]
        for b in self.batches:
            self.assertIn(f'href="{bp.page_file(b["batch"])}"', index)

    def test_citation_flag_and_kind_follow_the_queue(self):
        flag = {u["id"]: ("1" if u.get("citation_required_to_accept") else "0", u["kind"]) for u in self.units}
        for name, text in self.pages.items():
            for _, target, kind, cite in self.cards(text):
                self.assertEqual((cite, kind), flag[target], target)
        self.assertGreater(sum(1 for v in flag.values() if v[0] == "1"), 0)

    def test_claim_and_basis_shown_verbatim(self):
        for b in self.queue["claims"]:
            text = html.unescape(self.pages[bp.page_file(b["batch"])])
            for u in b["units"]:
                self.assertIn(u["claim"], text)
                if u["basis"].get("text"):
                    self.assertIn(u["basis"]["text"], text)
                if u.get("source_wording"):
                    self.assertIn(u["source_wording"], text)

    def test_arabic_beside_the_english_where_the_graph_has_it(self):
        found = 0
        for b in self.batches:
            text = self.pages[bp.page_file(b["batch"])]
            arabic = [e["name_ar"] for u in b["units"] if u["kind"] == "claim" for e in (u["subject"], u["object"]) if e.get("name_ar")]
            arabic += [u["name_ar"] for u in b["units"] if u["kind"] == "identity" and u.get("name_ar")]
            arabic += [u["basis"]["matn_ar"] for u in b["units"] if u["kind"] == "claim" and u["basis"].get("matn_ar")]
            for u in b["units"]:
                for pid in (u.get("basis") or {}).get("passages", []):
                    if self.queue["passages"].get(pid, {}).get("text_ar"):
                        arabic.append(self.queue["passages"][pid]["text_ar"])
            for a in arabic:
                found += 1
                self.assertRegex(text, r'lang="ar" dir="rtl">(<p>)?' + re.escape(html.escape(a)), a)
        self.assertGreater(found, 0, "the corpus has some Arabic, and it is shown")

    def test_story_page_shows_the_story_and_its_ai_warning(self):
        b = next(b for b in self.queue["claims"] if b["kind"] == "story")
        text = self.pages[bp.page_file(b["batch"])]
        p = self.queue["passages"][b["passage"]]
        self.assertIn('id="story"', text)
        self.assertIn(html.escape(p["text"]), text)
        self.assertIn(bp.t("batch.passage.ai"), text)
        self.assertIn(bp.t("card.ai"), text)

    def test_controls_written_once_and_cloned(self):
        text = self.pages[bp.page_file(self.queue["claims"][0]["batch"])]
        self.assertEqual(text.count('id="decide-tpl"'), 1)
        self.assertEqual(text.count('value="accept"'), 1)
        for k in self.queue["checks"]:
            self.assertIn(f'value="{k}"', text)

    def test_reviewer_names_and_ids_never_in_pages(self):
        with (HERE / "roster.test.csv").open(encoding="utf-8") as fh:
            names = [r["name"] for r in csv.DictReader(fh)]
        for name, text in self.pages.items():
            self.assertNotRegex(text, r"agt:[0-9A-Za-z]{22}", name)
            for n in names:
                self.assertNotIn(n, text, name)
        src = (REVIEW / "build_pages.py").read_text(encoding="utf-8")
        self.assertFalse("load_roster" in src or "roster.csv" in src, "build_pages.py must not read the roster")

    def test_lens_is_declared_default(self):
        index = html.unescape(self.pages["index.html"])
        self.assertIn(self.queue["tradition"]["label"], index)
        self.assertIn("declared default", index)

    def test_scope_filter_keeps_only_what_the_scope_covers(self):
        stem = sorted(self.tree.sources())[0]
        grants = c.parse_scope(f"source:{stem}", self.tree.topics(), self.tree.sources())
        pages = built(self.tmp / "scoped", self.queue, scope_text=f"source:{stem}", grants=grants)
        files = {u["id"]: u for u in self.units}
        targets = [t for text in pages.values() for _, t, _, _ in self.cards(text)]
        self.assertTrue(targets)
        for t in targets:
            u = files[t]
            self.assertIn(stem, [u["file"].rsplit(".ttl", 1)[0]] if u["kind"] == "claim" else u["files"])

    def test_build_is_deterministic(self):
        again = built(self.tmp / "b", self.queue)
        self.assertEqual(again, self.pages)

    # ---- weight, HTML, no external loads (the site's own checkers) --------------------------
    def test_budget_and_no_external_loads(self):
        results, problems = check_budget.check(self.tmp / "a")
        self.assertEqual(problems, [])
        self.assertLess(max(r[0] for r in results), 150_000, "a batch page stays small")

    def test_html_well_formed_and_accessible(self):
        root = self.tmp / "a"
        ids = check_html.collect_ids(root)
        errors = [e for p in sorted(root.glob("*.html")) for e in check_html.check_page(root, p, ids)]
        self.assertEqual(errors, [])

    # ---- i18n, logical CSS, no hard-coded words or IDs ---------------------------------------
    def used_keys(self) -> set:
        strings = bp.STRINGS
        used = set(bp.js_keys((REVIEW / "static" / "review.js").read_text(encoding="utf-8")))
        for path in (REVIEW / "templates").glob("*.html"):
            used |= set(re.findall(r"\[\[([a-z0-9_.]+)\]\]", path.read_text(encoding="utf-8")))
        tree = ast.parse((REVIEW / "build_pages.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str) and KEY.match(node.value)
                    and not re.search(r"\.(json|html|css|py|js|cjs|csv|ttl)$", node.value)):
                used |= {node.value, f"{node.value}.one", f"{node.value}.other"} & set(strings) or {node.value}
        families = {"check.": self.queue["checks"], "decision.": list(c.OUTCOMES), "status.": list(c.OUTCOME_STATUS.values()) + ["proposed", "superseded"],
                    "index.section.": bp.KINDS, "index.lead.": bp.KINDS, "batch.title.": bp.KINDS,
                    "identity.question.": list(bp.ENTITY_KINDS) + ["other"]}
        for prefix, values in families.items():
            used |= {prefix + v for v in values}
        return used

    def test_every_used_key_exists_and_none_unused(self):
        used, have = self.used_keys(), set(bp.STRINGS)
        unknown = sorted(k for k in used if k not in have and k.split(".")[0] in {x.split(".")[0] for x in have}
                         and not any(h.startswith(k + ".") for h in have))
        self.assertEqual(unknown, [], "keys used but missing from review/i18n/en.json")
        self.assertEqual(sorted(have - used), [], "keys in review/i18n/en.json that nothing uses")

    def test_templates_contain_no_hard_coded_text(self):
        for path in sorted((REVIEW / "templates").glob("*.html")):
            src = path.read_text(encoding="utf-8")
            src = re.sub(r"\[\[[a-z0-9_.]+\]\]", "", src)
            src = re.sub(r"\$\{?\w+\}?", "", src)
            src = re.sub(r"<[^>]+>", "", src)
            self.assertEqual(src.strip(), "", f"{path.name} has literal text outside i18n keys")

    def test_html_built_in_python_has_no_hard_coded_words(self):
        tree = ast.parse((REVIEW / "build_pages.py").read_text(encoding="utf-8"))
        inner = {id(v) for n in ast.walk(tree) if isinstance(n, ast.JoinedStr) for v in n.values}
        inner |= {id(n.body[0].value) for n in ast.walk(tree)  # docstrings are not HTML
                  if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr)}
        bad = []
        for node in ast.walk(tree):
            if id(node) in inner:
                continue
            s = None
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                s = node.value
            elif isinstance(node, ast.JoinedStr):
                s = "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in node.values)
            if not s or "<" not in s:
                continue
            text = re.sub(r"<[^>]+>", " ", s)
            text = re.sub(r"\{[^}]*\}|&\w+;", " ", text)
            if re.findall(r"[A-Za-z]{2,}", text):
                bad.append((node.lineno, s[:60]))
        self.assertEqual(bad, [])

    def test_script_has_no_visible_english(self):
        js = (REVIEW / "static" / "review.js").read_text(encoding="utf-8")
        self.assertNotIn("</script", js.lower(), "review.js is inlined in a script element")
        js = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        # sentences: a capitalised word followed by another, or three words or more; CSS selectors aside
        words = [s for s in re.findall(r'"((?:[^"\\]|\\.)*)"', js)
                 if not re.search(r"[#\[=,]|^\.", s)
                 and (re.search(r"\b[A-Z][a-z]+ [A-Za-z]+", s) or re.search(r"[A-Za-z]+ [A-Za-z]+ [A-Za-z]+", s))]
        self.assertEqual(words, [], "visible text in review.js must come from #rv-strings")

    def test_css_uses_logical_properties_only(self):
        css = re.sub(r"/\*.*?\*/", "", (REVIEW / "static" / "review.css").read_text(encoding="utf-8"), flags=re.S)
        self.assertEqual(re.findall(r"[^\n]*\b(?:left|right)\b[^\n]*", css, flags=re.I), [])

    def test_no_entity_id_or_model_name_in_the_sources(self):
        payloads = set()
        for row in self.tree.identity:
            for v in [row["canonical_id"], *row.get("variant_ids", "").split(";")]:
                if ":" in v:
                    payloads.add(v.split(":", 1)[1])
        text = "".join(p.read_text(encoding="utf-8") for p in SOURCES)
        self.assertEqual(sorted(p for p in payloads if p and p in text + Path(__file__).read_text(encoding="utf-8")), [])
        found = re.search(r"\b(claude|anthropic|openai|gpt-?\d|gemini|llama|opus|sonnet|haiku)\b", text, re.I)
        self.assertIsNone(found, "a model or vendor name in the review sources")


if __name__ == "__main__":
    unittest.main()
