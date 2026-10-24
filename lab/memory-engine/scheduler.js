/* al-Marṣad memory engine: spaced repetition + knowledge tracing. No dependencies.
 *
 * Two models, kept apart on purpose:
 *  1. Per ITEM (one question): an FSRS-style memory model (stability S in days,
 *     difficulty D in 1..10). Uses the published FSRS-4 forgetting curve and
 *     default weights; the update rules are FSRS-4's, slightly simplified
 *     (no short-term/same-day steps, no fuzz). Interval = days until predicted
 *     recall falls to the target retention.
 *  2. Per CONCEPT (a person, place or event): Bayesian Knowledge Tracing,
 *     P(known), updated from every question that touches the concept. This is
 *     what the sky shows: a star's brightness is how well its concept is known.
 *
 * Works as a CommonJS module (node) and as a browser global (MemoryEngine).
 */
(function (root) {
  "use strict";
  const DAY = 86400000;
  // FSRS-4 default weights.
  const W = [0.4, 0.6, 2.4, 5.8, 4.93, 0.94, 0.86, 0.01, 1.49, 0.14, 0.94, 2.18, 0.05, 0.34, 1.26, 0.29, 2.61];
  const GRADE = { again: 1, hard: 2, good: 3, easy: 4 };
  const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));

  /** Probability of recall t days after the last review, given stability S (R(S,S) = 0.9). */
  function retrievability(tDays, S) {
    return Math.pow(1 + tDays / (9 * S), -1);
  }
  /** Days until recall probability drops to `retention`. */
  function interval(S, retention = 0.9) {
    return Math.max(1, Math.round(9 * S * (1 / retention - 1)));
  }
  const initD = (g) => clamp(W[4] - (g - 3) * W[5], 1, 10);

  function newItem(id) {
    return { id, S: 0, D: 0, reps: 0, lapses: 0, last: null, due: 0 };
  }

  /** Review an item with grade 1..4 at time `now` (ms). Returns a new state; input is not mutated. */
  function review(item, grade, now, retention = 0.9) {
    const g = typeof grade === "string" ? GRADE[grade] : grade;
    if (!(g >= 1 && g <= 4)) throw new Error("grade must be 1..4");
    const s = { ...item };
    if (s.reps === 0) {
      s.S = W[g - 1];
      s.D = initD(g);
    } else {
      const t = Math.max(0, (now - s.last) / DAY);
      const R = retrievability(t, s.S);
      // Difficulty moves with the grade, mean-reverting toward the "good" default.
      s.D = clamp(W[7] * initD(3) + (1 - W[7]) * (s.D - W[6] * (g - 3)), 1, 10);
      if (g === 1) {
        s.lapses += 1;
        s.S = Math.min(s.S, W[11] * Math.pow(s.D, -W[12]) * (Math.pow(s.S + 1, W[13]) - 1) * Math.exp(W[14] * (1 - R)));
      } else {
        const hard = g === 2 ? W[15] : 1;
        const easy = g === 4 ? W[16] : 1;
        s.S = s.S * (1 + Math.exp(W[8]) * (11 - s.D) * Math.pow(s.S, -W[9]) * (Math.exp(W[10] * (1 - R)) - 1) * hard * easy);
      }
    }
    s.S = Math.max(0.1, s.S);
    s.reps += 1;
    s.last = now;
    s.due = now + (g === 1 ? DAY : interval(s.S, retention) * DAY);
    return s;
  }

  /** Turn an answer into a grade. Recall-before-reveal: a correct answer that was
   *  recalled before the options were shown counts more than a recognised one. */
  function gradeFromAnswer({ correct, recalled = false, slow = false }) {
    if (!correct) return GRADE.again;
    if (recalled) return slow ? GRADE.good : GRADE.easy;
    return slow ? GRADE.hard : GRADE.good;
  }

  // ---------------- Bayesian Knowledge Tracing per concept ----------------
  const BKT = { pInit: 0.2, pLearn: 0.15, pSlip: 0.1 };

  function newConcept(id, p = BKT.pInit) {
    return { id, pKnown: p, seen: 0 };
  }
  /** Update P(known) after one observation. guess = 1/options for multiple choice. */
  function trace(concept, correct, guess = 0.25, prm = BKT) {
    const p = concept.pKnown;
    const post = correct
      ? (p * (1 - prm.pSlip)) / (p * (1 - prm.pSlip) + (1 - p) * guess)
      : (p * prm.pSlip) / (p * prm.pSlip + (1 - p) * (1 - guess));
    return { ...concept, pKnown: post + (1 - post) * prm.pLearn, seen: concept.seen + 1 };
  }
  const mastered = (c, threshold = 0.95) => c.pKnown >= threshold;

  /** How the sky draws a concept: brightness from P(known); a star unseen stays dark. */
  function star(concept) {
    if (!concept || concept.seen === 0) return { brightness: 0, label: "unseen" };
    const b = Math.round(concept.pKnown * 100) / 100;
    return { brightness: b, label: mastered(concept) ? "mastered" : b >= 0.6 ? "learning" : "faint" };
  }

  // ---------------- Learner: items + concepts + recall-before-reveal ----------------
  class Learner {
    constructor(bank, state = {}) {
      this.bank = new Map(bank.map((q) => [q.id, q]));
      this.items = state.items || {};
      this.concepts = state.concepts || {};
      this.pending = null;
    }
    /** Next question: the most overdue seen item, else the easiest unseen one. */
    next(now) {
      let best = null;
      for (const it of Object.values(this.items)) {
        if (it.due <= now && (!best || it.due < best.due)) best = it;
      }
      if (best) return this.bank.get(best.id);
      const fresh = [...this.bank.values()].filter((q) => !this.items[q.id]);
      fresh.sort((a, b) => a.difficulty - b.difficulty || (a.id < b.id ? -1 : 1));
      return fresh[0] || null;
    }
    /** Show only the stem. Options and evidence stay hidden until recall is committed. */
    ask(q) {
      this.pending = { id: q.id, recalled: null };
      return { id: q.id, stem: q.stem, type: q.type };
    }
    /** The learner commits a free recall attempt (may be empty: "I don't know"). */
    commitRecall(text) {
      if (!this.pending) throw new Error("no question asked");
      this.pending.recalled = String(text || "").trim();
      return true;
    }
    /** Reveal the options. Refused until a recall attempt has been committed. */
    reveal() {
      if (!this.pending || this.pending.recalled === null) throw new Error("recall before reveal");
      const q = this.bank.get(this.pending.id);
      return q.options.map((o) => ({ text: o.text })); // evidence comes only after answering
    }
    /** Answer with the set of chosen option texts (or, for order questions, the sequence). */
    answer(choice, now, { slow = false } = {}) {
      if (!this.pending || this.pending.recalled === null) throw new Error("recall before reveal");
      const q = this.bank.get(this.pending.id);
      const picked = Array.isArray(choice) ? choice : [choice];
      let correct;
      if (q.type === "order") {
        correct = picked.join("\u0000") === q.options.slice().sort((a, b) => a.rank - b.rank).map((o) => o.text).join("\u0000");
      } else {
        const want = q.options.filter((o) => o.correct).map((o) => o.text).sort();
        correct = picked.slice().sort().join("\u0000") === want.join("\u0000");
      }
      const rightTexts = q.options.filter((o) => o.correct).map((o) => o.text.toLowerCase());
      const recalled = !!this.pending.recalled && rightTexts.some((t) => t.includes(this.pending.recalled.toLowerCase()));
      const g = gradeFromAnswer({ correct, recalled, slow });
      this.items[q.id] = review(this.items[q.id] || newItem(q.id), g, now);
      const guess = q.type === "order" ? 0.05 : Math.max(0.05, q.options.filter((o) => o.correct).length / q.options.length);
      for (const k of q.concepts) this.concepts[k] = trace(this.concepts[k] || newConcept(k), correct, guess);
      this.pending = null;
      // The reveal: every option with the claim that makes it right or wrong.
      return { correct, grade: g, evidence: q.options.map(({ text, correct, claim, gloss, cite }) => ({ text, correct, claim, gloss, cite })) };
    }
    sky() {
      return Object.fromEntries(Object.values(this.concepts).map((c) => [c.id, star(c)]));
    }
    toJSON() {
      return { items: this.items, concepts: this.concepts };
    }
  }

  const api = { DAY, W, GRADE, retrievability, interval, newItem, review, gradeFromAnswer, BKT, newConcept, trace, mastered, star, Learner };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.MemoryEngine = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
