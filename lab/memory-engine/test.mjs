// node lab/memory-engine/test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const M = require("./scheduler.js");
const T0 = Date.UTC(2026, 0, 1);

test("forgetting curve: R(0)=1, R(S)=0.9, decreasing", () => {
  assert.equal(M.retrievability(0, 5), 1);
  assert.ok(Math.abs(M.retrievability(5, 5) - 0.9) < 1e-12);
  assert.ok(M.retrievability(10, 5) < M.retrievability(5, 5));
  assert.equal(M.interval(10, 0.9), 10);
});

test("first review: stability and difficulty set by grade", () => {
  const a = M.review(M.newItem("q"), "again", T0);
  const e = M.review(M.newItem("q"), "easy", T0);
  assert.ok(e.S > a.S && e.D < a.D);
  assert.equal(a.due - T0, M.DAY);
});

test("successful reviews grow stability and intervals; lapses shrink them", () => {
  let it = M.review(M.newItem("q"), "good", T0);
  const s1 = it.S;
  it = M.review(it, "good", it.due);
  assert.ok(it.S > s1, "stability grows");
  const before = it.S;
  const lapsed = M.review(it, "again", it.due);
  assert.ok(lapsed.S < before && lapsed.lapses === 1);
  const hard = M.review(it, "hard", it.due), easy = M.review(it, "easy", it.due);
  assert.ok(hard.S < easy.S && hard.D > easy.D);
  assert.throws(() => M.review(it, 7, T0));
});

test("BKT: correct raises, wrong lowers, guessing is discounted", () => {
  const c = M.newConcept("person:x");
  const up = M.trace(c, true, 0.25), down = M.trace(c, false, 0.25);
  assert.ok(up.pKnown > c.pKnown && down.pKnown < up.pKnown);
  assert.ok(M.trace(c, true, 0.5).pKnown < up.pKnown, "an easy guess teaches us less");
  let k = c;
  for (let i = 0; i < 6; i++) k = M.trace(k, true);
  assert.ok(M.mastered(k));
  assert.equal(M.star(M.newConcept("x")).label, "unseen");
  assert.equal(M.star(k).label, "mastered");
});

const bank = JSON.parse(readFileSync(new URL("./bank.json", import.meta.url), "utf8"));

test("bank: every option carries claim, gloss and citation; ≤3 distractors", () => {
  assert.ok(bank.total > 500);
  const ids = new Set();
  for (const q of bank.questions) {
    assert.ok(!ids.has(q.id), "unique id");
    ids.add(q.id);
    for (const o of q.options) assert.ok(o.claim.startsWith("ast:") && o.gloss && o.cite, q.id);
    assert.ok(q.options.filter((o) => !o.correct).length <= 3);
    assert.ok(q.options.some((o) => o.correct));
    assert.ok(q.difficulty >= 0 && q.difficulty <= 1);
  }
  for (const t of ["present", "where", "order", "dispute", "event", "family"]) assert.ok(bank.counts[t] > 0, t);
});

test("learner: recall before reveal is enforced, evidence shown after answering", () => {
  const L = new M.Learner(bank.questions);
  const q = L.next(T0);
  const shown = L.ask(q);
  assert.equal(shown.options, undefined, "stem only");
  assert.throws(() => L.reveal(), /recall before reveal/);
  assert.throws(() => L.answer("x", T0), /recall before reveal/);
  L.commitRecall("");
  const opts = L.reveal();
  assert.ok(opts.every((o) => o.claim === undefined), "no evidence before answering");
  const right = q.type === "order"
    ? q.options.slice().sort((a, b) => a.rank - b.rank).map((o) => o.text)
    : q.options.filter((o) => o.correct).map((o) => o.text);
  const res = L.answer(right, T0);
  assert.ok(res.correct && res.evidence.every((e) => e.claim && e.cite));
  assert.ok(L.items[q.id].due > T0);
  for (const k of q.concepts) assert.ok(L.sky()[k].brightness > 0);
  assert.notEqual(L.next(T0).id, q.id, "not due again today");
  // recalled-and-right beats recognised-and-right
  const L2 = new M.Learner(bank.questions);
  L2.ask(q);
  L2.commitRecall(right[0]);
  assert.equal(L2.answer(right, T0).grade, M.GRADE.easy);
});

test("learner: a wrong answer comes back tomorrow and dims the concept", () => {
  const q = bank.questions.find((x) => x.type === "where");
  const L = new M.Learner(bank.questions);
  L.ask(q);
  L.commitRecall("no idea");
  const wrong = q.options.find((o) => !o.correct).text;
  const res = L.answer(wrong, T0);
  assert.equal(res.correct, false);
  assert.ok(res.evidence.find((e) => e.text === wrong).gloss, "the learner sees why it is wrong");
  assert.equal(L.items[q.id].due, T0 + M.DAY);
  assert.equal(L.next(T0 + M.DAY).id, q.id);
  for (const k of q.concepts) assert.ok(L.concepts[k].pKnown < M.BKT.pInit);
  const restored = new M.Learner(bank.questions, JSON.parse(JSON.stringify(L)));
  assert.equal(restored.next(T0 + M.DAY).id, q.id, "state round-trips");
});
