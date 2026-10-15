"""Shared set-up for the ask tests: one index and engine per test run.

The integration tests need build/graph.ttl (run ontology/build_graph.py first) and
are skipped without it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ASK = TESTS.parent
ROOT = ASK.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GRAPH = ROOT / "build" / "graph.ttl"
GOLDEN = ASK / "golden" / "questions.jsonl"

_CACHE: dict = {}


def have_graph() -> bool:
    return GRAPH.exists()


def engine():
    if "engine" not in _CACHE:
        from ask import index
        from ask.dsl import Engine
        _CACHE["engine"] = Engine(index.build(GRAPH))
    return _CACHE["engine"]


def i18n() -> dict:
    from ask.dsl import load_i18n
    return load_i18n()


def golden() -> list[dict]:
    return [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()]
