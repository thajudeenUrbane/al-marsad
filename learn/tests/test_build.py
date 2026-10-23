"""The learn pages: built output at three depths, budgets, i18n, logical CSS, JS-free reading.

The built-site tests need build/graph.ttl (run ontology/build_graph.py first) and are
skipped without it; they state invariants, never corpus counts. The fixture tests use
made-up graphs (fixtures.py) and carry the exact expectations.
Run:  .venv/bin/python -m unittest discover -s learn/tests -v
"""
import ast
import contextlib
import filecmp
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock

LEARN = Path(__file__).resolve().parents[1]
ROOT = LEARN.parent
SITE = ROOT / "site"
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(LEARN))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build as site_build  # noqa: E402
import build_learn  # noqa: E402
import check_budget  # noqa: E402
import check_html  # noqa: E402
import golden  # noqa: E402
import journey_export as X  # noqa: E402
import journeys as J  # noqa: E402
import practice  # noqa: E402
import render_learn  # noqa: E402
from fixtures import (GLOSS, NOTE, SOFTWARE_AGENT, Fx, big_people_graph, events_spec, people_spec,  # noqa: E402
                      side_fixture, status_fixture)
from model import Site  # noqa: E402

GRAPH = ROOT / "build" / "graph.ttl"
EN = json.loads((LEARN / "i18n" / "en.json").read_text(encoding="utf-8"))
SITE_EN = json.loads((SITE / "i18n" / "en.json").read_text(encoding="utf-8"))
SITE_AR = json.loads((SITE / "i18n" / "ar.json").read_text(encoding="utf-8"))
PY_FILES = sorted(LEARN.glob("*.py"))
KEY = re.compile(r"^[a-z_]+(\.[a-z0-9_]+)+$")
SMALL = 30_000        # the small step and part budget of the split builds (design §14)
AI_LABEL = EN["learn.source.ai_document"].replace("{source}", "")
# The keys a Discover render may read (design §8 "Shows"): the shared frame, titles and
# leads, the rule in plain words, the facts line, the computed reasons, narration with its
# sources, the no-work and more lines, prompts, next directions, group and set-apart
# headings, and the index. A new key at Discover is a decision: add it here on purpose.
DISCOVER_ALLOWED_KEYS = {
    "claim.source", "common.not_recorded", "fact.story_number", "site.name", "title.sep",
    "learn.ai_source_note", "learn.apart.heading", "learn.apart.lead_discover", "learn.contents.heading",
    "learn.depths.label", "learn.door.discover", "learn.facts.when", "learn.facts.where", "learn.group.against",
    "learn.group.against_lead", "learn.nav", "learn.quote", "learn.source.ai_document", "learn.step_no",
    "learn.steps.heading", "learn.title.depth", "learn.why.named", "learn.why.part",
    "learn.order.prophet_first_then_name", "learn.order.name", "learn.order.recorded_discover", "learn.order.story",
    "learn.order.e3", "learn.order.e3_sources", "learn.order.e3_links", "learn.order.e3_no_last"}
DISCOVER_ALLOWED_PREFIXES = ("footer.", "nav.", "type.", "learn.depth.", "learn.discover.no_work.", "learn.follow.",
                             "learn.index.", "learn.kinds.", "learn.list.", "learn.narr.", "learn.next.",
                             "learn.progress.", "learn.prompt.", "learn.rule.", "learn.scale.")
DISCOVER_TITLE = re.compile(r"journey\.[a-z0-9_]+\.(?:title|lead)")


def discover_allowed(key: str) -> bool:
    return (key in DISCOVER_ALLOWED_KEYS or key.startswith(DISCOVER_ALLOWED_PREFIXES)
            or bool(DISCOVER_TITLE.fullmatch(key))) and not render_learn.forbidden_at_discover(key)


def quiet(fn, *args, **kw):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kw)


def family_keys() -> set:
    """Keys the code builds from parts, listed here so that none can go missing or stale."""
    keys = set()
    for k in ("named", "part", "part_of", "has_part", "date_after", "date_before", "date_related", "dated_after_this",
              "dated_before_this", "dated_related_this", "event_claim"):
        keys.add(f"learn.why.{k}")
    keys |= {f"learn.order_note.{k}" for k in ("part", "recorded", "unrecorded")}
    keys |= {f"learn.order.{o}" for orders in J.ORDERS.values() for o in orders}
    keys |= {f"learn.follow.{f}" for f in J.FOLLOW}
    keys |= {f"learn.list.{n}_{w}" for n in ("two", "many") for w in ("or", "and")}
    keys |= {"learn.kinds.event", "learn.kinds.story", "learn.kinds.event_story"}
    keys |= {f"learn.legend.{t}" for t in J.STEP_TYPES}
    keys |= {f"learn.door.{d}" for d in J.DOORS}
    for t in practice.QUESTION_TYPES:
        for p in practice.PARTICIPATION:
            keys.add(f"learn.q.{t}.{practice.local(p)}")
    plural = ["learn.scale.events", "learn.scale.people", "learn.scale.stories", "learn.scale.apart",
              "learn.claims.assertions", "learn.claims.links", "learn.claims.show", "learn.records.heading",
              "learn.contrary.heading", "learn.named.summary", "learn.named.show", "learn.index.steps",
              "learn.index.practice_count", "learn.rule.events_follow", "learn.rule.people_follow",
              "learn.claims.more", "learn.narr.more", "learn.discover.no_work"]
    for k in plural:
        keys |= {f"{k}.one", f"{k}.other"}
    for path in sorted((LEARN / "journeys").glob("*.json")):
        spec = json.loads(path.read_text(encoding="utf-8"))
        keys |= {spec[k] for k in ("title", "lead", "lead_study") if k in spec}
    return keys


def literal_keys() -> set:
    found = set()
    namespaces = {k.split(".")[0] for k in list(EN) + list(SITE_EN)}
    for path in PY_FILES:
        tree_ = ast.parse(path.read_text(encoding="utf-8"))
        inner = {id(v) for n in ast.walk(tree_) if isinstance(n, ast.JoinedStr) for v in n.values}
        for node in ast.walk(tree_):
            if id(node) in inner:
                continue  # a fragment of an f-string builds a key family, listed in family_keys()
            if (isinstance(node, ast.Constant) and isinstance(node.value, str) and KEY.match(node.value)
                    and node.value.split(".")[0] in namespaces
                    and not re.search(r"\.(json|html|css|py|ttl|cjs|js)$", node.value)):
                found.add(node.value)
    for path in (LEARN / "templates").glob("*.html"):
        found |= set(re.findall(r"\[\[([a-z0-9_.]+)\]\]", path.read_text(encoding="utf-8")))
    return found


