  // ------------------------------------------------------------------ Sky Atlas additions (data side)
  // distance in a recorded chain of narration: the first narrator is 1, each hop adds one, the collector is last
  const chainDist = new Int16Array(n);
  const chainInfo = new Map();
  let chainMax = 1;
  CHAINS.forEach((ch, ci) => {
    const set = (i, d, col) => {
      if (i === null || i === undefined) return;
      if (!chainDist[i] || d < chainDist[i]) { chainDist[i] = d; chainInfo.set(i, { ci, d, col }); }
      chainMax = Math.max(chainMax, d);
    };
    if (ch.links.length) set(ch.links[0][0], 1, false);
    ch.links.forEach((ln, k) => set(ln[1], k + 2, false));
    if (ch.collector !== null && ch.collector !== undefined) set(ch.collector, ch.links.length + 2, true);
  });

  // who was there, and who wasn't: only what a record states; silence is not absence
  const PRESENT_PK = new Set(["participated_in", "led", "present_at", "witnessed", "took_part"]);
  function presenceOf(e) {
    const present = new Map(), absent = new Map();
    for (const li of adj[e]) for (const ci of L[li].cl) {
      const c = C[ci];
      if (c.o !== e || (N[c.s].k !== "person" && N[c.s].k !== "group")) continue;
      const m = c.pk === "absent_from" ? absent : PRESENT_PK.has(c.pk) ? present : null;
      if (!m) continue;
      if (!m.has(c.s)) m.set(c.s, []);
      m.get(c.s).push(ci);
    }
    return { present, absent };
  }
  const absentFrom = (i) => C.filter((c) => c.s === i && c.pk === "absent_from").map((c) => c.o);
  let absentCache = { e: -2, set: null };
  function absentSet() {
    let e = S.focus >= 0 && N[S.focus].k === "event" ? S.focus : -1;
    if (e < 0 && S.journey && S.journey.event >= 0) e = S.journey.event;
    if (e !== absentCache.e) absentCache = { e, set: e >= 0 ? new Set(presenceOf(e).absent.keys()) : null };
    return absentCache.set;
  }
  const predText = (c) => I18N["pred." + c.pk] || c.p;

  // the globe: the record's dated events at located places, one after another
  const yearOf = (i) => (N[i].mk && N[i].mk.length ? N[i].mk[0][0] : N[i].d && N[i].d.length ? N[i].d[0][0] : null);
  const MOVES = (() => {
    const ev = [];
    N.forEach((nd, i) => { if (nd.k === "event" && nd.pl !== undefined && N[nd.pl].geo && yearOf(i) !== null) ev.push({ i, y: yearOf(i), p: nd.pl }); });
    ev.sort((a, b) => a.y - b.y || a.i - b.i);
    const out = [];
    let prev = null;
    for (const e of ev) { if (prev && prev.p !== e.p) out.push({ a: prev.p, b: e.p, y: e.y, from: prev.i, to: e.i }); prev = e; }
    return out;
  })();
  const PLACE_COUNTS = { located: N.filter((x) => x.k === "place" && x.geo).length, places: N.filter((x) => x.k === "place").length };
  const LAND = (() => { try { return JSON.parse(byId("sky-land").textContent); } catch (e) { return []; } })();

  // translations of the flat views' own words (axis titles and the like), when they match an interface string
  const DECO_KEY = new Map();
  for (const k of Object.keys(EN)) if (!EN[k].includes("{") && !DECO_KEY.has(EN[k])) DECO_KEY.set(EN[k], k);
  const decoText = (s) => (S.lang === "ar" && DECO_KEY.has(s) ? I18N[DECO_KEY.get(s)] : s);

  // journeys: the learning journeys' selection rules, applied to the graph in this page
  const JOURNEYS = ["hijrah", "first_believers", "badr"];
  function buildJourney(key) {
    const stops = [], lit = new Set();
    const has = (i) => stops.some((s) => s.i === i);
    const yr = (i) => { const y = yearOf(i); return y === null ? Infinity : y; };
    const people = (i) => { for (const li of adj[i]) { const o = otherEnd(li, i); if (N[o].k === "person" || N[o].k === "group") lit.add(o); } };
    let line = true, event = -1, zoom = 3;
    if (key === "hijrah") {
      const named = [];
      N.forEach((nd, i) => { if ((nd.k === "event" || nd.k === "story") && /\bhijrah?\b/i.test(nd.nEn)) named.push(i); });
      named.sort((a, b) => yr(a) - yr(b) || (N[a].k === "story") - (N[b].k === "story") || a - b);
      for (const w of named) {
        if (!has(w)) stops.push({ i: w, why: { k: "named" } });
        const parts = C.filter((c) => c.pk === "part_of" && c.o === w).map((c) => c.s).sort((a, b) => yr(a) - yr(b) || a - b);
        for (const p of parts) if (!has(p)) stops.push({ i: p, why: { k: "part", w } });
      }
      stops.forEach((s) => people(s.i));
    } else if (key === "first_believers") {
      N.forEach((nd, i) => { if (nd.k === "story" && /makkan/i.test(nd.partl || "")) stops.push({ i, why: { k: "story", no: nd.no } }); });
      stops.sort((a, b) => (N[a.i].no || 999) - (N[b.i].no || 999));
      stops.forEach((s) => people(s.i));
    } else if (key === "badr") {
      line = false; zoom = 3.6;
      const named = [];
      N.forEach((nd, i) => { if ((nd.k === "event" || nd.k === "story") && /\bbadr\b/i.test(nd.nEn)) named.push(i); });
      named.sort((a, b) => (N[a].k === "story") - (N[b].k === "story") || yr(a) - yr(b) || (N[a].no || 0) - (N[b].no || 0));
      for (const w of named) stops.push({ i: w, why: { k: "named" } });
      event = named.find((i) => N[i].k === "event");
      if (event === undefined) event = -1;
      const present = new Map(), absent = new Map();
      for (const w of named) {
        const p = presenceOf(w);
        for (const [s, cis] of p.present) if (!present.has(s)) present.set(s, { w, ci: cis[0] });
        for (const [s] of p.absent) if (!absent.has(s)) absent.set(s, w);
      }
      for (const s of absent.keys()) present.delete(s);
      const byName = (a, b) => (a === LIGHT_I ? -1 : b === LIGHT_I ? 1 : N[a].nEn.localeCompare(N[b].nEn));
      for (const s of [...present.keys()].sort(byName)) stops.push({ i: s, why: { k: "present", w: present.get(s).w, ci: present.get(s).ci } });
      for (const s of [...absent.keys()].sort(byName)) stops.push({ i: s, why: { k: "absent", w: absent.get(s) } });
    }
    for (const s of stops) lit.add(s.i);
    return { key, stops, idx: stops.map((s) => s.i), lit: [...lit], line, event, zoom, k: 0, playing: false };
  }
  const LIGHT_I = META.light === undefined || META.light === null ? -1 : META.light;
