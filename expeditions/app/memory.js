/* al-Marṣad Expeditions: the learner's memory. Kept only on this device; no account, no server.
   Spaced review uses FSRS-4.5 with its published default weights (open-spaced-repetition).
   Two grades only: "again" (wrong) and "good" (right), so a learner never rates themself. */
"use strict";
(function (root) {
  const KEY = "marsad-x:v1";
  const W = [0.4872, 1.4003, 3.7145, 13.8206, 5.1618, 1.2298, 0.8975, 0.031, 1.6474, 0.1367, 1.0461, 2.1072, 0.0793, 0.3246, 1.587, 0.2272, 2.8755];
  const DECAY = -0.5, FACTOR = 19 / 81, RETAIN = 0.9, DAY = 864e5;

  function blank() { return { cards: {}, seen: {}, steps: {}, notes: {}, picks: {}, desk: {}, reviewer: "" }; }
  let state = blank(), ok = true;
  try { const raw = localStorage.getItem(KEY); if (raw) state = Object.assign(blank(), JSON.parse(raw)); } catch (e) { ok = false; }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { ok = false; } }

  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const retr = (t, s) => Math.pow(1 + FACTOR * t / s, DECAY);
  const interval = s => Math.max(1, Math.round(s / FACTOR * (Math.pow(RETAIN, 1 / DECAY) - 1)));
  const d0 = g => clamp(W[4] - (g - 3) * W[5], 1, 10);

  // g: 1 = again, 3 = good
  function grade(id, g, now = Date.now()) {
    let c = state.cards[id];
    if (!c) {
      c = { s: W[g - 1], d: d0(g), reps: 1, lapses: g === 1 ? 1 : 0, last: now };
    } else {
      const t = Math.max(0, (now - c.last) / DAY), r = retr(t, c.s);
      const d = clamp(W[7] * d0(3) + (1 - W[7]) * (c.d - W[6] * (g - 3)), 1, 10);
      const s = g === 1
        ? W[11] * Math.pow(d, -W[12]) * (Math.pow(c.s + 1, W[13]) - 1) * Math.exp(W[14] * (1 - r))
        : c.s * (Math.exp(W[8]) * (11 - d) * Math.pow(c.s, -W[9]) * (Math.exp(W[10] * (1 - r)) - 1) + 1);
      c = { s: Math.max(0.1, s), d, reps: c.reps + 1, lapses: c.lapses + (g === 1 ? 1 : 0), last: now };
    }
    c.due = now + (g === 1 ? DAY / 2 : interval(c.s) * DAY);
    state.cards[id] = c; save();
    return c;
  }
  function due(now = Date.now()) { return Object.entries(state.cards).filter(([, c]) => c.due <= now).map(([id]) => id); }

  const M = {
    get ok() { return ok; },
    get state() { return state; },
    grade, due,
    nextDue() { const ds = Object.values(state.cards).map(c => c.due).sort((a, b) => a - b); return ds[0] || null; },
    see(name, slug) { if (!state.seen[name]) { state.seen[name] = slug; save(); } },
    step(slug, i) { const s = state.steps[slug] || (state.steps[slug] = []); if (!s.includes(i)) { s.push(i); save(); } },
    note(key, v) { if (v === undefined) return state.notes[key] || ""; state.notes[key] = v; save(); },
    pick(key, v) { if (v === undefined) return state.picks[key]; state.picks[key] = v; save(); },
    desk(slug, id, v) { const d = state.desk[slug] || (state.desk[slug] = {}); if (v === undefined) return d[id]; if (v === null) delete d[id]; else d[id] = v; save(); },
    reviewer(v) { if (v === undefined) return state.reviewer; state.reviewer = v; save(); },
    export() { return JSON.stringify(state); },
    import(text) { const s = JSON.parse(text); if (typeof s !== "object" || !s.cards) throw new Error("not a memory file"); state = Object.assign(blank(), s); save(); },
    wipe() { state = blank(); save(); },
  };
  root.Memory = M;
})(window);