class StaticChecks(unittest.TestCase):
    def test_the_scans_see_every_learn_module(self):
        names = {p.name for p in PY_FILES}
        for module in ("journeys.py", "journey_lists.py", "journey_export.py", "render_learn.py", "build_learn.py",
                       "practice.py"):
            self.assertIn(module, names)

    def test_every_key_used_exists(self):
        missing = [k for k in sorted(literal_keys() | family_keys()) if k not in EN and k not in SITE_EN
                   and f"{k}.one" not in EN]
        self.assertEqual(missing, [])

    def test_no_unused_learn_keys(self):
        used = literal_keys() | family_keys()
        unused = [k for k in EN if k not in used and not any(k.startswith(u + ".") for u in used)]
        self.assertEqual(unused, [])

    def test_learn_keys_do_not_shadow_site_keys(self):
        self.assertEqual(sorted(set(EN) & set(SITE_EN)), [])

    def test_templates_contain_no_hard_coded_text(self):
        for path in sorted((LEARN / "templates").glob("*.html")):
            src = path.read_text(encoding="utf-8")
            src = re.sub(r"\[\[[a-z0-9_.]+\]\]", "", src)
            src = re.sub(r"\$\{?\w+\}?", "", src)
            src = re.sub(r"<[^>]+>", "", src)
            self.assertEqual(src.strip(), "", f"{path.name} has literal text outside i18n keys")

    def test_html_built_in_python_has_no_hard_coded_words(self):
        bad = []
        for path in PY_FILES:
            tree_ = ast.parse(path.read_text(encoding="utf-8"))

            def flatten(node):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    return node.value
                if isinstance(node, ast.JoinedStr):
                    return "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in node.values)
                return None

            inner = {id(v) for n in ast.walk(tree_) if isinstance(n, ast.JoinedStr) for v in n.values}
            for node in ast.walk(tree_):
                if id(node) in inner:
                    continue
                if isinstance(node, ast.JoinedStr) or (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                    s = flatten(node)
                    if not s or "<" not in s:
                        continue
                    text = re.sub(r"<[^>]+>", " ", s)
                    text = re.sub(r"\{[^}]*\}|&\w+;", " ", text)
                    words = re.findall(r"[A-Za-z]{2,}", text)
                    if words:
                        bad.append((path.name, node.lineno, words))
        self.assertEqual(bad, [])

    def test_css_uses_logical_properties_only(self):
        css = re.sub(r"/\*.*?\*/", "", (LEARN / "static" / "learn.css").read_text(encoding="utf-8"), flags=re.S)
        self.assertEqual(re.findall(r"[^\n]*\b(?:left|right|top|bottom)\b[^\n]*", css, flags=re.I), [])

    def test_script_holds_no_interface_text_and_guards_storage(self):
        js = (LEARN / "static" / "learn.js").read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        literals = re.findall(r'"((?:[^"\\]|\\.)*)"', code)
        phrases = [s for s in literals if re.search(r"[A-Za-z]+\s+[A-Za-z]+", s) and s != "use strict"]
        self.assertEqual(phrases, [])
        self.assertIn("try", code)
        # every storage call sits inside a function whose body is wrapped in try/catch
        for fn in ("storage", "load", "save"):
            body = re.search(r"function " + fn + r"\([^)]*\) \{(.*?)\n  \}", code, flags=re.S).group(1)
            self.assertIn("try {", body)
            self.assertIn("catch (e)", body)
        self.assertNotIn("localStorage", code.replace("window.localStorage", ""))
        self.assertIn('"al-marsad.learn.progress.v1"', code)        # the key E1 progress lives under (design §9)
        for attr_ in ("data-steps", "data-total"):                   # progress counts the whole journey
            self.assertIn(f'"{attr_}"', code)

    def test_progress_markup_is_hidden_until_the_script_runs(self):
        src = (LEARN / "templates" / "progress.html").read_text(encoding="utf-8")
        self.assertRegex(src, r"<div class=\"learn-progress\"[^>]* hidden>")
        self.assertIn("<template id=\"learn-step-done\">", src)


class GoldenRecipe(unittest.TestCase):
    """golden.held_page takes out exactly the additions a held Study page may carry
    (design §3.7 and §8), so the E1 hash recorded on the v1 page still applies to it, and
    golden.e1_gate gates the E1 check on the graph, never on what learn computes."""

    V1 = ('<article class="journey door-study" data-journey="x">\n<header class="journey-head">\n<h1>T</h1>\n'
          '</header>\n<nav class="breadcrumb"><ol><li><a href="../../">H</a></li></ol></nav>\n'
          '<ol class="journey-steps">\n<li class="step" id="step-1" data-step="p1" aria-labelledby="step-1-title">\n'
          '<h3 class="step-title" id="step-1-title"><a href="../../event/p1/">N</a></h3>\n</li>\n</ol>\n</article>')

    def held(self) -> str:
        v2 = self.V1.replace('data-journey="x">', 'data-journey="x" data-depth="study" data-total="1" data-steps="p1">')
        v2 = v2.replace('<header class="journey-head">\n',
                        '<header class="journey-head">\n<nav class="journey-depths" aria-label="D"><ul><li>'
                        '<a href="discover/#s-p1">D</a></li><li><a href="./#s-p1" aria-current="page">S</a></li>'
                        '</ul></nav>\n')
        v2 = v2.replace('aria-labelledby="step-1-title">\n', 'aria-labelledby="step-1-title">\n<span id="s-p1"></span>\n')
        return v2.replace('href="../../event/p1/"', 'href="../../../event/p1/"')

    def test_the_permitted_additions_are_neutralised(self):
        v2 = self.held()
        self.assertNotEqual(golden.page_sha(v2), golden.page_sha(self.V1))
        self.assertEqual(golden.page_sha(golden.held_page(v2)), golden.page_sha(self.V1))

    def test_the_e1_check_is_gated_on_the_graph_not_on_what_learn_computes(self):
        """golden.e1_gate: on the golden graph a changed content_sha, content facts or page is
        a failure, never a skip; only another graph fingerprint skips."""
        want = json.loads(golden.E1_FILE.read_text(encoding="utf-8"))
        fp, sha, page, facts = want["graph"]["fingerprint"], want["content_sha"], want["page_sha256"], want["content_v1_gate"]
        self.assertEqual(golden.e1_gate(want, fp, sha, page, facts), (True, []))
        for name, args in (("content_sha", ("0" * 12, page, facts)), ("page_sha256", (sha, "0" * 64, facts)),
                           ("content_v1_gate", (sha, page, dict(facts, claims=facts["claims"] - 1)))):
            with self.subTest(name):
                checked, problems = golden.e1_gate(want, fp, *args)
                self.assertTrue(checked)
                self.assertEqual([p.split(":")[0] for p in problems], [name])
        checked, problems = golden.e1_gate(want, "f" * 12, "0" * 12, "0" * 64, {})
        self.assertFalse(checked)
        self.assertTrue(problems[0].startswith("re-verify E1"))

    def test_a_page_without_them_is_unchanged(self):
        self.assertEqual(golden.held_page(self.V1), self.V1)

    def test_nothing_else_is_taken_out(self):
        for extra in ('<span data-id="s-p1"></span>', '<span id="s-p1">text</span>', '<p data-depth="study">x</p>',
                      '<nav class="journey-contents"><a href="#s-p1">C</a></nav>'):
            page = self.held().replace("<h1>T</h1>", "<h1>T</h1>" + extra)
            with self.subTest(extra):
                self.assertIn(extra, golden.held_page(page))


# --------------------------------------------------------------------------- reading built pages
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.children, self.parent = tag, dict(attrs), [], parent

    @property
    def classes(self) -> set:
        return set((self.attrs.get("class") or "").split())

    def text(self) -> str:
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def walk(self):
        yield self
        for c in self.children:
            if not isinstance(c, str):
                yield from c.walk()

    def find(self, tag=None, cls=None) -> list:
        return [n for n in self.walk() if (tag is None or n.tag == tag) and (cls is None or cls in n.classes)]


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = self.cur = Node("#root", [], None)

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


_TREES: dict[str, Node] = {}


def tree(src: str) -> Node:
    """The parsed page (cached: the tests read the same pages many times)."""
    key = hashlib.sha256(src.encode("utf-8")).hexdigest()
    if key not in _TREES:
        p = _Tree()
        p.feed(src)
        p.close()
        _TREES[key] = p.root
    return _TREES[key]


_FILES: dict[tuple, str] = {}


def read_page(path: Path) -> str:
    st = path.stat()
    key = (str(path), st.st_mtime_ns, st.st_size)
    if key not in _FILES:
        _FILES[key] = path.read_text(encoding="utf-8")
    return _FILES[key]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


_READER: dict[Path, tempfile.TemporaryDirectory] = {}


def reader_site(graph: Path = GRAPH) -> Path:
    """The reader-tier site of the page graph, built once per test process (learn only adds
    learn/ to it; a fixture graph builds its own site in build_into)."""
    if graph not in _READER:
        _READER[graph] = tempfile.TemporaryDirectory(prefix="learn-reader-")
        quiet(site_build.build, graph, Path(_READER[graph].name), True)
    return Path(_READER[graph].name)


def build_into(out: Path, graph: Path = GRAPH, journeys_dir: Path | None = None, **kw) -> dict:
    if graph == GRAPH:
        shutil.copytree(reader_site(graph), out, dirs_exist_ok=True)
    else:
        quiet(site_build.build, graph, out, True)
    return quiet(build_learn.build, graph, out, True, journeys_dir, **kw)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def export_of(out: Path) -> dict:
    """The built export: index, pages, and per journey its head with every part and
    research file joined (steps in order, the tables merged, the glosses)."""
    data = out / "learn" / "data"
    index = load_json(data / "index.json")
    docs = {}
    for e in index["journeys"]:
        head = load_json(data / e["file"])
        doc = {"head": head, "steps": [], "claims": {}, "passages": {}, "entities": {}, "terms": {}, "glosses": {}}
        for name in head["parts"]:
            part = load_json(data / "journeys" / e["slug"] / name)
            doc["steps"] += part["steps"]
            for k in ("claims", "passages", "entities", "terms"):
                doc[k].update(part[k])
        for name in head["research"]:
            doc["glosses"].update(load_json(data / "journeys" / e["slug"] / name)["glosses"])
        doc["by_key"] = {s["key"]: s for s in doc["steps"]}
        docs[e["slug"]] = doc
    return {"index": index, "pages": load_json(data / "pages.json")["pages"], "journeys": docs}


def journey_pages(out: Path, exp: dict, slug: str | None = None, depth: str | None = None) -> list:
    """[(pages.json entry, HTML)] of the journey pages, each depth's pages in order."""
    rows = [e for e in exp["pages"] if e["kind"] == "journey" and slug in (None, e["journey"]) and depth in (None, e["depth"])]
    rows.sort(key=lambda e: (e["journey"], X.DEPTHS.index(e["depth"]), e["page"]))
    return [(e, read_page(out / e["file"])) for e in rows]


_KEYS: dict[int, tuple] = {}


def page_keys(root: Node) -> tuple[list, list]:
    """The step keys (li.step data-step) and set-apart keys (li.apart anchors) on a page, in
    order (cached per parsed page, which the cache keeps alive, so its id stays its own)."""
    if id(root) not in _KEYS:
        steps = [n.attrs["data-step"] for n in root.find("li", "step")]
        apart = []
        for li in root.find("li", "apart"):
            spans = [n.attrs["id"][2:] for n in li.find("span") if n.attrs.get("id", "").startswith("s-")]
            apart += spans[:1]
        _KEYS[id(root)] = (root, tuple(steps), tuple(apart))
    _, steps, apart = _KEYS[id(root)]
    return list(steps), list(apart)


def graph_data(doc: dict) -> set:
    """Every graph datum a journey's export holds: entity names and labels, term labels,
    literals as written, dates as shown, part titles and works."""
    out = set()
    for e in doc["entities"].values():
        out |= {e.get("name"), e.get("scholarly"), e.get("part_label"), e.get("work")}
        out |= {(d.get("text") or {}).get("en") for d in e.get("dates") or []}
    out |= {t.get("en") for t in doc["terms"].values()}
    out |= {(c.get("text") or {}).get("value") for c in doc["claims"].values()}
    out |= {p.get("work") for p in doc["passages"].values()}
    out |= set(doc["head"].get("ai_documents") or []) | set(doc["head"].get("part_labels") or [])
    return {norm(x) for x in out if x}


def review_language(root: Node, data: set) -> list:
    """Review words in a page's text outside a, .term and .data, and in any such exempt
    element whose text is not a graph datum (design §8, enforcement 3)."""
    found = []

    def walk(node: Node, exempt: bool):
        for ch in node.children:
            if isinstance(ch, str):
                if not exempt and J.review_words(ch):
                    found.append(norm(ch))
                continue
            here = ch.tag == "a" or bool({"term", "data"} & ch.classes)
            if here and not exempt:
                text = norm(ch.text())
                if J.review_words(text) and text not in data:
                    found.append(text)
            walk(ch, exempt or here)

    walk(root, False)
    return found


def node_env() -> tuple[str | None, dict]:
    """node, with NODE_PATH from `npm root -g` and PLAYWRIGHT_BROWSERS_PATH as review/check_pages.py finds them."""
    node = shutil.which("node")
    env = dict(os.environ)
    if node and not env.get("NODE_PATH") and shutil.which("npm"):
        env["NODE_PATH"] = subprocess.run([shutil.which("npm"), "root", "-g"], capture_output=True, text=True).stdout.strip()
    if not env.get("PLAYWRIGHT_BROWSERS_PATH") and Path("/opt/pw-browsers").is_dir():
        env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/pw-browsers"
    if node and subprocess.run([node, "-e", 'require.resolve("playwright")'], env=env, capture_output=True).returncode:
        return None, env
    return node, env


def differs(cmp) -> list:
    bad = list(cmp.diff_files) + list(cmp.left_only) + list(cmp.right_only)
    for sub in cmp.subdirs.values():
        bad += differs(sub)
    return bad


class PageChecks:
    """Invariants every built learn site keeps, whatever the graph and the budgets."""
    out: Path
    exp: dict

    def test_the_pages_match_the_manifest(self):
        listed = sorted(e["file"] for e in self.exp["pages"])
        found = sorted(p.relative_to(self.out).as_posix() for p in (self.out / "learn").rglob("index.html"))
        self.assertEqual(listed, found)
        for e in self.exp["pages"]:
            self.assertEqual(e["file"], e["path"] + "index.html")

    def test_reader_pages_follow_the_export(self):
        """At every depth the stops appear once each, in the export's order, numbered across pages."""
        for slug, doc in self.exp["journeys"].items():
            head = doc["head"]
            for depth in X.DEPTHS:
                steps, apart, numbers = [], [], []
                for e, src in journey_pages(self.out, self.exp, slug, depth):
                    root = tree(src)
                    s, a = page_keys(root)
                    steps += s
                    apart += a
                    numbers += [int(n.attrs["id"][5:]) for n in root.find("li", "step")]
                    self.assertEqual(e["first"], (s + a)[0])
                    self.assertEqual(e["last"], (s + a)[-1])
                with self.subTest(slug=slug, depth=depth):
                    self.assertEqual(steps, [x["key"] for x in head["stops"]])
                    self.assertEqual(apart, [x["key"] for x in head["set_apart"]])
                    self.assertEqual(numbers, list(range(1, len(steps) + 1)))

    def test_every_stop_url_names_the_page_that_holds_it(self):
        for slug, doc in self.exp["journeys"].items():
            for stop in doc["head"]["stops"] + doc["head"]["set_apart"]:
                for depth, url in stop["urls"].items():
                    page, frag = url.split("#", 1)
                    root = tree(read_page(self.out / page / "index.html"))
                    s, a = page_keys(root)
                    self.assertIn(stop["key"], s + a, url)
                    self.assertEqual(frag, f"s-{stop['key']}")

    def test_every_step_has_a_stable_pid_anchor(self):
        for e, src in journey_pages(self.out, self.exp):
            root = tree(src)
            for li in root.find("li", "step"):
                spans = [n.attrs.get("id") for n in li.children if not isinstance(n, str) and n.tag == "span"]
                self.assertEqual(spans[:1], [f"s-{li.attrs['data-step']}"], e["path"])

    def test_depth_links_land_on_the_page_holding_the_first_stop(self):
        for e, src in journey_pages(self.out, self.exp):
            root = tree(src)
            nav = root.find("nav", "journey-depths")
            self.assertEqual(len(nav), 1, e["path"])
            links = nav[0].find("a")
            self.assertEqual([a.attrs.get("aria-current") for a in links].count("page"), 1)
            first = (page_keys(root)[0] + page_keys(root)[1])[0]
            here = Path(e["path"])
            for a, depth in zip(links, X.DEPTHS):
                target, frag = a.attrs["href"].split("#", 1)
                self.assertEqual(frag, f"s-{first}")
                path = os.path.normpath(here / target).replace(os.sep, "/") + "/"
                held = tree(read_page(self.out / path / "index.html"))
                self.assertIn(first, sum(page_keys(held), []), f"{e['path']} -> {a.attrs['href']}")
                self.assertEqual(held.find("article")[0].attrs["data-depth"], depth)
                self.assertEqual(a.attrs.get("aria-current") == "page", depth == e["depth"])

    def test_split_depths_have_a_pager_and_page_one_a_contents_list(self):
        for e, src in journey_pages(self.out, self.exp):
            root = tree(src)
            pager, contents = root.find("nav", "journey-pager"), root.find("nav", "journey-contents")
            if e["pages"] == 1:
                self.assertEqual((pager, contents), ([], []), e["path"])
                continue
            self.assertEqual(len(pager[0].find("a")), e["pages"])
            self.assertEqual(len(contents), 1 if e["page"] == 1 else 0, e["path"])
            if e["page"] == 1:
                s, a = page_keys(root)
                doc = self.exp["journeys"][e["journey"]]
                keys = [x["key"] for x in doc["head"]["stops"] + doc["head"]["set_apart"]]
                anchored = {li.attrs["id"][2:] for li in contents[0].find("li") if li.attrs.get("id")}
                self.assertEqual(anchored, set(keys) - set(s + a))

    def test_every_step_links_to_its_entity_page(self):
        for e, src in journey_pages(self.out, self.exp):
            for li in tree(src).find("li", "step"):
                links = li.find("h3")[0].find("a")
                self.assertEqual(len(links), 1)
                target = os.path.normpath(Path(e["path"]) / links[0].attrs["href"]).replace(os.sep, "/")
                kind, pid = target.split("/")[-2:]
                self.assertEqual(pid, li.attrs["data-step"])
                self.assertTrue((self.out / kind / pid / "index.html").is_file(), target)

    def test_evidence_links_reach_the_evidence_section(self):
        seen = 0
        for e, src in journey_pages(self.out, self.exp):
            for href in set(re.findall(r'href="([^"]+)#evidence"', src)):
                path = os.path.normpath(Path(e["path"]) / href).replace(os.sep, "/")
                self.assertIn('id="evidence"', read_page(self.out / path / "index.html"), path)
                seen += 1
        self.assertGreater(seen, 0)

    def test_every_step_keeps_to_its_depth_caps(self):
        """Design §7.1, §8 and §13: a step shows at most NARRATION[depth] narration sentences,
        each prompt's answer at most as many, Discover one prompt, and Study and Research at
        most CLAIM_LIST[depth] claim rows. A held Study page is the v1 page (§3.7) and is
        left out."""
        for e, src in journey_pages(self.out, self.exp):
            depth = e["depth"]
            if depth == "study" and self.exp["journeys"][e["journey"]]["head"]["hold_study"]:
                continue
            cap = render_learn.NARRATION[depth]
            for li in tree(src).find("li", "step"):
                with self.subTest(page=e["path"], step=li.attrs["data-step"]):
                    narration = li.find("ul", "narration")
                    self.assertLessEqual(sum(len(u.find("li", "sentence")) for u in narration), cap)
                    prompts = li.find("details", "prompt")
                    for p in prompts:
                        self.assertLessEqual(len(p.find("li", "sentence")), cap)
                    self.assertLessEqual(len(li.find("li", "sentence")), cap * (1 + len(prompts)))
                    if depth == "discover":
                        self.assertLessEqual(len(prompts), X.DEPTH_POLICY["discover"]["prompts"])
                    else:
                        self.assertLessEqual(len(li.find("li", "claim")), render_learn.CLAIM_LIST[depth])

    def test_study_and_research_pages_show_the_draft_note_and_a_status_on_every_claim(self):
        for e, src in journey_pages(self.out, self.exp):
            if e["depth"] == "discover":
                continue
            root = tree(src)
            with self.subTest(e["path"]):
                self.assertIn(norm(EN["learn.draft_banner"]), norm(root.text()))
                self.assertIn(EN["learn.rule.heading"], src)
                for li in root.find("li", "claim"):
                    self.assertIn("Status:", li.text())

    def test_no_recorded_by_line_is_labelled_a_source(self):
        label = norm(f'{SITE_EN["claim.source"]} {SITE_EN["claim.recorded_by"].split("{")[0]}')
        for e, src in journey_pages(self.out, self.exp):
            self.assertNotIn(label, norm(tree(src).text()), e["path"])

    def test_discover_pages_carry_no_review_language(self):
        for e, src in journey_pages(self.out, self.exp, depth="discover"):
            root = tree(src)
            doc = self.exp["journeys"][e["journey"]]
            with self.subTest(e["path"]):
                for n in root.walk():
                    self.assertNotIn("status", n.classes)
                    self.assertNotIn("claim-id", n.classes)
                    self.assertFalse(any(c.startswith("coverage") for c in n.classes), n.classes)
                self.assertNotIn(norm(EN["learn.draft_banner"]), norm(root.text()))
                self.assertNotIn("Status:", root.text())
                if doc["head"]["lead_study"]:   # a Study and Research text (design §12, §20.1)
                    self.assertNotIn(norm(doc["head"]["lead_study"]["en"]), norm(root.text()))
                self.assertEqual(review_language(root, graph_data(doc)), [])

    def test_discover_sources_are_short_citations_only(self):
        """Every .source on a Discover page is source_line(c, "discover") of an eligible claim
        of a stop on that page (or a reviewed list's source); no basis text or recorded-by
        agent of the journey's claims appears there."""
        t = X.translators()["en"]
        for e, src in journey_pages(self.out, self.exp, depth="discover"):
            doc = self.exp["journeys"][e["journey"]]
            root = tree(src)
            s, a = page_keys(root)
            allowed = {X.source_line(doc["claims"][c], "discover", doc["passages"], t)
                       for key in s + a for item in doc["by_key"][key]["narration"] for c in item["c"]
                       if doc["claims"][c]["discover"]}
            lists = doc["head"].get("lists") or {}
            if lists.get("state") == "reviewed":
                allowed |= {x["text"] for x in lists["sources"] if x.get("text")}
            sources = [norm(n.text()) for n in root.find(cls="source")]
            with self.subTest(e["path"]):
                self.assertEqual(sorted(set(sources) - {norm(x) for x in allowed}), [])
                text = norm(root.text())
                cites = " ".join(p.get("cite") or "" for p in doc["passages"].values())
                for c in doc["claims"].values():
                    if c.get("basis"):
                        self.assertNotIn(norm(c["basis"]), text)
                    for agent in c.get("recorded_by") or []:
                        if agent["label"] not in cites:
                            self.assertNotIn(agent["label"], text)

    def test_every_discover_sentence_has_a_source_line(self):
        for e, src in journey_pages(self.out, self.exp, depth="discover"):
            doc = self.exp["journeys"][e["journey"]]
            ai = {norm(X.source_line(c, "discover", doc["passages"], X.translators()["en"]))
                  for c in doc["claims"].values() if c["discover"] and c.get("ai_document")}
            for li in tree(src).find("li", "sentence"):
                sources = [norm(n.text()) for n in li.find(cls="source")]
                self.assertTrue(sources, e["path"])
                for s in sources:
                    if s in ai:
                        self.assertTrue(s.endswith(norm(AI_LABEL)), s)

    def test_every_page_holding_a_titled_group_step_shows_its_heading_and_lead(self):
        """design §6.4 and §7: a page holding steps of a titled group (the against group)
        shows the group's heading and lead before the first of them, at every depth, also
        on a page that starts inside the group."""
        for e, src in journey_pages(self.out, self.exp):
            doc = self.exp["journeys"][e["journey"]]
            numbers = [int(n) for n in re.findall(r'<li class="step" id="step-(\d+)"', src)]
            for g in doc["head"]["groups"]:
                inside = [n for n in numbers if g["t"] and g["from"] <= n <= g["to"]]
                if not inside:
                    continue
                block = f'<h3 class="group-heading" id="group-{g["key"]}">{render_learn.esc(EN[g["t"]])}</h3>'
                if g["lead"]:
                    block += f'<p class="group-lead">{render_learn.esc(EN[g["lead"]])}</p>'
                with self.subTest(page=e["path"], group=g["key"]):
                    self.assertIn(block, src)
                    self.assertLess(src.index(block), src.index(f'<li class="step" id="step-{inside[0]}"'))

    def test_discover_shows_the_record_behind_a_titled_group(self):
        """G1/G8 and design §6.4: at Discover every step of a titled group (the against
        group) shows in its narration the sentence of one of its own side claims, with that
        claim's short source, so the heading it stands under has its source on the page."""
        t = X.translators()["en"]
        for e, src in journey_pages(self.out, self.exp, depth="discover"):
            doc = self.exp["journeys"][e["journey"]]
            titled = {g["key"] for g in doc["head"]["groups"] if g["t"]}
            for li in tree(src).find("li", "step"):
                step = doc["by_key"][li.attrs["data-step"]]
                if step["group"] not in titled:
                    continue
                wanted = []
                for side in step["side"]:
                    words = [norm(w) for w in re.split(r"\{[^}]*\}", EN[X.NARR_SIDE[side["pk"]]]) if norm(w)]
                    sources = {norm(X.source_line(doc["claims"][c], "discover", doc["passages"], t))
                               for c in side["claims"] if doc["claims"][c]["discover"]}
                    wanted.append((words, sources))
                shown = [(norm(s.text()), {norm(n.text()) for n in s.find(cls="source")})
                         for ul in li.find("ul", "narration") for s in ul.find("li", "sentence")]
                with self.subTest(page=e["path"], step=step["n"]):
                    self.assertTrue(any(got & sources and all(w in text for w in words)
                                        for text, got in shown for words, sources in wanted))

    def test_stops_without_a_cited_claim_show_the_no_work_line(self):
        for e, src in journey_pages(self.out, self.exp, depth="discover"):
            doc = self.exp["journeys"][e["journey"]]
            for li in tree(src).find("li", "step") + tree(src).find("li", "apart"):
                key = li.attrs.get("data-step") or [n.attrs["id"][2:] for n in li.find("span") if n.attrs.get("id")][0]
                step = doc["by_key"][key]
                no_work = li.find(cls="no-work")
                if step["counts"]["discover"] == 0:
                    self.assertEqual(len(no_work), 1, key)
                    self.assertEqual(li.find(cls="source"), [], key)
                    self.assertEqual(norm(no_work[0].text()),
                                     norm(EN["learn.discover.no_work." + ("one" if step["counts"]["records"] == 1 else "other")]
                                          .format(n=step["counts"]["records"])))
                else:
                    self.assertEqual(no_work, [], key)

    def test_research_pages_show_claim_ids_and_the_data_files(self):
        for e, src in journey_pages(self.out, self.exp):
            root = tree(src)
            ids = root.find(cls="claim-id")
            if e["depth"] != "research":
                self.assertEqual(ids, [], e["path"])
                self.assertNotIn(EN["learn.gloss.label"], src)
                continue
            claims = root.find("li", "claim")
            self.assertEqual(len(ids), len(claims), e["path"])
            head = self.exp["journeys"][e["journey"]]["head"]
            for needle in (head["rule_sha"], head["content_sha"], head["graph"]["fingerprint"],
                           f"learn/data/journeys/{e['journey']}/journey.json"):
                self.assertIn(needle, src, e["path"])

    def test_the_site_checks_pass_with_the_learn_pages_in_place(self):
        self.assertEqual(quiet(check_html.main, [str(self.out)]), 0)
        results, problems = check_budget.check(self.out)      # what check_budget.main runs, once
        self.assertTrue(results)
        self.assertEqual(problems, [])
        learn = [r for r in results if r[1].startswith("learn/")]
        self.assertEqual(len(learn), len(self.exp["pages"]))
        self.assertTrue(all(total <= 300_000 for total, *_ in learn))


def step_html_bytes(src: str) -> int:
    """The bytes of a page's step HTML: its step lists and set-apart section."""
    body = src.split('<section class="journey-body"', 1)[1]
    steps = body.split("<ol class=\"journey-steps\"", 1)[1].split("</ol>\n</section>", 1)[0] if "<li class=\"step\"" in body else ""
    apart = re.findall(r'<section class="journey-apart".*?</section>', src, flags=re.S)
    return len(steps.encode("utf-8")) + sum(len(a.encode("utf-8")) for a in apart)


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class BuiltPages(PageChecks, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.summary = build_into(cls.out)
        cls.learn = cls.out / "learn"
        cls.exp = export_of(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def pages(self):
        return sorted(self.learn.rglob("*.html"))

    def test_every_journey_has_three_depths_and_its_door_at_the_root(self):
        self.assertEqual(json.loads((self.learn / "practice" / "bank.json").read_text(encoding="utf-8")),
                         {"questions": []})
        for slug, doc in self.exp["journeys"].items():
            door = doc["head"]["door"]
            self.assertEqual(tree((self.learn / slug / "index.html").read_text(encoding="utf-8"))
                             .find("article")[0].attrs["data-depth"], door)
            for depth in X.DEPTHS:
                if depth != door:
                    self.assertTrue((self.learn / slug / depth / "index.html").is_file())
            self.assertEqual(self.summary["journeys"][slug]["pages"],
                             {d: len(journey_pages(self.out, self.exp, slug, d)) for d in X.DEPTHS})

    def test_ai_generated_material_is_flagged_at_every_depth(self):
        for e, src in journey_pages(self.out, self.exp):
            head = self.exp["journeys"][e["journey"]]["head"]
            if not head["ai_note"]:
                continue
            text = norm(tree(src).text())
            if e["depth"] == "discover":
                self.assertIn(norm(EN["learn.ai_source_note"].split("{work}")[0]), text, e["path"])
                self.assertNotIn(norm(EN["learn.ai_note"]), text)
            else:
                self.assertIn(norm(EN["learn.ai_note"]), text, e["path"])
        fb = (self.learn / "first-believers" / "study" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(fb.count(SITE_EN["story.banner"]), self.summary["journeys"]["first-believers"]["steps"])
        self.assertNotIn(SITE_EN["story.banner"], (self.learn / "first-believers" / "index.html").read_text(encoding="utf-8"))

    def test_discover_set_apart_lines_are_sentences_with_source_and_ai_label(self):
        src = (self.learn / "people-of-badr" / "discover" / "index.html").read_text(encoding="utf-8")
        apart = tree(src).find("section", "journey-apart")
        self.assertEqual(len(apart), 1)
        self.assertIn(EN["learn.apart.lead_discover"], norm(apart[0].text()))
        doc = self.exp["journeys"]["people-of-badr"]
        for li in apart[0].find("li", "apart"):
            sentences = li.find("li", "sentence")
            key = li.find("span")[0].attrs["id"][2:]
            if doc["by_key"][key]["counts"]["discover"] == 0:
                self.assertEqual(sentences, [])
                continue
            for s in sentences:
                self.assertTrue(s.find(cls="source"))
                self.assertIn(EN["learn.narr.marker"].split("{marker}")[0].strip(), s.text())
                if any(norm(x.text()).endswith(norm(AI_LABEL)) for x in s.find(cls="source")):
                    continue
                self.fail(f"{key}: a set-apart line from the AI document without its label")

    def test_index_is_depth_neutral(self):
        src = (self.learn / "index.html").read_text(encoding="utf-8")
        root = tree(src)
        for k in ("learn.draft_banner", "learn.ai_note"):
            self.assertNotIn(norm(EN[k]), norm(root.text()))
        for doc in self.exp["journeys"].values():
            if doc["head"]["lead_study"]:   # a Study and Research text (design §12, §20.1)
                self.assertNotIn(norm(doc["head"]["lead_study"]["en"]), norm(root.text()))
        for n in root.walk():
            self.assertNotIn("status", n.classes)
        self.assertIn(EN["learn.index.how_depths"], src)
        data = set()
        for doc in self.exp["journeys"].values():
            data |= graph_data(doc)
        self.assertEqual(review_language(root, data), [])
        for slug, doc in self.exp["journeys"].items():
            card = [n for n in root.find("li", "journey-card") if n.attrs["data-journey-card"] == slug][0]
            self.assertEqual(card.attrs["data-steps"].split(), [x["key"] for x in doc["head"]["stops"]])
            links = card.find(cls="depth-links")[0].find("a")
            self.assertEqual([a.attrs["href"] for a in links],
                             [e["urls"][d][0][len("learn/"):] for e in self.exp["index"]["journeys"]
                              if e["slug"] == slug for d in X.DEPTHS])

    def test_discover_pages_render_from_the_data_files_alone(self):
        """Design §8: a Discover page is rendered from the resolved export. Rebuilt from
        learn/data alone (each head with its parts joined, the page cut read from the stop
        URLs), with no Site and no engine journey behind the renderer, every Discover page
        is the built page byte for byte."""
        docs, plans = {}, {}
        for slug, j in self.exp["journeys"].items():
            head = j["head"]
            docs[slug] = {**head, "steps": j["steps"], "claims": j["claims"], "passages": j["passages"],
                          "entities": {**head["entities"], **j["entities"]}, "terms": {**head["terms"], **j["terms"]},
                          "glosses": j["glosses"]}
            plans[slug] = {}
            for depth in X.DEPTHS:
                pages: dict[str, list] = {}
                for stop in head["stops"] + head["set_apart"]:
                    pages.setdefault(stop["urls"][depth].split("#", 1)[0], []).append(stop["key"])
                plans[slug][depth] = list(pages.values())
        r = render_learn.LearnRenderer(None, render_learn.Strings(LEARN / "i18n" / "en.json", SITE / "i18n" / "en.json"),
                                       LEARN / "templates").at("discover")
        seen = 0
        for slug in docs:
            book = r.book(types.SimpleNamespace(slug=slug, steps=[], set_apart=[]), docs, plans[slug])
            for k in range(1, len(plans[slug]["discover"]) + 1):
                ctx = r.ctx(book, "discover", k)
                with self.subTest(ctx.path):
                    self.assertEqual(r.page(ctx), read_page(self.out / ctx.path / "index.html"))
                seen += 1
        self.assertEqual(seen, len([e for e in self.exp["pages"] if e["kind"] == "journey" and e["depth"] == "discover"]))

    def test_the_practice_page_is_honest_about_being_empty(self):
        src = (self.learn / "practice" / "index.html").read_text(encoding="utf-8")
        self.assertIn(EN["learn.practice.empty"], src)
        self.assertNotIn('class="questions"', src)
        self.assertNotIn("<script", src)
        self.assertIn("0 accepted", src)

    def test_only_progress_needs_the_script(self):
        for p in self.pages():
            src = p.read_text(encoding="utf-8")
            scripts = re.findall(r"<script[^>]*>", src)
            if p.parent.name == "practice":
                self.assertEqual(scripts, [], p)
            else:
                self.assertEqual(scripts, ['<script src="' + "../" * (len(p.relative_to(self.out).parts) - 1)
                                           + 'learn/assets/learn.js" defer>'], p)
            self.assertNotIn("onclick", src)
            # nothing on the page depends on the script: progress controls are hidden or inert
            self.assertNotIn("<input", re.sub(r"<template.*?</template>", "", src, flags=re.S))
            if p.parent.name != "practice" and p.name == "index.html" and "data-journey=" in src:
                article = tree(src).find("article")[0]
                self.assertEqual(int(article.attrs["data-total"]), len(article.attrs["data-steps"].split()))

    def test_licence_footer_on_every_page(self):
        for p in self.pages():
            foot = p.read_text(encoding="utf-8").split("<footer", 1)[1]
            for needle in ("LICENSING.md", "creativecommons.org/licenses/by-sa/4.0/", "gnu.org/licenses/agpl-3.0.html"):
                self.assertIn(needle, foot, p)

    def test_hijrah_root_page_is_still_the_e1_study_page(self):
        """The E1 class page (design §3.7): same URL, the Study depth, the v1 steps with their
        claims and statuses, today's lead_study, none of the layers; and, while the page
        graph is the one the golden values were recorded on (its fingerprint, an input), the
        Hijrah content_sha, the stage-A content facts and the v1 page byte for byte
        (golden.held_page takes out the permitted additions). A learn change that alters
        any of them fails; only another graph skips (golden.e1_gate)."""
        want = json.loads(golden.E1_FILE.read_text(encoding="utf-8"))
        page = (self.learn / golden.HIJRAH / "index.html").read_text(encoding="utf-8")
        root = tree(page)
        self.assertEqual(root.find("article")[0].attrs["data-depth"], "study")
        steps = [(li.attrs["id"], li.attrs["data-step"]) for li in root.find("li", "step")]
        head = self.exp["journeys"][golden.HIJRAH]["head"]
        self.assertEqual(steps, [(f"step-{n}", s["key"]) for n, s in enumerate(head["stops"], 1)])
        for li in root.find("li", "claim"):
            self.assertIn("Status:", li.text())
        self.assertIn(norm(EN["learn.draft_banner"]), norm(root.text()))
        self.assertIn(EN["journey.hijrah.lead_study"], page)
        for n in root.walk():
            self.assertFalse(n.classes & {"step-prompts", "step-next", "accepted-share", "narration", "claim-id",
                                          "journey-contents", "journey-pager"}, n.classes)
        site, built = self.engine()
        hijrah = [j for j in built if j.slug == golden.HIJRAH][0]
        checked, problems = golden.e1_gate(want, self.exp["index"]["graph"]["fingerprint"], golden.content_sha(self.out),
                                           golden.page_sha(golden.held_page(page)), golden.content_facts(site, hijrah))
        if not checked:
            self.skipTest(problems[0])
        self.assertEqual(problems, [], "the E1 page or what it shows changed on the golden graph: a learn change, or a "
                                       "graph change in blank nodes only (re-verify E1 and record new golden values)")

    def test_study_pages_keep_the_v1_order(self):
        """While the page graph is the one the v1 order was recorded on, every journey's Study
        pages list the v1 steps and set-apart people in the v1 order (Badr's list file is
        unreviewed, so its order is the Prophet ﷺ, then A to Z; design §3.8)."""
        want = json.loads(golden.ORDER_FILE.read_text(encoding="utf-8"))
        if self.exp["index"]["graph"]["fingerprint"] != want["graph"]["fingerprint"]:
            self.skipTest("the page graph changed since the v1 order was recorded")
        for slug, facts in want["journeys"].items():
            steps, apart = [], []
            for _, src in journey_pages(self.out, self.exp, slug, "study"):
                s, a = page_keys(tree(src))
                steps += s
                apart += a
            with self.subTest(slug):
                self.assertEqual((len(steps), golden.sha12(steps)), (facts["steps"], facts["steps_sha"]))
                self.assertEqual((len(apart), golden.sha12(apart)), (facts["apart"], facts["apart_sha"]))

    @classmethod
    def engine(cls) -> tuple:
        """(Site, built journeys) on the page graph, made once for the class."""
        if getattr(cls, "_engine", None) is None:
            site = Site(GRAPH)
            cls._engine = (site, J.build_all(site, J.load_specs(LEARN / "journeys")))
        return cls._engine

    @classmethod
    def discover_keys(cls) -> set:
        """Every key a fresh Discover render reads: every journey page and the index."""
        if getattr(cls, "_discover_keys", None) is None:
            site, built = cls.engine()
            r = render_learn.default_renderer(site)
            res = X.resolve_all(site, None, journeys=built, renderer=r)
            for j in built:
                r.journey_pages(j, res["journeys"], res["plans"][j.slug])
            r.at("discover").index_page(built, 0, res["index"]["journeys"])
            cls._discover_keys = set(r.s.used_at["discover"])
        return cls._discover_keys

    def test_discover_strings_have_no_review_words(self):
        """Every key a Discover render reads (pages and the index): its en text has no review
        word, and for a site key, its ar text, where there is one, no Arabic review stem
        (design §8). The learn ar texts are test_arabic_titles_leads_and_discover_keys_*."""
        used = self.discover_keys()
        self.assertTrue({"learn.narr.took_part", "learn.discover.no_work.other", "learn.prompt.note"} <= used)
        for key in sorted(used):
            self.assertFalse(render_learn.forbidden_at_discover(key), key)
            self.assertTrue(discover_allowed(key), f"{key} is not on DISCOVER_ALLOWED_*")
            self.assertEqual(J.review_words({**SITE_EN, **EN}[key]), [], key)
            if key in SITE_AR and key not in EN:
                self.assertEqual(J.ar_review_stems(SITE_AR[key]), [], key)

    def test_arabic_titles_leads_and_discover_keys_have_no_review_stems(self):
        """Design §8 enforcement 2 and §12: the ar text of every exported title and lead, and
        of every learn key a Discover render reads, has no Arabic review stem."""
        self.assertTrue((LEARN / "i18n" / "ar.json").is_file(), "learn/i18n/ar.json is missing (design §12)")
        learn_ar = J.load_i18n()["ar"]
        self.assertTrue(learn_ar, "learn/i18n/ar.json is empty or unreadable")
        for e in self.exp["index"]["journeys"]:
            for role in ("title", "lead"):
                with self.subTest(e["slug"], role=role):
                    self.assertTrue(e[role]["ar"], "no Arabic text")
                    self.assertEqual(J.ar_review_stems(e[role]["ar"]), [])
        for key in sorted(self.discover_keys() & set(learn_ar)):
            self.assertEqual(J.ar_review_stems(learn_ar[key]), [], key)

    def test_rebuilding_replaces_only_learn(self):
        marker = self.out / "person" / "index.html"
        before = marker.read_bytes()
        quiet(build_learn.build, GRAPH, self.out, True)
        self.assertEqual(marker.read_bytes(), before)
        self.assertTrue((self.learn / ".al-marsad-learn").is_file())

    def test_public_mode_accepted_stops_the_build_before_it_writes_or_removes_anything(self):
        """design §8, fail-closed: no reader page that shows other statuses is left behind."""
        def snapshot(root: Path) -> dict:
            return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(root.rglob("*")) if p.is_file()}

        before = snapshot(self.learn)
        with mock.patch.dict(os.environ, {"MARSAD_PUBLIC_MODE": "accepted"}):
            with self.assertRaises(J.RuleError):
                quiet(build_learn.build, GRAPH, self.out, True)
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaises(J.RuleError):
                    quiet(build_learn.build, GRAPH, Path(d), True)
                self.assertEqual(list(Path(d).iterdir()), [])
        self.assertEqual(snapshot(self.learn), before)

    def test_the_cli_writes_the_same_files_as_the_build(self):
        """journey_export.py computes the reader's page cuts too, so its stop URLs and
        pages.json name the pages build_learn writes."""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable, str(LEARN / "journey_export.py"), "--graph", str(GRAPH), "--out", tmp],
                           check=True, capture_output=True, cwd=ROOT)
            cli = {p.relative_to(tmp).as_posix(): p.read_bytes() for p in Path(tmp).rglob("*") if p.is_file()}
        built = {p.relative_to(self.learn / "data").as_posix(): p.read_bytes()
                 for p in (self.learn / "data").rglob("*") if p.is_file()}
        self.assertEqual(sorted(cli), sorted(built))
        for k in cli:
            self.assertEqual(cli[k], built[k], k)

    def test_build_is_deterministic_across_processes(self):
        """Two learn builds under hash seeds 1 and 2 are byte-identical, with the default budgets
        and with --step-budget 30000 --part-budget 30000 (split pages, cross-page links, contents
        and several parts), data/ and every page included (design §14). Each runs on a copy of
        the same reader site: the site's own build is the site's tests' to check."""
        with tempfile.TemporaryDirectory() as tmp:
            outs = {}
            for seed in ("1", "2"):
                env = {**os.environ, "PYTHONHASHSEED": seed}
                site = Path(tmp) / f"site-{seed}"
                shutil.copytree(reader_site(), site)
                for name, extra in (("default", []), ("small", ["--step-budget", str(SMALL), "--part-budget", str(SMALL)])):
                    subprocess.run([sys.executable, str(LEARN / "build_learn.py"), "--graph", str(GRAPH), "--site", str(site),
                                    *extra], check=True, capture_output=True, env=env)
                    outs[(name, seed)] = Path(tmp) / f"{name}-{seed}"
                    shutil.copytree(site / "learn", outs[(name, seed)])
            for name in ("default", "small"):
                with self.subTest(name):
                    self.assertEqual(differs(filecmp.dircmp(outs[(name, "1")], outs[(name, "2")])), [])
            small = load_json(outs[("small", "1")] / "data" / "pages.json")["pages"]
            self.assertTrue(any(e["pages"] > 1 for e in small if e["kind"] == "journey"))
            self.assertGreater(len(list((outs[("small", "1")] / "data" / "journeys" / "people-of-badr").glob("part-*.json"))), 2)


@unittest.skipUnless(GRAPH.exists(), "build/graph.ttl missing: run ontology/build_graph.py")
class SplitPages(PageChecks, unittest.TestCase):
    """The page graph built with a 30,000-byte step and part budget: every depth of every
    journey is cut into pages, with contents, pager and cross-page links (design §13)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.summary = build_into(cls.out, step_budget=SMALL, part_budget=SMALL)
        cls.exp = export_of(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_long_journeys_are_split_within_the_budget(self):
        self.assertTrue(any(n > 1 for j in self.summary["journeys"].values() for n in j["pages"].values()))
        for e, src in journey_pages(self.out, self.exp):
            s, a = page_keys(tree(src))
            size = step_html_bytes(src)
            if e["page"] == 1 and e["pages"] > 1:
                contents = re.search(r'<nav class="journey-contents".*?</nav>', src, flags=re.S).group(0)
                size += len(contents.encode("utf-8"))
            if len(s + a) > 1:
                self.assertLessEqual(size, SMALL + 64 * len(s + a), e["path"])   # the joins between items
        for path in (self.out / "learn" / "data" / "journeys").rglob("*.json"):
            if path.name.startswith(("part-", "research-")):
                self.assertLessEqual(path.stat().st_size, SMALL, path)

    def test_split_build_passes_the_browser_check(self):
        node, env = node_env()
        if node is None:
            if os.environ.get("GITHUB_ACTIONS"):
                self.fail("node with the playwright package is needed for learn/check_nojs.cjs")
            self.skipTest("node with the playwright package not found")
        res = subprocess.run([node, str(LEARN / "check_nojs.cjs"), str(self.out)], capture_output=True, text=True, env=env,
                             timeout=1200)
        self.assertEqual(res.returncode, 0, res.stdout[-3000:] + res.stderr[-2000:])


class DiscoverGuard(unittest.TestCase):
    """Strings.at("discover") refuses every key that carries review status or review
    language, and the template cache is keyed by depth (design §8, enforcement 1)."""

    def strings(self):
        return render_learn.Strings(LEARN / "i18n" / "en.json", SITE / "i18n" / "en.json")

    def test_discover_guard_raises_on_forbidden_keys(self):
        s = self.strings()
        keys = list(render_learn.DISCOVER_FORBIDDEN_KEYS) + [p + "x" for p in render_learn.DISCOVER_FORBIDDEN_PREFIXES]
        keys += ["status.label", "coverage.label", "learn.claims.show.one", "learn.accepted_share.line",
                 "learn.order.e3_pending", "learn.gloss.label", "learn.check.not_both", "learn.research.heading"]
        # text resting on claims Discover does not show with a source (design §8 "Never shown")
        claim_based = ["learn.order_note.recorded", "learn.order_note.unrecorded", "learn.order_note.part",
                       "learn.note.text", "learn.note.ai_document", "learn.side.heading", "learn.links.heading",
                       "learn.why.heading", "learn.why.plain_link"]
        claim_based += [k for k in family_keys() if k.startswith("learn.why.") and k not in render_learn.DISCOVER_REASONS]
        self.assertIn("learn.why.part_of", claim_based)
        for key in keys + claim_based:
            with self.subTest(key), self.assertRaises(render_learn.ReviewLanguageAtDiscover):
                s.at("discover").t(key)
        for key in list(render_learn.DISCOVER_FORBIDDEN_KEYS) + claim_based:
            s.at("study").raw(key)          # Study and Research may show them
        self.assertNotIn("discover", s.used_at)
        for key in render_learn.DISCOVER_REASONS:          # the computed reasons stay
            s.at("discover").raw(key)
        self.assertEqual(s.used_at["discover"], set(render_learn.DISCOVER_REASONS))
        self.assertTrue(issubclass(render_learn.ReviewLanguageAtDiscover, J.RuleError))

    def test_fixture_discover_renders_read_only_allowed_keys(self):
        """The status fixture (notes, glosses, order notes, every status) and the side
        fixture read at Discover only keys on DISCOVER_ALLOWED_*."""
        from fixtures import site_of
        cases = [(status_fixture()[0], [events_spec(["Fixtureplace"]), people_spec(order="prophet_first_then_name")]),
                 (side_fixture()[0], [people_spec(order="prophet_first_then_name", group_by="side")])]
        for fx, specs in cases:
            site = site_of(fx)
            built = [J.build(site, J.validate(spec)) for spec in specs]
            r = render_learn.LearnRenderer(site, self.strings(), LEARN / "templates")
            res = X.resolve_all(site, None, journeys=built, bank=[], renderer=r)
            for j in built:
                r.journey_pages(j, res["journeys"], res["plans"][j.slug])
            r.at("discover").index_page(built, 0, res["index"]["journeys"])
            used = r.s.used_at["discover"]
            self.assertTrue(any(k.startswith("learn.narr.") for k in used))
            self.assertEqual(sorted(k for k in used if not discover_allowed(k)), [])

    def test_a_forbidden_key_in_a_template_stops_a_discover_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            for p in (LEARN / "templates").glob("*.html"):
                shutil.copyfile(p, Path(tmp) / p.name)
            (Path(tmp) / "probe.html").write_text("<p>[[learn.draft_banner]]</p>", encoding="utf-8")
            r = render_learn.LearnRenderer(None, self.strings(), Path(tmp))
            self.assertIn(EN["learn.draft_banner"][:20], r.at("research").tpl("probe").replace("&#x27;", "'"))
            with self.assertRaises(render_learn.ReviewLanguageAtDiscover):
                r.at("discover").tpl("probe")          # the research copy in the cache is not reused

    def test_discover_after_research_render_sees_the_same_keys(self):
        fx, i = side_fixture()
        from fixtures import site_of
        site = site_of(fx)
        j = J.build(site, J.validate(people_spec(order="prophet_first_then_name", group_by="side")))
        res = X.resolve_all(site, None, journeys=[j], bank=[])

        def discover_keys(first_research: bool) -> set:
            r = render_learn.LearnRenderer(site, self.strings(), LEARN / "templates")
            book = r.book(j, res["journeys"], res["plans"][j.slug])
            if first_research:
                rr = r.at("research")
                rr.page(rr.ctx(book, "research", 1))
            rd = r.at("discover")
            rd.page(rd.ctx(book, "discover", 1))
            return r.s.used_at["discover"]

        fresh, after = discover_keys(False), discover_keys(True)
        self.assertEqual(fresh, after)
        self.assertFalse(any(render_learn.forbidden_at_discover(k) for k in after))
        self.assertTrue({"learn.group.against", "learn.group.against_lead"} <= after)
        self.assertEqual(sorted(k for k in after if not discover_allowed(k)), [])


class StatusesAtEachDepth(unittest.TestCase):
    """A made-up battle with claims of every status, cited and uncited, a gloss, a note, a
    software agent and a 50 Stories record (fixtures.status_fixture), built as an events
    journey and a people journey."""

    @classmethod
    def setUpClass(cls):
        fx, cls.i = status_fixture()
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        graph = fx.write(root / "graph.ttl")
        jdir = root / "journeys"
        jdir.mkdir()
        (jdir / "fixture-events.json").write_text(json.dumps(events_spec(["Fixtureplace"])), encoding="utf-8")
        (jdir / "fixture-people.json").write_text(json.dumps(people_spec(order="prophet_first_then_name")),
                                                  encoding="utf-8")
        cls.out = root / "dist"
        cls.summary = build_into(cls.out, graph, jdir)
        cls.exp = export_of(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def page(self, slug: str, depth: str) -> str:
        e = [e for e in self.exp["pages"] if e.get("journey") == slug and e["depth"] == depth and e["page"] == 1][0]
        return (self.out / e["file"]).read_text(encoding="utf-8")

    def name(self, k: str) -> str:
        return f"Person {k.replace('_cited', ' cited').replace('_uncited', ' uncited').replace('_', ' ')}"

    def test_discover_never_shows_rejected_or_superseded_claims(self):
        hidden = [self.name(k) for k in ("rejected_cited", "superseded_cited", "rejected_uncited", "superseded_uncited")]
        hidden.append("Person twostatus")
        hidden += [self.name(k) for k in ("accepted_uncited", "proposed_uncited", "under_review_uncited")]
        for slug in ("fixture-events", "fixture-people"):
            sentences = " ".join(norm(li.text()) for li in tree(self.page(slug, "discover")).find("li", "sentence"))
            self.assertTrue(sentences, slug)
            for who in hidden:
                self.assertNotIn(who, sentences, (slug, who))
        # each person is a stop of the people journey, so every eligible record shows there; the
        # events journey's one step shows only its first sentences and its prompt's first answers
        # (the Discover caps, design §7.1 and §8) and counts the rest for Study
        sentences = " ".join(norm(li.text()) for li in tree(self.page("fixture-people", "discover")).find("li", "sentence"))
        for who in (self.name("accepted_cited"), self.name("proposed_cited"), "Person nostatus"):
            self.assertIn(who, sentences, who)
        study = tree(self.page("fixture-events", "study"))
        self.assertIn(self.name("rejected_cited"), " ".join(li.text() for li in study.find("li", "claim")))

    def test_a_stop_without_a_cited_claim_shows_the_no_work_line(self):
        root = tree(self.page("fixture-people", "discover"))
        doc = self.exp["journeys"]["fixture-people"]
        by_name = {doc["entities"][s["ref"]]["name"]: s for s in doc["steps"]}
        step = by_name[self.name("accepted_uncited")]
        li = [n for n in root.find("li", "step") if n.attrs["data-step"] == step["key"]][0]
        self.assertEqual(li.find(cls="source"), [])
        self.assertEqual(norm(li.find(cls="no-work")[0].text()), EN["learn.discover.no_work.one"].format(n=1))

    def test_the_ai_document_label_is_on_every_depth(self):
        for depth in X.DEPTHS:
            src = self.page("fixture-events", depth)
            self.assertIn(norm(AI_LABEL), norm(tree(src).text()), depth)

    def test_glosses_notes_and_agents_by_depth(self):
        gloss = GLOSS.split("): ", 1)[1]
        note = EN["learn.note.text"].format(note=NOTE)
        software = EN["learn.research.software"].format(name=SOFTWARE_AGENT)
        pages = {d: norm(tree(self.page("fixture-events", d)).text()) for d in X.DEPTHS}
        self.assertNotIn(gloss, pages["discover"] + pages["study"])
        self.assertIn(gloss, pages["research"])
        self.assertIn(EN["learn.gloss.label"], pages["research"])
        self.assertNotIn(GLOSS, pages["research"])            # the gloss prefix is never shown as text
        self.assertNotIn(NOTE, pages["discover"])
        self.assertIn(note, pages["study"])
        self.assertIn(note, pages["research"])
        self.assertNotIn(SOFTWARE_AGENT, pages["discover"])
        self.assertIn(software, pages["research"])
        self.assertNotIn(software, pages["study"])

    def test_a_recorded_by_line_is_never_labelled_a_source(self):
        """A claim with no citation and no basis says who recorded it, without the "Source:"
        label, in its sentence as on its claim row."""
        agent = SITE_EN["claim.recorded_by"].format(value=SOFTWARE_AGENT)
        for slug in ("fixture-events", "fixture-people"):
            for depth in ("study", "research"):
                self.assertNotIn(norm(f'{SITE_EN["claim.source"]} {agent}'), norm(tree(self.page(slug, depth)).text()))
        li = [n for n in tree(self.page("fixture-people", "study")).find("li", "step")
              if n.attrs["data-step"] == self.i["software"].rsplit("/", 1)[-1]][0]
        sentences = li.find("li", "sentence")
        self.assertTrue(sentences)
        self.assertEqual([norm(s.text()) for s in sentences[0].find(cls="source")], [agent])
        self.assertEqual([norm(s.text()) for s in sentences[0].find(cls="sources")], [agent])
        rows = [r for r in li.find("li", "claim") if SOFTWARE_AGENT in r.text()]
        self.assertEqual([norm(s.text()) for r in rows for s in r.find(cls="source")], [agent])

    def test_statuses_are_shown_as_recorded(self):
        study = tree(self.page("fixture-events", "study"))
        rows = {norm(li.find(cls="claim-text")[0].text()): norm(li.text()) for li in study.find("li", "claim")}
        two = [v for k, v in rows.items() if k.startswith("Person twostatus")][0]
        self.assertIn("Status: rejected", two)                # the most cautious of its two statuses, never folded


class LongJourneys(unittest.TestCase):
    """A made-up battle with 600 people (fixtures.big_people_graph), at the default budget:
    the Study and Research depths are cut into pages within STEP_HTML_BUDGET, page 1 lists
    every stop, the pages link to each other and the site checks pass."""

    @classmethod
    def setUpClass(cls):
        fx, cls.i = big_people_graph(600)
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        graph = fx.write(root / "graph.ttl")
        jdir = root / "journeys"
        jdir.mkdir()
        (jdir / "fixture-people.json").write_text(json.dumps(people_spec(order="prophet_first_then_name")),
                                                  encoding="utf-8")
        cls.out = root / "dist"
        cls.summary = build_into(cls.out, graph, jdir)
        cls.exp = export_of(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_a_600_person_journey_is_split_within_the_budget(self):
        pages = self.summary["journeys"]["fixture-people"]["pages"]
        self.assertGreater(pages["study"], 1)
        self.assertGreater(pages["research"], pages["study"] - 1)
        budget = render_learn.STEP_HTML_BUDGET
        for e, src in journey_pages(self.out, self.exp):
            s, a = page_keys(tree(src))
            size = step_html_bytes(src)
            if e["page"] == 1 and e["pages"] > 1:
                size += len(re.search(r'<nav class="journey-contents".*?</nav>', src, flags=re.S).group(0).encode("utf-8"))
            self.assertLessEqual(size, budget + 64 * len(s + a), e["path"])
        self.assertEqual(quiet(check_html.main, [str(self.out)]), 0)
        # the reader tier's own page for a 600-person battle is over its budget; the learn pages are not
        results, _ = check_budget.check(self.out)
        learn = [(total, rel) for total, rel, *_ in results if rel.startswith("learn/")]
        self.assertEqual(len(learn), len(self.exp["pages"]))
        self.assertEqual([rel for total, rel in learn if total > 300_000], [])

    def test_the_numbering_and_the_contents_run_across_pages(self):
        PageChecks.test_reader_pages_follow_the_export(self)
        PageChecks.test_split_depths_have_a_pager_and_page_one_a_contents_list(self)
        PageChecks.test_every_stop_url_names_the_page_that_holds_it(self)


class CapsAtEachDepth(unittest.TestCase):
    """A made-up battle with a cited whole, a cited leader and 100 cited participants (102
    records): each depth keeps the step to its narration cap, and so does the answer of
    every prompt (design §7.1, §8, §13). At Discover the count of records left for Study
    leaves out what the narration and the prompt's answer show."""

    @classmethod
    def setUpClass(cls):
        fx = Fx()
        cite = "Ibn Hishām, al-Sīra al-Nabawiyya, vol. 1, p. {}"
        cls.battle = fx.event("fxBattle", "Fixtureplace battle", dates=("0624-03-01", "0624-03-31"))
        whole = fx.event("fxWhole", "Greater campaign", dates=("0624-01-01", "0624-12-31"))
        fx.claim(cls.battle, "rel_part_of", whole, cite=cite.format(10))
        fx.claim(fx.person("fxLeader", "Leader fixture"), "rel_led", cls.battle, cite=cite.format(20))
        for i in range(100):
            fx.claim(fx.person(f"fxP{i:03d}", f"Person {i:03d}"), "rel_participated_in", cls.battle,
                     cite=cite.format(100 + i))
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        graph = fx.write(root / "graph.ttl")
        jdir = root / "journeys"
        jdir.mkdir()
        (jdir / "fixture-events.json").write_text(json.dumps(events_spec(["Fixtureplace"])), encoding="utf-8")
        cls.out = root / "dist"
        build_into(cls.out, graph, jdir)
        cls.exp = export_of(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def step(self, depth: str) -> Node:
        rel = "" if depth == "study" else f"{depth}/"       # the fixture journey's door is Study
        src = (self.out / "learn" / "fixture-events" / rel / "index.html").read_text(encoding="utf-8")
        return [li for li in tree(src).find("li", "step") if li.attrs["data-step"] == "fxBattle"][0]

    def test_a_discover_step_shows_three_sentences_and_one_capped_prompt(self):
        li = self.step("discover")
        cap = render_learn.NARRATION["discover"]
        narration = li.find("ul", "narration")[0].find("li", "sentence")
        prompts = li.find("details", "prompt")
        self.assertEqual(len(narration), cap)
        self.assertEqual(len(prompts), 1)
        answer = prompts[0].find("li", "sentence")
        self.assertEqual(len(answer), cap)
        self.assertEqual(len(li.find("li", "sentence")), 2 * cap)
        for s in narration + answer:
            self.assertTrue(s.find(cls="source"))
        # the narration shows the whole, the leader and the first participant; the answer
        # (who took part) the leader and the first two participants: 4 of the 102 records
        self.assertIn("Greater campaign", narration[0].text())
        self.assertIn("Leader fixture", answer[0].text())
        self.assertIn("Person 001", answer[2].text())
        self.assertEqual(norm(li.find(cls="narr-more")[0].text()), EN["learn.narr.more.other"].format(n=98))

    def test_study_and_research_keep_narration_answers_and_claim_rows_to_their_caps(self):
        for depth in ("study", "research"):
            li = self.step(depth)
            cap, rows = render_learn.NARRATION[depth], render_learn.CLAIM_LIST[depth]
            with self.subTest(depth):
                self.assertEqual(len(li.find("ul", "narration")[0].find("li", "sentence")), min(cap, 102))
                prompts = li.find("details", "prompt")
                self.assertEqual(len(prompts), 1)              # who took part; no dated or place claim
                answer = self.exp["journeys"]["fixture-events"]["by_key"]["fxBattle"]["prompts"][0]["answer"]["claims"]
                self.assertGreater(len(answer), cap if depth == "study" else 0)
                self.assertEqual(len(prompts[0].find("li", "sentence")), min(cap, len(answer)))
                self.assertEqual(len(li.find("li", "claim")), rows)
                self.assertEqual(norm(li.find(cls="claims-more")[0].text()),
                                 EN["learn.claims.more.other"].format(n=102 - rows))


class PracticeWithAcceptedClaims(unittest.TestCase):
    """A made-up graph where scholars have accepted four claims: the page shows the
    questions, each answer linked to the people, events and sources behind it."""

    @classmethod
    def setUpClass(cls):
        fx = Fx()
        cls.a, cls.b = fx.person("fxPersonA", "Person A"), fx.person("fxPersonB", "Person B")
        cls.e1, cls.e2 = fx.event("fxEventA", "Rihla one"), fx.event("fxEventB", "Rihla two")
        cls.claims = [fx.claim(w, "rel_participated_in", e, ("accepted",)) for w in (cls.a, cls.b) for e in (cls.e1, cls.e2)]
        fx.claim(cls.a, "rel_led", cls.e1, ("proposed",))
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        graph = fx.write(root / "graph.ttl")
        jdir = root / "journeys"
        jdir.mkdir()
        spec = json.loads((LEARN / "journeys" / "hijrah-step-by-step.json").read_text(encoding="utf-8"))
        spec["select"]["named"]["words"] = ["Rihla"]
        (jdir / "hijrah-step-by-step.json").write_text(json.dumps(spec), encoding="utf-8")
        cls.out = root / "dist"
        old = render_learn.QUESTIONS_PER_PAGE
        render_learn.QUESTIONS_PER_PAGE = 1        # two questions -> two pages
        try:
            cls.summary = build_into(cls.out, graph, jdir)
        finally:
            render_learn.QUESTIONS_PER_PAGE = old

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_questions_are_made_and_paged(self):
        self.assertEqual(self.summary["questions"], 2)
        self.assertEqual(self.summary["practice_pages"], 2)
        bank = json.loads((self.out / "learn" / "practice" / "bank.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(q["type"] for q in bank["questions"]), ["both_events", "shared_events"])
        self.assertEqual(practice.claims_used(bank["questions"]), set(self.claims))
        pages = load_json(self.out / "learn" / "data" / "pages.json")["pages"]
        self.assertEqual(sorted(e["path"] for e in pages if e["kind"] == "practice"),
                         ["learn/practice/", "learn/practice/2/"])

    def test_each_answer_links_to_its_entities_and_sources(self):
        pages = [self.out / "learn" / "practice" / "index.html", self.out / "learn" / "practice" / "2" / "index.html"]
        text = "".join(p.read_text(encoding="utf-8") for p in pages)
        self.assertEqual(text.count('<li class="question"'), 2)
        self.assertEqual(text.count("Status: accepted"), 8)          # two answers x two claims, per question
        self.assertNotIn("Status: proposed", text)
        self.assertEqual(text.count("Source: Fixture basis."), 8)
        for href in set(re.findall(r'href="((?:\.\./)+)(person|event)/([^/"]+)/"', text)):
            self.assertTrue((self.out / href[1] / href[2] / "index.html").is_file())
        self.assertEqual(quiet(check_html.main, [str(self.out)]), 0)
        self.assertEqual(quiet(check_budget.main, [str(self.out)]), 0)


class NotWordsInTheRuleBox(unittest.TestCase):
    """not_words filter the events chosen by name; the links may still add an event whose
    name holds one (a raid recorded as part of the battle), as design §3.3 has it. So the
    rule box says the words leave events out of those chosen by name, and says it before
    the sentence on the links, at every depth, for a people and an events journey."""

    @classmethod
    def setUpClass(cls):
        from fixtures import site_of
        fx = Fx()
        fx.prophet()
        cls.battle = fx.event("fxBattle", "Battle of Fixtureplace")
        cls.raid = fx.event("fxRaid", "Raid of Fixtureplace")
        fx.claim(cls.raid, "rel_part_of", cls.battle, cite="Fixture work, vol. 1, p. 3")
        cls.a, cls.b = fx.person("fxA", "Person A"), fx.person("fxB", "Person B")
        fx.participation(cls.battle, cls.a)
        fx.participation(cls.raid, cls.b)
        cls.site = site_of(fx)
        cls.specs = {"people": J.validate(people_spec(order="prophet_first_then_name", not_words=["raid"])),
                     "events": J.validate(events_spec(["Fixtureplace"], follow=("parts",), max_links=1,
                                                      not_words=["raid"]))}
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        graph = fx.write(root / "graph.ttl")
        jdir = root / "journeys"
        jdir.mkdir()
        for spec in cls.specs.values():
            (jdir / f"{spec['slug']}.json").write_text(json.dumps(spec), encoding="utf-8")
        cls.out = root / "dist"
        build_into(cls.out, graph, jdir)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def rule(self, slug: str, depth: str) -> str:
        rel = "" if depth == "study" else f"{depth}/"       # both fixture journeys open at Study
        src = (self.out / "learn" / slug / rel / "index.html").read_text(encoding="utf-8")
        return norm(src.split('id="h-rule"', 1)[1].split("</section>", 1)[0])

    def test_the_words_filter_the_named_events_and_the_links_may_add_one(self):
        links = J.Links(self.site)
        hop, _ = J.select_events(self.site, links, self.specs["people"]["select"]["events"])
        self.assertEqual(hop, {self.battle: 0, self.raid: 1})      # the raid is reached as a part
        people = J.build(self.site, self.specs["people"])
        self.assertEqual(sorted(s.iri for s in people.steps), sorted([self.a, self.b]))
        events = J.build(self.site, self.specs["events"])
        self.assertEqual({s.iri: [r.kind for r in s.reasons] for s in events.steps},
                         {self.battle: ["named"], self.raid: ["part_of"]})

    def test_the_rule_box_scopes_the_words_to_the_events_chosen_by_name(self):
        text = EN["learn.rule.not_words"]
        self.assertTrue(text.endswith(" are left out of those chosen by name."), text)
        self.assertEqual(J.review_words(text), [])
        head, tail = (render_learn.esc(x) for x in text.split("{words}"))
        follow = {"fixture-people": EN["learn.rule.people_follow.one"], "fixture-events": EN["learn.rule.events_follow.one"]}
        r = render_learn.default_renderer(self.site)
        for slug, sentence in follow.items():
            links = render_learn.esc(sentence.split("{links}")[0])
            v1 = norm(r.rule_html(J.build(self.site, self.specs[slug.split("-")[1]])))     # the held-page form
            for depth, rule in [(d, self.rule(slug, d)) for d in X.DEPTHS] + [("held", v1)]:
                with self.subTest(slug, depth=depth):
                    at = rule.index(head)
                    self.assertIn("raid", rule[at:rule.index(tail, at)])
                    self.assertNotIn(links, rule[:at])
                    self.assertIn(links, rule[rule.index(tail, at):])


class SideGroupsAtEveryDepth(unittest.TestCase):
    """A made-up battle with people recorded on both sides (fixtures.side_fixture): every
    depth gives the against group its heading and lead where the group starts, numbers the
    steps across both lists, and says in the rule box that the order holds inside each group
    (design §6.4). Without group_by, neither appears."""

    @classmethod
    def setUpClass(cls):
        fx, cls.i = side_fixture()
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        graph = fx.write(root / "graph.ttl")
        cls.out = {}
        for name, group_by in (("grouped", "side"), ("plain", None)):
            jdir = root / f"journeys-{name}"
            jdir.mkdir()
            spec = people_spec(order="prophet_first_then_name", group_by=group_by)
            (jdir / f"{spec['slug']}.json").write_text(json.dumps(spec), encoding="utf-8")
            out = root / f"dist-{name}"
            build_into(out, graph, jdir)
            cls.out[name] = out
        cls.slug = spec["slug"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def page(self, name: str, depth: str = "study") -> str:
        rel = "" if depth == "study" else f"{depth}/"       # the fixture journey's door is Study
        return (self.out[name] / "learn" / self.slug / rel / "index.html").read_text(encoding="utf-8")

    def test_the_against_group_has_its_heading_and_lead_where_it_starts(self):
        heading, lead = (render_learn.esc(EN[k]) for k in ("learn.group.against", "learn.group.against_lead"))
        for depth in X.DEPTHS:
            src = self.page("grouped", depth)
            with self.subTest(depth):
                self.assertEqual(src.count(heading), 1)
                self.assertEqual(src.count(lead), 1)
                before, after = src.split(heading, 1)
                steps_before = re.findall(r'<li class="step" id="step-(\d+)" data-step="([^"]+)"', before)
                steps_after = re.findall(r'<li class="step" id="step-(\d+)" data-step="([^"]+)"', after)
                self.assertEqual(sorted(pid for _, pid in steps_after),
                                 sorted(self.i[k].rsplit("/", 1)[-1] for k in ("against", "convert")))
                self.assertEqual([int(n) for n, _ in steps_before + steps_after], list(range(1, 12)))
                self.assertIn(f'<ol class="journey-steps" start="{len(steps_before) + 1}">', after)
        self.assertEqual(quiet(check_html.main, [str(self.out["grouped"])]), 0)

    def test_the_rule_box_says_the_order_holds_inside_each_group(self):
        for depth in X.DEPTHS:
            rule = self.page("grouped", depth).split('id="h-rule"', 1)[1].split("</section>", 1)[0]
            with self.subTest(depth):
                order = rule.index(render_learn.esc(EN["learn.order.prophet_first_then_name"]))
                self.assertGreater(rule.index(render_learn.esc(EN["learn.rule.group_side"])), order)
        self.assertEqual(J.review_words(EN["learn.rule.group_side"]), [])
        self.assertNotIn("last", EN["learn.rule.group_side"].lower().split())

    def test_without_group_by_there_is_one_list_and_no_group_text(self):
        for depth in X.DEPTHS:
            src = self.page("plain", depth)
            for k in ("learn.group.against", "learn.group.against_lead", "learn.rule.group_side"):
                self.assertNotIn(render_learn.esc(EN[k]), src, k)
            self.assertEqual(src.count('<ol class="journey-steps"'), 1)


def side_graph():
    """fixtures.side_fixture plus three cited records for Person Against (led, took part,
    absent from), on another page than its side claim, that rank before the side claim:
    in the export's order its side sentence is past Discover's three-sentence cap."""
    fx, i = side_fixture()
    for pred in ("rel_led", "rel_participated_in", "rel_absent_from"):
        fx.claim(i["against"], pred, i["battle"], cite="Fixture work, vol. 3, p. 9")
    return fx, i


class SideGroupsOnSplitPages(PageChecks, unittest.TestCase):
    """side_graph grouped by side with a 1-byte step budget, so every stop has a page of its
    own and the against group (steps 10 and 11) spans two pages at every depth. Every page
    invariant holds; each page holding an against-group step shows the group's heading and
    lead, not only the page where it starts; and at Discover the record behind the heading
    is shown within the cap (design §6.4, G1/G8)."""

    @classmethod
    def setUpClass(cls):
        fx, cls.i = side_graph()
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        graph = fx.write(root / "graph.ttl")
        jdir = root / "journeys"
        jdir.mkdir()
        spec = people_spec(order="prophet_first_then_name", group_by="side")
        (jdir / f"{spec['slug']}.json").write_text(json.dumps(spec), encoding="utf-8")
        cls.slug = spec["slug"]
        cls.out = root / "dist"
        cls.summary = build_into(cls.out, graph, jdir, step_budget=1)
        cls.exp = export_of(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_each_page_of_the_against_group_has_its_heading_and_lead(self):
        heading, lead = (render_learn.esc(EN[k]) for k in ("learn.group.against", "learn.group.against_lead"))
        g = [g for g in self.exp["journeys"][self.slug]["head"]["groups"] if g["key"] == "against"][0]
        self.assertEqual((g["from"], g["to"]), (10, 11))
        for depth in X.DEPTHS:
            pages = journey_pages(self.out, self.exp, self.slug, depth)
            with self.subTest(depth):
                self.assertEqual(len(pages), 11)
                for e, src in pages:
                    numbers = {int(n) for n in re.findall(r'<li class="step" id="step-(\d+)"', src)}
                    inside = bool(numbers & {10, 11})
                    self.assertEqual((src.count(heading), src.count(lead)), (int(inside), int(inside)), e["path"])

    def test_the_side_record_leads_an_against_step_at_discover(self):
        step = self.exp["journeys"][self.slug]["by_key"][self.i["against"].rsplit("/", 1)[-1]]
        cap = render_learn.NARRATION["discover"]
        side = {c for s in step["side"] for c in s["claims"]}
        items = [x for x in step["narration"] if x["d"] == "discover"]
        self.assertGreaterEqual([n for n, x in enumerate(items) if side & set(x["c"])][0], cap)   # past the cap
        src = journey_pages(self.out, self.exp, self.slug, "discover")[step["n"] - 1][1]
        li = [x for x in tree(src).find("li", "step") if x.attrs["data-step"] == step["key"]][0]
        sentences = li.find("ul", "narration")[0].find("li", "sentence")
        self.assertEqual(len(sentences), cap)
        self.assertIn("among those who fought against", norm(sentences[0].text()))
        self.assertIn("Fixture work, vol. 2, p. 7", norm(sentences[0].text()))


if __name__ == "__main__":
    unittest.main()
