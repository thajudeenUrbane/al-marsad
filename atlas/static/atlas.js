/* Sky Atlas: the page. Reads the packed graph, builds the five views, the Record card,
   the guided tours, the index, the logbook and the Arabic interface. Every sentence a
   reader sees is either an interface string or a recorded claim with its source; the
   page computes positions and orders, never facts. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const EN = JSON.parse($("i18n-en").textContent);
  const AR = JSON.parse($("i18n-ar").textContent);
  const LAND = JSON.parse($("land").textContent);
  const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let STR = EN, LANG = "en";

  // ------------------------------------------------------------------ small helpers
  function t(key, vars) {
    let s = STR[key];
    if (s === undefined) s = EN[key];
    if (s === undefined) s = key;
    if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] !== undefined ? vars[k] : m));
    return s;
  }
  const NUM = { en: new Intl.NumberFormat("en"), ar: new Intl.NumberFormat("ar-EG") };
  const fmt = (x) => NUM[LANG].format(x);
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    if (attrs) for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") el.className = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else if (k === "text") el.textContent = v;
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const k of kids.flat(3)) {
      if (k === null || k === undefined || k === false) continue;
      el.append(k.nodeType ? k : document.createTextNode(String(k)));
    }
    return el;
  }
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage unavailable: nothing is kept */ } },
  };
  function hash01(s, salt) { // FNV-1a: the same item always gets the same jitter
    let x = 2166136261 ^ (salt || 0);
    for (let i = 0; i < s.length; i++) { x ^= s.charCodeAt(i); x = Math.imul(x, 16777619); }
    return ((x >>> 0) % 100000) / 100000;
  }
  function announce(s) { $("announce").textContent = s; }
  let toastTimer = 0;
  function toast(s) {
    const el = $("toast"); el.textContent = s; el.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, 3400);
  }

  // ------------------------------------------------------------------ data
  async function unpack() {
    const raw = atob($("atlas-data").textContent.trim());
    const bin = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) bin[i] = raw.charCodeAt(i);
    const text = await new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream("gzip"))).text();
    return JSON.parse(text);
  }

  let D, ND, CL, META, n, nc, LIGHT;
  let deg, adjStart, adj, KIND, firstMs;
  const KINDS = ["person", "group", "place", "event", "story"];
  const CLASS_ORDER = ["participation", "transmission", "social_political", "spatial", "kinship"];
  const LIST = { rashidun: new Map(), ten: new Map() };
  const FLAG_OPP = 1, FLAG_TURNED = 2, FLAG_BACK = 4;

  function model(d) {
    D = d; ND = d.nodes; CL = d.claims; META = d.meta;
    n = ND.k.length; nc = CL.s.length; LIGHT = META.light;
    KIND = ND.k.map((k) => META.kinds[k]);
    deg = new Int32Array(n);
    for (let c = 0; c < nc; c++) { deg[CL.s[c]]++; if (CL.o[c] !== CL.s[c]) deg[CL.o[c]]++; }
    adjStart = new Int32Array(n + 1);
    for (let i = 0; i < n; i++) adjStart[i + 1] = adjStart[i] + deg[i];
    adj = new Int32Array(adjStart[n]);
    const fill = adjStart.slice(0, n);
    for (let c = 0; c < nc; c++) {
      adj[fill[CL.s[c]]++] = c;
      if (CL.o[c] !== CL.s[c]) adj[fill[CL.o[c]]++] = c;
    }
    for (const L of META.lists) L.m.forEach((i, k) => LIST[L.key] && LIST[L.key].set(i, k));
    firstMs = (i) => (ND.ms ? ND.ms[i] : undefined);
  }
  const nf = (field, i) => (ND[field] ? ND[field][i] : undefined);
  const cf = (field, c) => (CL[field] ? CL[field][c] : undefined);
  const flags = (i) => nf("f", i) || 0;
  const isOpp = (i) => !!(flags(i) & FLAG_OPP);
  const isTurned = (i) => !!(flags(i) & FLAG_TURNED);
  const isBack = (i) => !!(flags(i) & FLAG_BACK);
  const pk = (c) => META.preds[CL.p[c]][0];
  const pclass = (c) => META.preds[CL.p[c]][2];
  const other = (c, i) => (CL.s[c] === i ? CL.o[c] : CL.s[c]);
  function claimsOf(i) { return adj.subarray(adjStart[i], adjStart[i + 1]); }
  function neighbours(i) {
    const out = new Set();
    for (const c of claimsOf(i)) out.add(other(c, i));
    out.delete(i);
    return out;
  }

  function nameOf(i) {
    if (i === LIGHT) return t("light.name");
    if (LANG === "ar") { const a = nf("ar", i); if (a) return a; }
    if (S.depth !== "discover") { const s = nf("sch", i); if (s) return s; }
    return ND.n[i];
  }
  function altNames(i) {
    const out = [];
    const a = nf("ar", i), s = nf("sch", i), en = ND.n[i];
    if (LANG === "ar") { if (a) out.push(s || en); }
    else { if (S.depth === "discover" && s) out.push(s); if (S.depth !== "discover" && s) out.push(en); }
    return { names: out, ar: LANG === "en" ? a : null, other: nf("other", i) || [] };
  }
  function predText(c) {
    const k = "pred." + pk(c);
    return LANG === "ar" && AR[k] ? AR[k] : META.preds[CL.p[c]][1];
  }
  const kindText = (i) => t("kind." + KIND[i]);

  // the order of people (E3): the Prophet ﷺ, the four, the ten, then recorded links;
  // those recorded as opposing him come last unless the record says they later accepted Islam
  function e3Key(i) {
    const tier = i === LIGHT ? 0 : LIST.rashidun.has(i) ? 1 : LIST.ten.has(i) ? 2 : isOpp(i) && !isTurned(i) ? 4 : 3;
    const within = tier === 1 ? LIST.rashidun.get(i) : tier === 2 ? LIST.ten.get(i) : -deg[i];
    return [tier, within];
  }
  function sortPeople(arr, mode) {
    const m = mode || "e3";
    const name = (i) => nameOf(i);
    return arr.slice().sort((a, b) => {
      if (m === "az") return name(a).localeCompare(name(b), LANG);
      if (m === "links") return deg[b] - deg[a] || name(a).localeCompare(name(b), LANG);
      if (m === "text") return (firstMs(a) ?? 1e9) - (firstMs(b) ?? 1e9) || name(a).localeCompare(name(b), LANG);
      const ka = e3Key(a), kb = e3Key(b);
      return ka[0] - kb[0] || ka[1] - kb[1] || name(a).localeCompare(name(b), LANG);
    });
  }

  // a citation in short (volume and page) and in full
  function citation(c, full) {
    const cs = cf("cs", c), cp = cf("cp", c);
    if (!cs) return null;
    if (full) return (cp !== undefined ? META.citp[cp] + ", " : "") + cs;
    const short = cs.split(";")[0];
    return t("cite.short", { where: short });
  }
  const msCite = new Map(); // milestone -> "vol. 1, p. 250", for the Book view's scale and first mentions
  function buildMsCite() {
    for (let c = 0; c < nc; c++) {
      const ms = cf("ms", c), cs = cf("cs", c);
      if (ms === undefined || !cs || msCite.has(ms)) continue;
      msCite.set(ms, cs.split(";")[0].replace(/pp\. (\d+)[–-]\d+/, "p. $1"));
    }
  }

  // ------------------------------------------------------------------ state
  const S = {
    depth: "discover", view: "sky", focus: -1, hover: -1, lit: null, litLines: null,
    show: { lines: true, names: true, background: true, turning: false, orbit: false,
      kinds: { person: true, group: true, place: true, event: true, story: true } },
    guide: null, trace: { from: -1, path: null, lineage: false }, lineageOf: -1, visible: null,
    labels: [], markers: [],
  };
  let R = null;
  const LOG_KEY = "marsad-atlas-log-v1";
  let LOG = store.get(LOG_KEY, null) || { seen: {}, events: {}, places: {}, ladders: 0, chains: 0, traces: 0, tours: {}, lineages: 0, recalls: 0, arabic: 0, done: {} };

  // ------------------------------------------------------------------ colours and shapes
  const COL = {
    person: [[0.86, 0.92, 1.0], [1.0, 0.86, 0.66], [1.0, 0.74, 0.52], [0.78, 0.79, 0.84]],
    event: [0.89, 0.71, 0.36], place: [0.34, 0.78, 0.72], story: [0.87, 0.56, 0.65], group: [0.65, 0.59, 0.91],
    dark: [0.1, 0.09, 0.09],
  };
  const LINE = { participation: [0.89, 0.71, 0.36], kinship: [0.86, 0.74, 0.8], social_political: [0.65, 0.59, 0.91], spatial: [0.34, 0.78, 0.72], transmission: [0.72, 0.9, 1.0] };
  const SHAPE = { person: 0, event: 1, place: 2, story: 3, group: 4 };
  function markStyle(i) {
    const k = KIND[i];
    if (k === "person") {
      if (isOpp(i) && !(S.show.turning && isTurned(i))) return [COL.dark, 5, 0];
      const tb = nf("tb", i);
      if (tb === undefined) return [COL.person[3], 0, 0];
      return [COL.person[tb], 0, [1, 0.7, 0.5][tb]];
    }
    return [COL[k], SHAPE[k], 0];
  }
  function cssColor(i) {
    const [c] = markStyle(i);
    return `rgb(${Math.round(c[0] * 255)},${Math.round(c[1] * 255)},${Math.round(c[2] * 255)})`;
  }
  function glyph(i) { // a small picture of the mark, for lists
    const cv = h("canvas", { class: "glyph", width: 28, height: 28, "aria-hidden": "true" });
    drawGlyph(cv.getContext("2d"), i === LIGHT ? "light" : KIND[i], i === LIGHT ? null : markStyle(i));
    return cv;
  }
  function drawGlyph(g, kind, style) {
    g.clearRect(0, 0, 28, 28);
    const c = style ? style[0] : [1, 0.9, 0.7], shape = style ? style[1] : -1;
    g.fillStyle = `rgb(${c.map((x) => Math.round(x * 255)).join(",")})`;
    g.strokeStyle = g.fillStyle;
    g.beginPath();
    if (kind === "light") {
      const gr = g.createRadialGradient(14, 14, 0, 14, 14, 13);
      gr.addColorStop(0, "#fffbe9"); gr.addColorStop(0.4, "rgba(240,200,120,0.8)"); gr.addColorStop(1, "rgba(240,200,120,0)");
      g.fillStyle = gr; g.arc(14, 14, 13, 0, 7); g.fill(); return;
    }
    if (shape === 0) g.arc(14, 14, 7, 0, 7);
    else if (shape === 1) { for (let k = 0; k < 8; k++) { const a = k * Math.PI / 4 - Math.PI / 2, r = k % 2 ? 3 : 11; g.lineTo(14 + Math.cos(a) * r, 14 + Math.sin(a) * r); } g.closePath(); }
    else if (shape === 2) { g.moveTo(14, 4); g.lineTo(24, 14); g.lineTo(14, 24); g.lineTo(4, 14); g.closePath(); }
    else if (shape === 3) { for (let k = 0; k < 6; k++) { const a = k * Math.PI / 3; g.lineTo(14 + Math.cos(a) * 9, 14 + Math.sin(a) * 9); } g.closePath(); g.lineWidth = 3; g.stroke(); return; }
    else if (shape === 4) { g.moveTo(14, 5); g.lineTo(23, 21); g.lineTo(5, 21); g.closePath(); }
    else if (shape === 5) { g.arc(14, 14, 8, 0, 7); g.fillStyle = "#1a1716"; g.fill(); g.lineWidth = 1.6; g.strokeStyle = "#d46446"; g.stroke(); return; }
    g.fill();
  }

  // ------------------------------------------------------------------ the five views
  const VIEWS = ["sky", "book", "time", "map", "lineage"];
  const BOOK_W = 2600;
  function viewPositions(view) {
    const pos = new Float32Array(n * 3), vis = new Uint8Array(n);
    const put = (i, x, y, z) => { pos[3 * i] = x; pos[3 * i + 1] = y; pos[3 * i + 2] = z; vis[i] = 1; };
    const jit = (i, s) => hash01(ND.id[i], s);
    if (view === "sky") {
      pos.set(D.pos); vis.fill(1);
    } else if (view === "book") {
      const max = META.ms_max || 1;
      for (let i = 0; i < n; i++) {
        if (i === LIGHT) { put(i, -BOOK_W / 2 - 240, 900, 0); continue; }
        const ms = firstMs(i), k = KIND[i];
        if (ms === undefined) { // not named in Ibn Hishām's text: a column of their own on the left
          put(i, -BOOK_W / 2 - 120 - jit(i, 1) * 240, -560 + jit(i, 2) * 1120, (jit(i, 3) - 0.5) * 40); continue;
        }
        const x = -BOOK_W / 2 + (ms / max) * BOOK_W;
        if (k === "event") put(i, -BOOK_W / 2 + ((nf("mt", i) ?? ms) / max) * BOOK_W, 0, 0);
        else if (k === "place") put(i, x, -60 - jit(i, 1) * 180, (jit(i, 3) - 0.5) * 30);
        else if (k === "group") put(i, x, -290, 0);
        else if (isBack(i)) put(i, x, 470 + jit(i, 1) * 260, (jit(i, 3) - 0.5) * 30);
        else put(i, x, 50 + jit(i, 1) * 360, (jit(i, 3) - 0.5) * 30);
      }
    } else if (view === "time") {
      for (let i = 0; i < n; i++) {
        if (i === LIGHT) { put(i, 0, 760, 0); continue; }
        const yr = nf("yr", i);
        if (yr === undefined) continue;
        const x = (yr - 628) * 80, k = KIND[i];
        if (k === "event" || k === "story") put(i, x, k === "story" ? -90 : 0, 0);
        else if (k === "place") put(i, x, -180 - jit(i, 1) * 80, 0);
        else put(i, x + (jit(i, 2) - 0.5) * 30, 50 + jit(i, 1) * 420, (jit(i, 3) - 0.5) * 30);
      }
    } else if (view === "map") {
      const groups = new Map();
      for (let i = 0; i < n; i++) {
        if (i === LIGHT) { put(i, 0, 520, 0); continue; }
        const g = nf("geo", i);
        if (g) { const p = geo(g[0], g[1]); put(i, p[0], 0, p[1]); continue; }
        const pl = nf("pl", i);
        if (pl !== undefined && nf("geo", pl)) { if (!groups.has(pl)) groups.set(pl, []); groups.get(pl).push(i); }
      }
      for (const [pl, items] of groups) { // gathered round their recorded place, in a fixed order
        const c = geo(nf("geo", pl)[0], nf("geo", pl)[1]);
        items.sort((a, b) => ND.k[a] - ND.k[b] || (ND.id[a] < ND.id[b] ? -1 : 1));
        items.forEach((i, k) => {
          const r = 16 + 6.5 * Math.sqrt(k + 1), a = k * 2.39996;
          put(i, c[0] + Math.cos(a) * r, 4 + (KIND[i] === "event" ? 10 : 0), c[1] + Math.sin(a) * r);
        });
      }
    } else if (view === "lineage") {
      const f = S.lineageOf;
      if (f >= 0) {
        const tree = lineage(f);
        for (const [i, [x, y]] of tree.at) put(i, x, y, 0);
      }
      if (!vis[LIGHT]) put(LIGHT, 0, 900, 0);
    }
    return { pos, vis };
  }
  const GEO_K = 62;
  const geo = (lon, lat) => [(lon - 41) * GEO_K, -(lat - 22) * GEO_K];

  // ancestors (up to 14 generations), descendants (3), spouses and siblings, on a plane
  function kin(i) {
    const parents = [], children = [], spouses = [], siblings = [];
    for (const c of claimsOf(i)) {
      const p = pk(c), o = other(c, i);
      if (p === "father_of" || p === "mother_of") (CL.o[c] === i ? parents : children).push([o, c]);
      else if (p === "spouse_of") spouses.push([o, c]);
      else if (p === "sibling_of") siblings.push([o, c]);
    }
    const uniq = (a) => { const s = new Set(); return a.filter(([x]) => (s.has(x) ? false : (s.add(x), true))); };
    return { parents: uniq(parents), children: uniq(children), spouses: uniq(spouses), siblings: uniq(siblings) };
  }
  function lineage(f) {
    const at = new Map(), levels = new Map();
    const add = (i, lv) => { if (at.has(i)) return false; at.set(i, null); if (!levels.has(lv)) levels.set(lv, []); levels.get(lv).push(i); return true; };
    add(f, 0);
    let front = [f];
    for (let lv = 1; lv <= 14 && front.length; lv++) {
      const next = [];
      for (const x of front) for (const [p] of kin(x).parents) if (add(p, lv)) next.push(p);
      front = next;
    }
    front = [f];
    for (let lv = -1; lv >= -3 && front.length; lv--) {
      const next = [];
      for (const x of front) for (const [c] of sortPeople(kin(x).children.map((z) => z[0]), "az").map((z) => [z])) if (add(c, lv)) next.push(c);
      front = next;
    }
    const k0 = kin(f);
    for (const [s] of k0.spouses) add(s, 0);
    for (const [s] of k0.siblings) add(s, 0);
    let width = 0;
    for (const [lv, items] of levels) {
      const gap = lv === 0 ? 120 : Math.max(46, Math.min(130, 1600 / items.length));
      if (lv === 0) items.sort((a, b) => (a === f ? -1 : b === f ? 1 : 0));
      items.forEach((i, k) => {
        let x = (k - (items.length - 1) / 2) * gap;
        if (lv === 0) x = i === f ? 0 : (k % 2 ? 1 : -1) * Math.ceil(k / 2) * gap;
        at.set(i, [x, lv * 92]);
      });
      width = Math.max(width, items.length * gap);
    }
    return { at, levels, width, up: Math.max(0, ...[...levels.keys()]), down: Math.min(0, ...[...levels.keys()]) };
  }

  function viewCamera(view) {
    if (view === "sky") return { target: [0, 0, 0], dist: 2650, yaw: 0.62, pitch: 0.3 };
    if (view === "book") return { target: [0, 120, 0], dist: 3600, yaw: 0, pitch: 0 };
    if (view === "time") return { target: [180, 220, 0], dist: 3200, yaw: 0, pitch: 0 };
    if (view === "map") return { target: [0, 0, 120], dist: 1900, yaw: 0, pitch: 1.05 };
    if (view === "lineage") {
      if (S.lineageOf < 0) return { target: [0, 0, 0], dist: 1600, yaw: 0, pitch: 0 };
      const T = lineage(S.lineageOf);
      const mid = (T.up + T.down) / 2 * 92, span = Math.max((T.up - T.down) * 92 + 200, T.width * 0.7);
      return { target: [0, mid, 0], dist: Math.max(700, Math.min(5200, span * 1.5)), yaw: 0, pitch: 0 };
    }
  }

  function setView(view, opts) {
    if (view === "lineage") {
      const f = (opts && opts.of !== undefined) ? opts.of : S.focus;
      if (f < 0 || KIND[f] !== "person") { toast(t("lineage.need")); return; }
      S.lineageOf = f; LOG.lineages++; saveLog(); checkMilestones();
    }
    S.view = view;
    const v = viewPositions(view);
    S.visible = v.vis;
    R.morphTo(v.pos, 1000);
    R.setExtra(view === "map" ? landLines() : null);
    if (!opts || opts.camera !== false) R.flyTo(viewCamera(view), 1100);
    document.querySelectorAll(".views button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.view === view)));
    restyle();
    caption();
    here();
  }
  let landCache = null;
  function landLines() {
    if (landCache) return landCache;
    const pts = [], cols = [];
    for (const ring of LAND) {
      for (let k = 0; k + 3 < ring.length; k += 2) {
        const a = ring.slice(k, k + 2), b = ring.slice(k + 2, k + 4);
        if (Math.abs(a[0] - b[0]) > 90) continue;
        if (a[0] < -30 || a[0] > 110 || a[1] < -20 || a[1] > 65) continue;
        const p = geo(a[0], a[1]), q = geo(b[0], b[1]);
        pts.push(p[0], 0, p[1], q[0], 0, q[1]);
        cols.push(0.34, 0.6, 0.62, 0.32, 0.34, 0.6, 0.62, 0.32);
      }
    }
    landCache = { pos: new Float32Array(pts), col: new Float32Array(cols) };
    return landCache;
  }

  // ------------------------------------------------------------------ emphasis and drawing
  function visibleNow(i) {
    if (i === LIGHT) return false;
    if (S.visible && !S.visible[i]) return false;
    if (!S.show.kinds[KIND[i]]) return false;
    if (!S.show.background && isBack(i) && !(S.lit && S.lit.has(i))) return false;
    return true;
  }
  let pairsCache = null;
  function linkPairs() { // one line per pair and kind of relationship
    if (pairsCache) return pairsCache;
    const seen = new Set(), out = [];
    for (let c = 0; c < nc; c++) {
      const a = Math.min(CL.s[c], CL.o[c]), b = Math.max(CL.s[c], CL.o[c]);
      if (a === b) continue;
      const key = a * 9000 * 8 + b * 8 + CLASS_ORDER.indexOf(pclass(c));
      if (seen.has(key)) continue;
      seen.add(key); out.push([a, b, pclass(c)]);
    }
    pairsCache = out;
    return out;
  }
  function restyle() {
    const cols = new Float32Array(n * 4), shapes = new Float32Array(n), glows = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const [c, s, g] = markStyle(i);
      let a = visibleNow(i) ? 1 : 0;
      if (a && S.lit && !S.lit.has(i)) a = 0.11;
      if (a && KIND[i] === "person" && nf("tb", i) === undefined && !isOpp(i)) a *= 0.86;
      cols.set([c[0], c[1], c[2], a], 4 * i);
      shapes[i] = s; glows[i] = a > 0.5 ? g : 0;
    }
    R.setStyle(cols, shapes, glows);
    // lines
    const pairs = [], lc = [];
    if (S.show.lines) {
      const flat = S.view !== "sky";
      for (const [a, b, cls] of linkPairs()) {
        if (!visibleNow(a) && a !== LIGHT) continue;
        if (!visibleNow(b) && b !== LIGHT) continue;
        let al;
        const touchesLight = a === LIGHT || b === LIGHT;
        if (S.litLines) al = S.litLines.has(a * 100000 + b) ? 0.7 : 0;
        else if (S.lit) al = (S.lit.has(a) && S.lit.has(b)) ? (touchesLight ? 0.18 : 0.34) : 0;
        else al = touchesLight ? 0 : (flat ? 0.018 : 0.04);
        if (S.view === "lineage" && cls !== "kinship") al = 0;
        if (al <= 0) continue;
        if (touchesLight && S.view === "map") continue;
        const col = LINE[cls];
        pairs.push(a, b); lc.push(col[0], col[1], col[2], al);
      }
    }
    R.setLines(new Int32Array(pairs), new Float32Array(lc));
    buildLabels();
    R.requestDraw();
  }
  function emphasise(set, lines) { S.lit = set; S.litLines = lines || null; restyle(); }

  function buildLabels() {
    const L = [];
    const rtl = LANG === "ar";
    const add = (i, pri, opts) => { if (i < 0 || i === LIGHT || !visibleNow(i)) return; L.push(Object.assign({ i, pri, text: nameOf(i), rtl }, opts || {})); };
    if (S.show.names) {
      if (S.lit) {
        const arr = sortPeople([...S.lit].filter((i) => i !== LIGHT));
        arr.slice(0, 160).forEach((i, k) => add(i, 60 - k * 0.2, { color: KIND[i] === "event" ? "#f0cf8a" : undefined }));
      } else {
        for (let i = 0; i < n; i++) {
          if (KIND[i] === "event" && (S.view !== "sky" || firstMs(i) !== undefined)) add(i, 20 + Math.min(deg[i], 400) / 100, { color: "#f0cf8a", size: 12 });
          else if (LIST.ten.has(i)) add(i, 30 - LIST.ten.get(i) * 0.1, { bold: true });
          else if (KIND[i] === "story" && S.view === "sky") add(i, 10, { color: "#efb3c4", size: 11.5 });
          else if (KIND[i] === "place" && S.view === "map" && nf("geo", i)) add(i, 40, { color: "#8fe0d5", bold: true });
        }
        if (S.view === "time" || S.view === "book") for (let i = 0; i < n; i++) if (KIND[i] === "person" && deg[i] > 40 && !isBack(i)) add(i, 5 + deg[i] / 200);
      }
      if (S.view === "lineage") for (let i = 0; i < n; i++) if (S.visible && S.visible[i]) add(i, 15, { size: 11.5 });
    }
    if (S.guide) for (const m of S.markers) add(m.i, m.now ? 98 : 90, { bold: true, force: !!m.now, color: "#ffe1a0" });
    if (S.focus >= 0) add(S.focus, 100, { bold: true, force: true, size: 14, color: "#fff4d6" });
    S.labels = L;
  }

  // ------------------------------------------------------------------ the renderer's hooks
  const api = {
    lightIndex: -1,
    background: [0.027, 0.039, 0.078],
    fontName: getComputedStyle(document.documentElement).getPropertyValue("--f-name") || "Georgia, serif",
    lightPos: (cur) => [cur[3 * LIGHT], cur[3 * LIGHT + 1], cur[3 * LIGHT + 2]],
    lightLabel: () => t("light.label"),
    labels: () => {
      const out = S.labels.slice();
      if (S.hover >= 0 && S.hover !== S.focus && S.hover !== LIGHT) out.push({ i: S.hover, pri: 95, text: nameOf(S.hover), bold: true, force: true, rtl: LANG === "ar" });
      return out;
    },
    underlay: (ctx, v) => drawUnderlay(ctx, v),
    overlay: (ctx, v) => drawOverlayMarks(ctx, v),
    onTap: (i) => {
      if (i === LIGHT) { focus(LIGHT); return; }
      if (i >= 0) focus(i);
      else if (!S.guide && S.focus >= 0) clearFocus();
    },
    onHover: (i, x, y) => {
      if (i === S.hover) { moveTip(x, y); return; }
      S.hover = i;
      const tip = $("tip");
      if (i < 0) { tip.hidden = true; R.requestDraw(); return; }
      tip.replaceChildren(h("b", null, nameOf(i)), h("span", null, kindText(i) + (contextLine(i) ? " · " + contextLine(i) : "")));
      tip.hidden = false; moveTip(x, y);
      R.requestDraw();
    },
    onCamera: () => {},
    tick: () => {
      if (!S.show.orbit || reduced) return false;
      R.nudge(0.0016);
      return true;
    },
  };
  function moveTip(x, y) {
    const tip = $("tip");
    if (tip.hidden || x === undefined) return;
    const [W] = R.size();
    tip.style.left = Math.min(x + 16, W - 290) + "px"; tip.style.top = (y + 14) + "px";
  }

  function drawUnderlay(ctx, v) {
    ctx.save();
    ctx.font = `12px ${api.fontName}`;
    const line = (a, b, style, w, dash) => {
      const p = v.project(a), q = v.project(b);
      if (!p || !q) return;
      ctx.strokeStyle = style; ctx.lineWidth = w || 1; ctx.setLineDash(dash || []);
      ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]); ctx.stroke();
    };
    const label = (pt, s, color, align) => {
      const p = v.project(pt); if (!p) return;
      ctx.fillStyle = color || "rgba(236,230,214,0.6)"; ctx.textAlign = align || "center"; ctx.textBaseline = "top";
      ctx.fillText(s, p[0], p[1]);
    };
    if (S.view === "sky" && !R.isMoving()) {
      // the ecliptic of the record: the spiral the events lie on, in the order of the text
      ctx.setLineDash([2, 5]); ctx.strokeStyle = "rgba(226,180,92,0.28)"; ctx.lineWidth = 1;
      ctx.beginPath();
      let started = false;
      for (let k = 0; k <= 480; k++) {
        const p = v.project(spiral(k / 480));
        if (!p) { started = false; continue; }
        if (!started) { ctx.moveTo(p[0], p[1]); started = true; } else ctx.lineTo(p[0], p[1]);
      }
      ctx.stroke(); ctx.setLineDash([]);
      if (!S.lit) {
        label(spiral(0), t("sky.ecliptic.start"), "rgba(240,207,138,0.85)");
        label(spiral(1), t("sky.ecliptic.end"), "rgba(240,207,138,0.85)");
      }
      // the ring of the 50 Stories
      ctx.strokeStyle = "rgba(223,143,166,0.2)"; ctx.beginPath(); started = false;
      for (let k = 0; k <= 160; k++) {
        const a = k / 160 * Math.PI * 2, x = Math.cos(a) * 700, y = Math.sin(a) * 700;
        const p = v.project([x, y * Math.sin(0.4091), y * Math.cos(0.4091)]);
        if (!p) { started = false; continue; }
        if (!started) { ctx.moveTo(p[0], p[1]); started = true; } else ctx.lineTo(p[0], p[1]);
      }
      ctx.stroke();
    } else if (S.view === "book") {
      const y0 = 0, x0 = -BOOK_W / 2, x1 = BOOK_W / 2, max = META.ms_max || 1;
      line([x0, y0, 0], [x1, y0, 0], "rgba(226,180,92,0.5)", 1.2);
      const ticks = [...msCite.keys()].sort((a, b) => a - b);
      let lastX = -1e9;
      for (const ms of ticks) {
        const x = x0 + ms / max * BOOK_W;
        const p = v.project([x, y0, 0]); if (!p || p[0] - lastX < 120) continue;
        lastX = p[0];
        line([x, y0 - 14, 0], [x, y0 + 14, 0], "rgba(226,180,92,0.5)", 1);
        ctx.fillStyle = "rgba(236,230,214,0.62)"; ctx.textAlign = "center"; ctx.textBaseline = "top";
        ctx.fillText(msCite.get(ms), p[0], p[1] + 18);
      }
      label([x0 - 240, -600, 0], t("book.lane.missing"), "rgba(236,230,214,0.55)");
      label([x1 + 20, 260, 0], t("book.lane.people"), "rgba(220,232,255,0.6)", "left");
      label([x1 + 20, 600, 0], t("book.lane.background"), "rgba(200,202,214,0.5)", "left");
      label([x1 + 20, 10, 0], t("book.lane.events"), "rgba(240,207,138,0.75)", "left");
      label([x1 + 20, -140, 0], t("book.lane.places"), "rgba(143,224,213,0.65)", "left");
      label([0, -360, 0], t("book.axis"), "rgba(240,207,138,0.8)");
    } else if (S.view === "time") {
      line([(605 - 628) * 80, 0, 0], [(660 - 628) * 80, 0, 0], "rgba(226,180,92,0.5)", 1.2);
      for (let y = 605; y <= 660; y += 5) {
        const x = (y - 628) * 80;
        line([x, -14, 0], [x, 14, 0], "rgba(226,180,92,0.5)");
        label([x, -26, 0], y === 620 ? "620" : String(y) + (y === 610 ? " " + t("time.ce") : ""));
      }
      line([(622 - 628) * 80, -40, 0], [(622 - 628) * 80, 560, 0], "rgba(226,180,92,0.22)", 1, [3, 5]);
      label([(622 - 628) * 80, 580, 0], t("time.ah1"), "rgba(240,207,138,0.8)");
      label([(600 - 628) * 80, 300, 0], t("time.lane.people"), "rgba(220,232,255,0.6)");
    } else if (S.view === "map") {
      for (let lon = 20; lon <= 70; lon += 10) line([geo(lon, -5)[0], 0, geo(lon, -5)[1]], [geo(lon, 50)[0], 0, geo(lon, 50)[1]], "rgba(86,198,184,0.08)");
      for (let lat = 0; lat <= 50; lat += 10) line([geo(15, lat)[0], 0, geo(15, lat)[1]], [geo(75, lat)[0], 0, geo(75, lat)[1]], "rgba(86,198,184,0.08)");
    } else if (S.view === "lineage" && S.lineageOf >= 0) {
      const T = lineage(S.lineageOf);
      for (const [i, [x, y]] of T.at) {
        for (const [p] of kin(i).parents) if (T.at.has(p)) {
          const [px, py] = T.at.get(p);
          if (py === y + 92) line([x, y, 0], [px, py, 0], "rgba(223,190,200,0.4)", 1.2);
        }
      }
      for (const lv of T.levels.keys()) if (lv !== 0) label([-(T.width / 2) - 120, lv * 92 + 8, 0], t(lv > 0 ? "lineage.up" : "lineage.down", { n: fmt(Math.abs(lv)) }), "rgba(236,230,214,0.45)");
    }
    ctx.restore();
  }
  function spiral(tt) {
    const R0 = 430, y = (1 - 2 * tt) * 0.86 * R0, rr = Math.sqrt(Math.max(R0 * R0 - y * y, 0)), a = tt * 4.5 * Math.PI * 2;
    return [rr * Math.cos(a), y, rr * Math.sin(a)];
  }
  function drawOverlayMarks(ctx, v) {
    const ring = (i, color, w, extra) => {
      if (i < 0 || i === LIGHT) return;
      const x = v.sx[i], y = v.sy[i];
      if (x < -100) return;
      const r = v.size(v.sw[i], i) / 2 + (extra || 7);
      ctx.strokeStyle = color; ctx.lineWidth = w; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
    };
    ctx.save();
    for (const m of S.markers) {
      const x = v.sx[m.i], y = v.sy[m.i];
      if (x < -100) continue;
      ring(m.i, m.now ? "#e2b45c" : "rgba(226,180,92,0.6)", m.now ? 2 : 1.2, m.now ? 10 : 7);
      if (m.label) {
        ctx.font = `600 11px ${api.fontName}`; ctx.fillStyle = "#1b1407";
        const r = v.size(v.sw[m.i], m.i) / 2 + (m.now ? 10 : 7);
        ctx.beginPath(); ctx.arc(x + r * 0.75, y - r * 0.75, 9, 0, Math.PI * 2); ctx.fillStyle = "#e2b45c"; ctx.fill();
        ctx.fillStyle = "#1b1407"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(m.label, x + r * 0.75, y - r * 0.75 + 0.5);
      }
    }
    if (S.trace.path) {
      const p = S.trace.path;
      ctx.strokeStyle = "rgba(255,225,160,0.9)"; ctx.lineWidth = 2; ctx.setLineDash([6, 4]);
      ctx.beginPath();
      p.forEach(([i], k) => { const x = v.sx[i], y = v.sy[i]; if (k) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
      ctx.stroke(); ctx.setLineDash([]);
    }
    if (S.focus >= 0) ring(S.focus, "#fff1cc", 1.6, 9);
    if (S.hover >= 0 && S.hover !== S.focus) ring(S.hover, "rgba(255,241,204,0.6)", 1, 6);
    ctx.restore();
  }

  // ------------------------------------------------------------------ focus and the Record card
  function focus(i, opts) {
    S.focus = i;
    if (i !== LIGHT) markSeen(i);
    const set = new Set([i, ...neighbours(i)]);
    if (!opts || !opts.keepEmphasis) emphasise(set);
    else restyle();
    if ((!opts || opts.fly !== false) && i !== LIGHT && S.visible && S.visible[i]) {
      R.flyToNode(i, spread(i, set));
    }
    openRecord(i);
    here();
    announce(t("announce.focus", { name: nameOf(i) }));
  }
  function spread(i, set) { // how far to stand back to see an item with everything it touches
    const p = R.targetPos(i);
    const ds = [];
    for (const j of set) {
      if (j === LIGHT || !visibleNow(j)) continue;
      const q = R.targetPos(j);
      ds.push(Math.hypot(q[0] - p[0], q[1] - p[1], q[2] - p[2]));
    }
    ds.sort((a, b) => a - b);
    const r = ds.length ? ds[Math.floor(ds.length * 0.85)] : 60;
    return Math.max(240, Math.min(3800, r * 2.8 + 120));
  }
  function clearFocus() {
    S.focus = -1; S.trace.path = null;
    emphasise(null);
    closeRecord();
    here();
  }
  function openRecord(i) {
    $("record").hidden = false;
    $("app").classList.add("has-record");
    renderRecord(i);
    $("record-body").scrollTop = 0;
    insets();
  }
  function closeRecord() { $("record").hidden = true; $("app").classList.remove("has-record"); insets(); }

  function nameBtn(i, self) {
    if (i === self) return h("b", { class: i === LIGHT ? "link light" : "" }, nameOf(i));
    return h("button", { type: "button", class: "link" + (i === LIGHT ? " light" : ""), onclick: () => focus(i) }, nameOf(i));
  }
  function chip(i) {
    return h("button", { type: "button", class: "person-chip" + (isOpp(i) && !isTurned(i) ? " dark" : ""), onclick: () => focus(i), title: kindText(i) }, glyph(i), nameOf(i));
  }
  function chips(list, limit) {
    const box = h("div", { class: "people" });
    const lim = limit || 24;
    const draw = (k) => { box.replaceChildren(...list.slice(0, k).map(chip)); if (list.length > k) box.append(h("button", { type: "button", class: "chip small", onclick: () => draw(list.length) }, t("more.all", { n: fmt(list.length) }))); };
    draw(lim);
    return box;
  }
  function sourceTag(c) {
    const s = CL.src[c];
    if (s < 0) return null;
    const src = META.sources[s];
    return h("span", { class: "tag" + (src.ai ? " ai" : ""), title: src.label }, src.ai ? t("source.ai", { label: src.label }) : src.label);
  }
  function statusTag(c) {
    const st = CL.st[c];
    return h("span", { class: "tag prop" }, st === 1 ? t("status.proposed") : st === 0 ? t("status.record") : t("status.other"));
  }
  function claimRow(c, self) {
    const row = h("li", null, h("span", { class: "sent" }, nameBtn(CL.s[c], self), " ", h("span", { class: "pred" }, predText(c)), " ", nameBtn(CL.o[c], self)));
    if (S.depth === "discover") return row;
    const meta = h("div", { class: "meta" }, statusTag(c), sourceTag(c));
    const role = cf("r", c); if (role) meta.append(h("span", null, t("claim.role", { role })));
    for (const q of cf("q", c) || []) { const key = "qual." + META.quals[q].replace(/\W+/g, "_"); meta.append(h("span", { class: "tag" }, STR[key] || EN[key] || META.quals[q])); }
    const sty = cf("sty", c); if (sty !== undefined) meta.append(h("span", null, t("claim.story"), " ", nameBtn(sty)));
    row.append(meta);
    const cit = citation(c, S.depth === "research");
    if (cit) row.append(h("div", { class: "cite" }, cit));
    const b = cf("b", c); if (b !== undefined) row.append(h("div", { class: "cite" }, t("claim.basis", { text: META.strings[b] })));
    if (S.depth === "research") {
      const g = cf("g", c); if (g) row.append(h("div", { class: "gloss" }, t("claim.gloss"), " ", g));
      const id = cf("id", c); if (id) row.append(h("div", { class: "cite" }, t("claim.id", { id })));
    }
    const rep = cf("rep", c), ch = cf("chain", c);
    if (rep !== undefined || ch !== undefined) row.append(ladder(c, rep, ch));
    return row;
  }
  function ladder(c, rep, ch) {
    const d = h("details", { class: "how" }, h("summary", null, t("ladder.how")));
    if (S.depth === "research") d.open = true;
    d.addEventListener("toggle", () => { if (d.open) { LOG.ladders++; if (ch !== undefined) LOG.chains++; saveLog(); checkMilestones(); } }, { once: true });
    const box = h("div", { class: "ladder" });
    if (rep !== undefined) {
      const r = D.reports[rep];
      box.append(h("p", null, h("b", null, t("ladder.report")), " ", r.label || "—"));
      if (r.genre || r.asc) box.append(h("p", { class: "muted" }, [r.genre, r.asc && t("ladder.asc", { v: r.asc })].filter(Boolean).join(" · ")));
      if (r.cit) box.append(h("p", { class: "cite" }, r.cit));
      if (r.grades && r.grades.length) for (const g of r.grades) box.append(h("p", null, t("ladder.grade", { grade: g.grade || "—", by: g.by || "—", scheme: g.scheme || "—" })));
      else box.append(h("p", { class: "muted" }, t("ladder.nograde")));
    }
    if (ch !== undefined) {
      const C = D.chains[ch];
      box.append(h("p", null, h("b", null, t("ladder.chain")), " ", C.label || ""));
      const ol = h("ol", { class: "plain path" });
      for (const [a, b, ord, mode, chk] of C.links) ol.append(h("li", null, nameBtn(a), " → ", nameBtn(b), mode ? h("span", { class: "muted" }, " · " + t("ladder.mode", { mode })) : null, chk ? h("span", { class: "muted" }, " · " + chk) : null));
      box.append(ol);
    }
    d.append(box);
    return d;
  }

  function groupClaims(i) {
    const groups = new Map();
    for (const c of claimsOf(i)) {
      const key = pk(c) + (CL.s[c] === i ? ">" : "<");
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(c);
    }
    const arr = [...groups.entries()];
    arr.sort((a, b) => CLASS_ORDER.indexOf(pclass(a[1][0])) - CLASS_ORDER.indexOf(pclass(b[1][0])) || b[1].length - a[1].length);
    for (const [, cs] of arr) cs.sort((a, b) => (cf("ms", a) ?? 1e9) - (cf("ms", b) ?? 1e9));
    return arr;
  }
  function othersBy(i, preds, dir) { // the other ends of i's claims with these predicates
    const out = new Set();
    for (const c of claimsOf(i)) {
      if (preds && !preds.includes(pk(c))) continue;
      if (dir === ">" && CL.s[c] !== i) continue;
      if (dir === "<" && CL.o[c] !== i) continue;
      out.add(other(c, i));
    }
    out.delete(i);
    return [...out];
  }
  const textOrder = (i) => (KIND[i] === "event" ? (nf("mt", i) ?? firstMs(i)) : firstMs(i)) ?? 1e9;
  const byText = (arr) => arr.slice().sort((a, b) => textOrder(a) - textOrder(b) || nameOf(a).localeCompare(nameOf(b), LANG));
  function firstMention(i) {
    const ms = firstMs(i);
    if (ms === undefined) return null;
    const where = msCite.get(ms);
    return where ? t("first.mention", { where }) + (S.depth === "research" ? " · " + t("first.ms", { ms }) : "") : null;
  }
  function placesOf(i) { return othersBy(i, ["took_place_at", "occurred_at", "migrated_to", "died_at", "born_at", "resided_in", "visited", "buried_at", "travelled_via", "sheltered_at", "migrated_from"]).filter((j) => KIND[j] === "place"); }
  function eventsOf(i) { return byText(othersBy(i).filter((j) => KIND[j] === "event")); }
  function peopleAt(ev) {
    const groups = { led: new Set(), part: new Set(), died: new Set(), killed: new Set(), absent: new Set(), other: new Set() };
    for (const c of claimsOf(ev)) {
      const o = other(c, ev);
      if (KIND[o] !== "person" || o === ev) continue;
      const p = pk(c);
      if (p === "led") groups.led.add(o);
      else if (p === "participated_in" || p === "took_part" || p === "present_at" || p === "witnessed") groups.part.add(o);
      else if (p === "died_during") groups.died.add(o);
      else if (p === "absent_from") groups.absent.add(o);
      else groups.other.add(o);
    }
    for (const k of ["part", "died", "other"]) for (const x of groups.led) groups[k].delete(x);
    for (const x of groups.died) groups.part.delete(x);
    return groups;
  }
  function contextLine(i) {
    const k = KIND[i];
    if (k === "event") { const d = nf("d", i); return d ? d[0][2] : (firstMs(i) !== undefined ? msCite.get(firstMs(i)) || "" : ""); }
    if (k === "person") {
      if (isBack(i)) return t("ctx.lineage");
      const ev = eventsOf(i); return ev.length ? nameOf(ev[0]) : "";
    }
    if (k === "story") return t("ctx.story", { n: fmt(nf("no", i) || 0) });
    if (k === "place") { const ar = nf("ar", i); return LANG === "en" && ar ? ar : ""; }
    return "";
  }

  function renderRecord(i) {
    const body = $("record-body");
    const k = KIND[i];
    const out = [];
    const alt = i === LIGHT ? { names: [], ar: null, other: [] } : altNames(i);
    out.push(h("p", { class: "kind" }, glyph(i), i === LIGHT ? t("light.kind") : kindText(i)));
    out.push(h("h2", { class: "name" }, nameOf(i)));
    if (alt.names.length || alt.ar) out.push(h("p", { class: "alt" }, alt.names.join(" · "), alt.ar ? h("span", { class: "ar", lang: "ar", dir: "rtl" }, (alt.names.length ? " · " : "") + alt.ar) : null));
    // marks the sky draws, and why
    const tags = h("p", { class: "status-line" });
    if (i === LIGHT) tags.append(h("span", { class: "tag list" }, t("light.tag")));
    if (LIST.rashidun.has(i)) tags.append(h("span", { class: "tag list", title: t("list.proposed") }, t("list.rashidun")));
    if (LIST.ten.has(i)) tags.append(h("span", { class: "tag list", title: t("list.proposed") }, t("list.ten")));
    const tb = nf("tb", i);
    if (tb !== undefined) tags.append(h("span", { class: "tag" }, t("gen." + META.tb[tb])));
    if (isOpp(i)) tags.append(h("span", { class: "tag dark" }, isTurned(i) ? t("mark.turned") : t("mark.opponent")));
    if (isBack(i)) tags.append(h("span", { class: "tag" }, t("mark.background")));
    tags.append(h("span", { class: "tag" }, t("records.count", { n: fmt(deg[i]) })));
    if (S.depth === "research") tags.append(h("span", { class: "tag" }, t("coverage", { v: META.cov[ND.cv[i]] || "—" })));
    out.push(tags);
    const fm = firstMention(i);
    if (fm) out.push(h("p", { class: "cite" }, fm));

    // actions
    const acts = h("div", { class: "row", style: "margin-top:10px" });
    if (i !== LIGHT) acts.append(h("button", { type: "button", class: "chip primary small", onclick: () => startTour(dynamicTour(i)) }, t("act.guide")));
    if (k === "person" && i !== LIGHT && (kin(i).parents.length || kin(i).children.length)) acts.append(h("button", { type: "button", class: "chip small", onclick: () => setView("lineage", { of: i }) }, t("act.lineage")));
    if (k === "person" && i === LIGHT) acts.append(h("button", { type: "button", class: "chip small", onclick: () => setView("lineage", { of: i }) }, t("act.lineage")));
    if (S.trace.from >= 0 && S.trace.from !== i) acts.append(h("button", { type: "button", class: "chip small", onclick: () => trace(S.trace.from, i) }, t("act.trace_to", { name: nameOf(S.trace.from) })));
    acts.append(h("button", { type: "button", class: "chip small", "aria-pressed": String(S.trace.from === i), onclick: () => { S.trace.from = i; toast(t("trace.start_set", { name: nameOf(i) })); renderRecord(i); } }, t("act.trace_from")));
    out.push(acts);

    if (i === LIGHT) out.push(h("p", { class: "note" }, t("light.note")));
    if (isOpp(i)) out.push(oppNote(i));

    // facets by kind
    const facet = (title, ...kids) => h("section", { class: "facet" }, h("h3", null, title), ...kids);
    if (k === "event") {
      const d = nf("d", i);
      if (d) out.push(facet(t("facet.when"), ...d.map((x) => h("p", null, x[2]))));
      const pl = placesOf(i);
      if (pl.length) out.push(facet(t("facet.where"), chips(pl)));
      const g = peopleAt(i);
      const who = [];
      for (const key of ["led", "part", "died", "other", "absent"]) {
        const arr = sortPeople([...g[key]]);
        if (!arr.length) continue;
        who.push(h("p", { class: "muted" }, t("who." + key, { n: fmt(arr.length) })), chips(arr, S.depth === "discover" ? 18 : 40));
      }
      if (who.length) out.push(facet(t("facet.who"), ...who));
      const disp = nf("disp", i);
      if (disp) out.push(facet(t("facet.disputes"), ...disp.map((x) => h("div", { class: "note" }, h("p", null, x.q || ""), h("ul", null, (x.pos || []).map((p) => h("li", null, p)))))));
      const ev = byText(othersBy(i).filter((j) => KIND[j] === "event"));
      if (ev.length) out.push(facet(t("facet.events_linked"), chips(ev)));
    } else if (k === "person") {
      const ev = eventsOf(i);
      if (ev.length) out.push(facet(t("facet.events"), h("p", { class: "muted" }, t("facet.events_note")), chips(ev, S.depth === "discover" ? 14 : 40)));
      const K = kin(i);
      const fam = [];
      for (const key of ["parents", "children", "spouses", "siblings"]) {
        if (!K[key].length) continue;
        fam.push(h("p", { class: "muted" }, t("kin." + key, { n: fmt(K[key].length) })), chips(sortPeople(K[key].map((x) => x[0]), "e3"), 16));
      }
      if (fam.length) out.push(facet(t("facet.family"), ...fam));
      const pl = placesOf(i);
      if (pl.length) out.push(facet(t("facet.places"), chips(pl)));
      const tr = othersBy(i, ["narrated_from", "transmitted_to"]);
      if (tr.length) out.push(facet(t("facet.transmission"), chips(sortPeople(tr), 16)));
      const st = othersBy(i).filter((j) => KIND[j] === "story");
      if (st.length) out.push(facet(t("facet.stories"), chips(st.sort((a, b) => (nf("no", a) || 0) - (nf("no", b) || 0)))));
      const death = nf("death", i);
      if (death) out.push(facet(t("facet.death"), ...death.map((x) => h("p", null, x[2]))));
    } else if (k === "place") {
      const g = nf("geo", i);
      out.push(facet(t("facet.location"), h("p", null, g ? t("place.located", { lon: g[0], lat: g[1], conf: g[2] || "" }) : t("place.unlocated"))));
      const ev = byText(othersBy(i).filter((j) => KIND[j] === "event"));
      if (ev.length) out.push(facet(t("facet.events_here"), chips(ev)));
      const pp = sortPeople(othersBy(i).filter((j) => KIND[j] === "person"));
      if (pp.length) out.push(facet(t("facet.people_here"), chips(pp, 20)));
    } else if (k === "story") {
      const parts = [];
      if (nf("no", i)) parts.push(t("story.no", { n: fmt(nf("no", i)) }));
      if (nf("partl", i)) parts.push(nf("partl", i));
      out.push(facet(t("facet.story"), h("p", null, parts.join(" · ")), nf("work", i) !== undefined ? h("p", { class: "cite" }, META.sources[nf("work", i)].label) : null, h("p", { class: "note warn" }, t("story.note"))));
      const pp = sortPeople(othersBy(i).filter((j) => KIND[j] === "person"));
      if (pp.length) out.push(facet(t("facet.people_named"), chips(pp, 30)));
    } else if (k === "group") {
      const pp = sortPeople(othersBy(i).filter((j) => KIND[j] === "person"));
      if (pp.length) out.push(facet(t("facet.members"), chips(pp, 30)));
    }
    const gaps = nf("gaps", i);
    if (gaps && S.depth !== "discover") out.push(facet(t("facet.gaps"), ...gaps.map((g) => h("p", { class: "note" }, g))));

    // every record
    if (S.depth === "discover") {
      out.push(h("section", { class: "facet" }, h("p", { class: "muted" }, t("discover.more", { n: fmt(deg[i]) })),
        h("button", { type: "button", class: "chip small", onclick: () => setDepth("study") }, t("discover.study"))));
    } else {
      const groups = groupClaims(i);
      const box = h("section", { class: "facet" }, h("h3", null, t("facet.records", { n: fmt(deg[i]) })));
      const lim = i === LIGHT ? 6 : 12;
      for (const [, cs] of groups) {
        const ul = h("ul", { class: "plain claims" });
        const draw = (m) => { ul.replaceChildren(...cs.slice(0, m).map((c) => claimRow(c, i))); if (cs.length > m) ul.append(h("li", null, h("button", { type: "button", class: "chip small", onclick: () => draw(cs.length) }, t("more.all", { n: fmt(cs.length) })))); };
        draw(lim);
        box.append(h("p", { class: "muted", style: "margin:10px 0 0" }, h("span", { class: "pred" }, predText(cs[0])), " · ", fmt(cs.length)), ul);
      }
      out.push(box);
    }
    body.replaceChildren(...out);
  }
  function oppNote(i) {
    const basis = [];
    for (const c of claimsOf(i)) {
      const p = pk(c);
      if ((p === "fought_against" && (CL.s[c] === LIGHT || CL.o[c] === LIGHT)) || (p === "opposed" && CL.o[c] === LIGHT && CL.s[c] === i)) basis.push(c);
      if ((cf("q", c) || []).some((q) => META.quals[q] === "accepted Islam later")) basis.push(c);
    }
    return h("div", { class: "note warn" }, h("p", null, isTurned(i) ? t("mark.turned_note") : t("mark.opponent_note")),
      h("ul", { class: "plain claims" }, [...new Set(basis)].map((c) => claimRow(c, i))));
  }

  // ------------------------------------------------------------------ guided tours
  let TOURS = [];
  function buildTours() {
    const ecl = META.ecliptic.map(([i]) => i);
    const dated = [];
    for (let i = 0; i < n; i++) if (KIND[i] === "event" && nf("d", i) && nf("d", i)[0][0] !== null) dated.push(i);
    dated.sort((a, b) => nf("d", a)[0][0] - nf("d", b)[0][0] || nf("d", a)[0][1] - nf("d", b)[0][1] || nameOf(a).localeCompare(nameOf(b)));
    const stories = [];
    for (let i = 0; i < n; i++) if (KIND[i] === "story") stories.push(i);
    stories.sort((a, b) => (nf("no", a) || 0) - (nf("no", b) || 0));
    const opp = [];
    for (let i = 0; i < n; i++) if (isOpp(i)) opp.push(i);
    TOURS = [
      { key: "ecliptic", stops: ecl, kind: "events", featured: true },
      { key: "dated", stops: dated, kind: "events" },
      ...META.journeys.map((j) => ({ key: "j_" + j.key, stops: j.steps.filter((i) => !isBack(i)), kind: j.type, journey: j })),
      { key: "ten", stops: META.lists.find((l) => l.key === "ten").m.slice(), kind: "people" },
      { key: "stories", stops: stories, kind: "stories" },
      { key: "opposition", stops: byText(opp), kind: "people" },
    ].filter((x) => x.stops.length);
  }
  function tourTitle(T) {
    if (T.dynamic) return t("tour.dyn." + T.dynamic, { name: nameOf(T.of) });
    if (T.journey) return LANG === "ar" ? t("tour." + T.key + ".title") : T.journey.title;
    return t("tour." + T.key + ".title");
  }
  function tourLead(T) {
    if (T.dynamic) return t("tour.dyn." + T.dynamic + ".lead", { name: nameOf(T.of) });
    if (T.journey) return LANG === "ar" ? t("tour." + T.key + ".lead") : T.journey.lead;
    return t("tour." + T.key + ".lead");
  }
  function dynamicTour(i) {
    const k = KIND[i];
    if (k === "person") {
      const stops = [i, ...eventsOf(i)];
      const fam = kin(i);
      for (const key of ["parents", "spouses", "children"]) for (const [x] of fam[key]) if (!isBack(x) || key !== "parents") stops.push(x);
      return { key: "life", dynamic: "life", of: i, stops: [...new Set(stops)].slice(0, 60), kind: "mixed" };
    }
    if (k === "place") return { key: "place", dynamic: "place", of: i, stops: [i, ...byText(othersBy(i).filter((j) => KIND[j] === "event")), ...sortPeople(othersBy(i).filter((j) => KIND[j] === "person")).slice(0, 30)], kind: "mixed" };
    if (k === "event") return { key: "around", dynamic: "around", of: i, stops: [i, ...sortPeople(othersBy(i).filter((j) => KIND[j] === "person" && !isBack(j))).slice(0, 40)], kind: "mixed" };
    return { key: "around", dynamic: "around", of: i, stops: [i, ...sortPeople(othersBy(i)).slice(0, 40)], kind: "mixed" };
  }
  let playTimer = 0;
  function startTour(T, k) {
    if (!T || !T.stops.length) return;
    S.guide = { T, k: Math.max(0, Math.min(k || 0, T.stops.length - 1)) };
    closeDrawer();
    $("guide").hidden = false; $("guide").classList.remove("folded"); $("guide-min").setAttribute("aria-expanded", "true");
    $("app").classList.add("has-guide");
    $("welcome").hidden = true;
    if (S.view === "lineage") setView("sky", { camera: false });
    closeRecord();
    insets();
    goStop(S.guide.k);
  }
  function endTour() {
    stopPlay();
    S.guide = null; S.markers = [];
    $("guide").hidden = true; $("app").classList.remove("has-guide");
    clearFocus();
    insets();
  }
  function goStop(k) {
    const G = S.guide; if (!G) return;
    G.k = Math.max(0, Math.min(k, G.T.stops.length - 1));
    const i = G.T.stops[G.k];
    if (S.view === "lineage") setView("sky", { camera: false });
    if (S.view !== "sky" && S.visible && !S.visible[i]) setView("sky", { camera: false });
    S.focus = i;
    if (i !== LIGHT) markSeen(i);
    const set = new Set([i, ...neighbours(i)]);
    for (const j of G.T.stops.slice(Math.max(0, G.k - 1), G.k + 2)) set.add(j);
    S.markers = [];
    const prev = G.T.stops[G.k - 1], next = G.T.stops[G.k + 1];
    if (prev !== undefined) S.markers.push({ i: prev, label: fmt(G.k) });
    S.markers.push({ i, label: fmt(G.k + 1), now: true });
    if (next !== undefined) S.markers.push({ i: next, label: fmt(G.k + 2) });
    emphasise(set);
    if (i !== LIGHT) R.flyToNode(i, spread(i, set), reduced ? 0 : 1300);
    const tk = G.T.key + (G.T.of !== undefined ? ":" + ND.id[G.T.of] : "");
    LOG.tours[tk] = Math.max(LOG.tours[tk] || 0, G.k + 1);
    if (G.k === G.T.stops.length - 1) { LOG.done["tour:" + G.T.key] = 1; }
    saveLog(); checkMilestones();
    renderStop();
    here();
    announce(t("announce.stop", { k: fmt(G.k + 1), n: fmt(G.T.stops.length), name: nameOf(i) }));
  }
  function renderStop() {
    const G = S.guide; if (!G) return;
    const T = G.T, i = T.stops[G.k], k = KIND[i];
    $("guide-tour").textContent = tourTitle(T);
    $("guide-progress").textContent = t("guide.progress", { k: fmt(G.k + 1), n: fmt(T.stops.length) });
    $("guide-meter").style.width = ((G.k + 1) / T.stops.length * 100).toFixed(1) + "%";
    $("guide-prev").disabled = G.k === 0;
    $("guide-next").disabled = G.k === T.stops.length - 1;
    const left = h("div", null);
    left.append(h("p", { class: "kind" }, glyph(i), i === LIGHT ? t("light.kind") : kindText(i)));
    left.append(h("h2", { class: "stop-name" }, nameOf(i)));
    const alt = i === LIGHT ? null : altNames(i);
    if (alt && alt.ar) left.append(h("p", { class: "alt" }, h("span", { class: "ar", lang: "ar", dir: "rtl" }, alt.ar)));
    if (G.k === 0) left.append(h("p", { class: "muted" }, tourLead(T)));
    const facts = h("ul", { class: "plain claims" });
    if (k === "event") {
      const d = nf("d", i); if (d) facts.append(h("li", null, h("b", null, t("stop.when")), " ", d[0][2]));
      const pl = placesOf(i); if (pl.length) facts.append(h("li", null, h("b", null, t("stop.where")), " ", ...pl.slice(0, 3).flatMap((p, q) => [q ? ", " : "", nameBtn(p)])));
      const g = peopleAt(i);
      const counts = ["led", "part", "died", "absent"].filter((x) => g[x].size).map((x) => t("who." + x, { n: fmt(g[x].size) }));
      if (counts.length) facts.append(h("li", null, counts.join(" · ")));
      const led = [...claimsOf(i)].filter((c) => pk(c) === "led").slice(0, S.depth === "discover" ? 2 : 4);
      led.forEach((c) => facts.append(claimRow(c, i)));
    } else {
      const cs = [...claimsOf(i)].filter((c) => pclass(c) !== "kinship" || S.depth !== "discover");
      cs.sort((a, b) => CLASS_ORDER.indexOf(pclass(a)) - CLASS_ORDER.indexOf(pclass(b)) || (cf("ms", a) ?? 1e9) - (cf("ms", b) ?? 1e9));
      cs.slice(0, S.depth === "discover" ? 3 : 6).forEach((c) => facts.append(claimRow(c, i)));
      if (k === "story" && nf("no", i)) facts.prepend(h("li", null, t("story.no", { n: fmt(nf("no", i)) }), nf("partl", i) ? " · " + nf("partl", i) : ""));
    }
    const fm = firstMention(i);
    if (fm) facts.append(h("li", { class: "cite" }, fm));
    if (facts.childNodes.length) left.append(h("section", { class: "facet" }, h("h3", null, t("stop.record")), facts));
    if (S.depth !== "discover") left.append(recall(i));

    const right = h("div", null);
    let people = [];
    if (k === "event") { const g = peopleAt(i); people = sortPeople([...g.led, ...g.part, ...g.died, ...g.other]); }
    else people = sortPeople([...neighbours(i)].filter((j) => KIND[j] === "person" && !isBack(j)));
    if (people.length) right.append(h("section", { class: "facet", style: "margin-top:0;border-top:0;padding-top:0" }, h("h3", null, k === "event" ? t("stop.who") : t("stop.people")), chips(people, S.depth === "discover" ? 10 : 18)));
    right.append(h("section", { class: "facet" }, h("h3", null, t("stop.next")), directions(i)));
    if (T.journey && T.journey.status !== "approved") right.append(h("p", { class: "note" }, t("tour.draft")));
    if (T.key === "opposition") right.append(h("p", { class: "note warn" }, t("tour.opposition.note")));
    $("guide-body").replaceChildren(h("div", { class: "stop-grid" }, left, right));
    $("guide-body").scrollTop = 0;
    insets();
  }
  function directions(i) {
    const box = h("div", { class: "dirs" });
    const dir = (label, name, fn) => box.append(h("button", { type: "button", class: "dir", onclick: fn }, h("small", null, label), h("span", null, name)));
    const k = KIND[i];
    if (k === "event") {
      const ecl = META.ecliptic.map(([x]) => x), at = ecl.indexOf(i);
      if (at > 0) dir(t("dir.before"), nameOf(ecl[at - 1]), () => jumpTo(ecl[at - 1]));
      if (at >= 0 && at < ecl.length - 1) dir(t("dir.after"), nameOf(ecl[at + 1]), () => jumpTo(ecl[at + 1]));
      const shared = sharedEvents(i).slice(0, 2);
      for (const [e, cnt] of shared) dir(t("dir.shared", { n: fmt(cnt) }), nameOf(e), () => jumpTo(e));
      const pl = placesOf(i)[0];
      if (pl !== undefined) dir(t("dir.stand"), nameOf(pl), () => startTour(dynamicTour(pl)));
      const g = peopleAt(i), lead = sortPeople([...g.led, ...g.part])[0];
      if (lead !== undefined && lead !== LIGHT) dir(t("dir.life"), nameOf(lead), () => startTour(dynamicTour(lead)));
    } else if (k === "person") {
      if (i !== LIGHT) dir(t("dir.life"), nameOf(i), () => startTour(dynamicTour(i)));
      if (kin(i).parents.length || kin(i).children.length) dir(t("dir.lineage"), nameOf(i), () => { setView("lineage", { of: i }); });
      const ev = eventsOf(i)[0];
      if (ev !== undefined) dir(t("dir.around"), nameOf(ev), () => startTour(dynamicTour(ev)));
    } else if (k === "place") {
      const ev = byText(othersBy(i).filter((j) => KIND[j] === "event"))[0];
      if (ev !== undefined) dir(t("dir.around"), nameOf(ev), () => startTour(dynamicTour(ev)));
    } else {
      const p = sortPeople(othersBy(i).filter((j) => KIND[j] === "person"))[0];
      if (p !== undefined && p !== LIGHT) dir(t("dir.life"), nameOf(p), () => startTour(dynamicTour(p)));
    }
    dir(t("dir.record"), nameOf(i), () => openRecord(i));
    return box;
  }
  function jumpTo(i) { // inside the current tour if it is a stop, otherwise a tour around it
    const G = S.guide;
    if (G) { const at = G.T.stops.indexOf(i); if (at >= 0) { goStop(at); return; } }
    startTour(dynamicTour(i));
  }
  function sharedEvents(ev) { // other events with people recorded at both: a count of shared records
    const people = othersBy(ev).filter((j) => KIND[j] === "person" && j !== LIGHT);
    const cnt = new Map();
    for (const p of people) for (const e of othersBy(p)) if (KIND[e] === "event" && e !== ev) cnt.set(e, (cnt.get(e) || 0) + 1);
    return [...cnt.entries()].filter(([, c]) => c >= 2).sort((a, b) => b[1] - a[1] || nameOf(a[0]).localeCompare(nameOf(b[0])));
  }
  function recall(i) { // a question about the stop, answered from the record; nothing is marked wrong
    const k = KIND[i];
    let q = null, ans = null;
    if (k === "event") {
      const led = othersBy(i, ["led"]).filter((j) => KIND[j] === "person");
      const pl = placesOf(i), d = nf("d", i);
      if (led.length) { q = t("recall.led", { name: nameOf(i) }); ans = () => chips(sortPeople(led)); }
      else if (pl.length) { q = t("recall.where", { name: nameOf(i) }); ans = () => chips(pl); }
      else if (d) { q = t("recall.when", { name: nameOf(i) }); ans = () => h("p", null, d[0][2]); }
    } else if (k === "person" && i !== LIGHT) {
      const ev = eventsOf(i);
      const par = kin(i).parents.map((x) => x[0]);
      if (ev.length) { q = t("recall.events", { name: nameOf(i) }); ans = () => chips(ev, 12); }
      else if (par.length) { q = t("recall.parents", { name: nameOf(i) }); ans = () => chips(par); }
    }
    if (!q) return h("span");
    const box = h("div", { class: "recall" }, h("p", null, h("b", null, t("recall.title")), " ", q));
    const btn = h("button", { type: "button", class: "chip small", onclick: () => {
      btn.replaceWith(ans(), h("p", { class: "muted", style: "margin-top:6px" }, t("recall.note")),
        h("button", { type: "button", class: "chip small", onclick: (e) => { LOG.recalls++; saveLog(); checkMilestones(); e.target.disabled = true; e.target.textContent = t("recall.kept"); } }, t("recall.remembered")));
    } }, t("recall.reveal"));
    box.append(btn);
    return box;
  }
  function stopPlay() { clearInterval(playTimer); playTimer = 0; $("guide-play").setAttribute("aria-pressed", "false"); $("guide-play").textContent = t("guide.play"); }
  function togglePlay() {
    if (playTimer) { stopPlay(); return; }
    $("guide-play").setAttribute("aria-pressed", "true"); $("guide-play").textContent = t("guide.pause");
    playTimer = setInterval(() => {
      const G = S.guide;
      if (!G || G.k >= G.T.stops.length - 1) { stopPlay(); return; }
      goStop(G.k + 1);
    }, S.depth === "discover" ? 6500 : 9000);
  }

  // ------------------------------------------------------------------ tracing a connection
  function trace(a, b) {
    // a 0-1-2 shortest path: kinship steps cost 2, others 1; never through the Prophet ﷺ
    // (connected to almost everyone) and, unless asked, never through lineage-only names
    const dist = new Int32Array(n).fill(1e9), prev = new Int32Array(n).fill(-1), via = new Int32Array(n).fill(-1);
    const buckets = [[a], [], []];
    dist[a] = 0;
    let d = 0, guard = 0;
    while (buckets.some((x) => x.length) && guard++ < 1e6) {
      const bk = buckets[d % 3];
      if (!bk.length) { d++; continue; }
      const x = bk.pop();
      if (dist[x] !== d) continue;
      if (x === b) break;
      if (x !== a && (x === LIGHT || (!S.trace.lineage && isBack(x)))) continue;
      for (const c of claimsOf(x)) {
        const y = other(c, x), w = pclass(c) === "kinship" ? 2 : 1;
        if (dist[x] + w < dist[y]) { dist[y] = dist[x] + w; prev[y] = x; via[y] = c; buckets[dist[y] % 3].push(y); }
      }
    }
    if (dist[b] >= 1e9) { toast(t("trace.none")); return; }
    const path = [];
    for (let x = b; x !== -1; x = prev[x]) path.unshift([x, via[x]]);
    S.trace.path = path;
    LOG.traces++; saveLog(); checkMilestones();
    const set = new Set(path.map(([x]) => x)), lines = new Set();
    for (const [x, c] of path) if (c >= 0) { const p = Math.min(CL.s[c], CL.o[c]), q = Math.max(CL.s[c], CL.o[c]); lines.add(p * 100000 + q); }
    emphasise(set, lines);
    R.flyToNode(b, spread(b, set));
    S.focus = b;
    $("record").hidden = false; $("app").classList.add("has-record");
    insets();
    const body = $("record-body");
    body.replaceChildren(
      h("p", { class: "kind" }, t("trace.kind")),
      h("h2", { class: "name" }, nameOf(a), " → ", nameOf(b)),
      h("p", { class: "note warn" }, t("trace.note")),
      h("p", { class: "muted" }, t("trace.rules")),
      h("label", { class: "toggle" }, h("input", { type: "checkbox", id: "trace-lineage", checked: S.trace.lineage ? true : null, onchange: (e) => { S.trace.lineage = e.target.checked; trace(a, b); } }), h("span", null, t("trace.lineage"))),
      h("ol", { class: "plain path" }, path.map(([x, c], k) => h("li", null, nameBtn(x), c >= 0 ? h("ul", { class: "plain claims" }, claimRow(c, -1)) : null))),
      h("p", { class: "note" }, t("trace.stories")));
    here();
  }

  // ------------------------------------------------------------------ search
  let SEARCH = null;
  const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[ʿʾ'’‘`ʼ]/g, "")
    .replace(/[ً-ْٰ]/g, "").replace(/[أإآٱ]/g, "ا").replace(/ة/g, "ه").replace(/ى/g, "ي")
    .toLowerCase().replace(/\bibn\b/g, "b.").replace(/\bbin\b/g, "b.").replace(/[-]/g, " ").replace(/\s+/g, " ").trim();
  function buildSearch() {
    SEARCH = [];
    for (let i = 0; i < n; i++) {
      const forms = [ND.n[i], nf("sch", i), nf("ar", i), ...(nf("other", i) || [])].filter(Boolean).map(norm);
      SEARCH.push(forms);
    }
    SEARCH[LIGHT].push(norm(t("light.name")), "muhammad", "محمد", "النبي");
  }
  function search(q) {
    const s = norm(q);
    if (!s) return [];
    const hits = [];
    for (let i = 0; i < n; i++) {
      let best = 0;
      for (const f of SEARCH[i]) {
        if (f === s) best = Math.max(best, 4);
        else if (f.startsWith(s)) best = Math.max(best, 3);
        else if (f.includes(" " + s)) best = Math.max(best, 2);
        else if (s.length > 2 && f.includes(s)) best = Math.max(best, 1);
      }
      if (best && S.show.kinds[KIND[i]]) hits.push([i, best]);
    }
    hits.sort((a, b) => b[1] - a[1] || e3Key(a[0])[0] - e3Key(b[0])[0] || isBack(a[0]) - isBack(b[0]) || deg[b[0]] - deg[a[0]] || nameOf(a[0]).localeCompare(nameOf(b[0])));
    return hits.slice(0, 14).map((x) => x[0]);
  }
  function wireSearch() {
    const inp = $("search"), list = $("search-results");
    let items = [], sel = -1;
    const close = () => { list.hidden = true; inp.setAttribute("aria-expanded", "false"); sel = -1; };
    const render = () => {
      list.replaceChildren();
      if (!inp.value.trim()) { close(); return; }
      items = search(inp.value);
      if (!items.length) list.append(h("li", { class: "empty" }, t("search.none")));
      items.forEach((i, k) => list.append(h("li", { role: "option", id: "sr-" + k, "aria-selected": String(k === sel),
        onmousedown: (e) => { e.preventDefault(); choose(i); } }, glyph(i), h("span", { class: "nm" }, nameOf(i)), h("span", { class: "ctx" }, kindText(i) + (contextLine(i) ? " · " + contextLine(i) : "")))));
      list.hidden = false; inp.setAttribute("aria-expanded", "true");
    };
    const choose = (i) => { close(); inp.value = ""; inp.blur(); if (S.view !== "sky" && S.visible && !S.visible[i]) setView("sky", { camera: false }); focus(i); };
    inp.addEventListener("input", () => { sel = -1; render(); });
    inp.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { sel = Math.min(items.length - 1, sel + 1); render(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { sel = Math.max(0, sel - 1); render(); e.preventDefault(); }
      else if (e.key === "Escape") close();
    });
    inp.addEventListener("blur", () => setTimeout(close, 120));
    $("search-form").addEventListener("submit", (e) => { e.preventDefault(); const r = search(inp.value); if (r.length) choose(r[Math.max(0, sel)]); });
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && document.activeElement !== inp && !/input|select|textarea/i.test(document.activeElement.tagName)) { e.preventDefault(); inp.focus(); }
      if (e.key === "Escape" && document.activeElement !== inp) {
        if (!$("drawer").hidden) closeDrawer();
        else if (S.guide) endTour();
        else if (S.focus >= 0) clearFocus();
      }
    });
  }

  // ------------------------------------------------------------------ the Atlas drawer
  let TAB = "guide";
  function openDrawer(tab) {
    if (tab) TAB = tab;
    $("drawer").hidden = false; $("open-atlas").setAttribute("aria-expanded", "true");
    renderDrawer();
    insets();
  }
  function closeDrawer() { $("drawer").hidden = true; $("open-atlas").setAttribute("aria-expanded", "false"); insets(); }
  function renderDrawer() {
    document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === TAB)));
    const body = $("drawer-body");
    body.replaceChildren(...({ guide: drawerGuide, show: drawerShow, index: drawerIndex, log: drawerLog, key: drawerKey })[TAB]());
    body.scrollTop = 0;
  }
  function drawerGuide() {
    const out = [h("p", { class: "section-title" }, t("guide.tours")), h("p", { class: "muted" }, t("guide.tours_note"))];
    for (const T of TOURS) {
      const tk = T.key, seen = LOG.tours[tk] || 0;
      out.push(h("div", { class: "tour" }, h("h3", null, tourTitle(T)), h("p", null, tourLead(T)),
        h("p", { class: "muted" }, t("tour.stops", { n: fmt(T.stops.length) }) + (seen ? " · " + t("tour.reached", { k: fmt(seen) }) : "")),
        h("div", { class: "row" }, h("button", { type: "button", class: "chip primary small", onclick: () => startTour(T, 0) }, t("tour.start")),
          seen > 1 && seen < T.stops.length ? h("button", { type: "button", class: "chip small", onclick: () => startTour(T, seen - 1) }, t("tour.resume", { k: fmt(seen) })) : null)));
    }
    out.push(h("p", { class: "section-title" }, t("guide.from_here")), h("p", { class: "muted" }, t("guide.from_here_note")));
    out.push(h("p", { class: "section-title" }, t("guide.trace")), h("p", { class: "muted" }, t("guide.trace_note")));
    out.push(h("p", { class: "section-title" }, t("guide.stories")), h("p", { class: "note" }, t("trace.stories")));
    return out;
  }
  function toggleRow(id, key, label, note, fn) {
    const inp = h("input", { type: "checkbox", id, checked: key() ? true : null, onchange: (e) => fn(e.target.checked) });
    return h("label", { class: "toggle", for: id }, inp, h("span", null, label, note ? h("small", null, note) : null));
  }
  function drawerShow() {
    const out = [h("p", { class: "section-title" }, t("show.marks"))];
    out.push(toggleRow("show-lines", () => S.show.lines, t("show.lines"), t("show.lines_note"), (v) => { S.show.lines = v; restyle(); }));
    out.push(toggleRow("show-names", () => S.show.names, t("show.names"), null, (v) => { S.show.names = v; restyle(); }));
    out.push(toggleRow("show-background", () => S.show.background, t("show.background"), t("show.background_note", { n: fmt(META.counts.background) }), (v) => { S.show.background = v; restyle(); }));
    out.push(toggleRow("show-turning", () => S.show.turning, t("show.turning"), t("show.turning_note", { n: fmt(META.counts.opponents), k: fmt(META.counts.turned) }), (v) => { S.show.turning = v; restyle(); if (S.focus >= 0) renderRecord(S.focus); }));
    out.push(toggleRow("show-orbit", () => S.show.orbit, t("show.orbit"), reduced ? t("show.orbit_reduced") : t("show.orbit_note"), (v) => { S.show.orbit = v && !reduced; R.requestDraw(); }));
    out.push(h("p", { class: "section-title" }, t("show.kinds")));
    for (const k of KINDS) out.push(toggleRow("kind-" + k, () => S.show.kinds[k], t("kind.plural." + k) + " · " + fmt(META.counts.kinds[k]), null, (v) => { S.show.kinds[k] = v; restyle(); }));
    return out;
  }
  let INDEX = { kind: "person", sort: "e3", q: "", lim: 80 };
  function drawerIndex() {
    const kinds = h("div", { class: "kinds", role: "group", "aria-label": t("index.kinds") }, KINDS.map((k) => h("button", { type: "button", class: "chip small", "aria-pressed": String(INDEX.kind === k), onclick: () => { INDEX.kind = k; INDEX.lim = 80; renderDrawer(); } }, t("kind.plural." + k) + " · " + fmt(META.counts.kinds[k]))));
    const sort = h("select", { class: "field", id: "index-sort", "aria-label": t("index.sort") }, ["e3", "az", "links", "text"].map((s) => h("option", { value: s, selected: INDEX.sort === s ? true : null }, t("sort." + s))));
    sort.addEventListener("change", () => { INDEX.sort = sort.value; renderDrawer(); });
    const q = h("input", { class: "field", id: "index-q", type: "search", value: INDEX.q, placeholder: t("index.filter"), "aria-label": t("index.filter") });
    const list = h("ul", { class: "plain index-list" });
    const fill = () => {
      const s = norm(INDEX.q);
      let items = [];
      for (let i = 0; i < n; i++) if (KIND[i] === INDEX.kind && (!s || SEARCH[i].some((f) => f.includes(s)))) items.push(i);
      items = INDEX.kind === "person" ? sortPeople(items, INDEX.sort) : items.sort((a, b) => INDEX.sort === "links" ? deg[b] - deg[a] : INDEX.sort === "text" ? (firstMs(a) ?? 1e9) - (firstMs(b) ?? 1e9) : nameOf(a).localeCompare(nameOf(b), LANG));
      list.replaceChildren(...items.slice(0, INDEX.lim).map((i) => h("li", null, glyph(i), nameBtn(i), h("span", { class: "count" }, S.depth === "discover" ? "" : t("records.count", { n: fmt(deg[i]) })))));
      if (items.length > INDEX.lim) list.append(h("li", null, h("button", { type: "button", class: "chip small", onclick: () => { INDEX.lim += 200; fill(); } }, t("more.next", { n: fmt(Math.min(200, items.length - INDEX.lim)), total: fmt(items.length) }))));
      if (!items.length) list.append(h("li", { class: "muted" }, t("search.none")));
    };
    q.addEventListener("input", () => { INDEX.q = q.value; INDEX.lim = 80; fill(); });
    fill();
    return [h("p", { class: "section-title" }, t("index.title")), h("p", { class: "muted" }, t("index.note")),
      h("div", { class: "index-tools" }, kinds, sort, q), INDEX.sort === "links" || INDEX.sort === "e3" ? h("p", { class: "note" }, t("sort.links_note")) : null, list];
  }

  // ------------------------------------------------------------------ the logbook
  function markSeen(i) {
    const id = ND.id[i];
    const k = KIND[i];
    if (k === "person") LOG.seen[id] = 1;
    if (k === "event") LOG.events[id] = 1;
    if (k === "place") LOG.places[id] = 1;
    saveLog(); checkMilestones();
  }
  function saveLog() { store.set(LOG_KEY, LOG); }
  const MILESTONES = [
    ["first_light", () => Object.keys(LOG.seen).length + Object.keys(LOG.events).length + Object.keys(LOG.places).length, 1],
    ["ten_stars", () => Object.keys(LOG.seen).length, 10],
    ["hundred_stars", () => Object.keys(LOG.seen).length, 100],
    ["five_events", () => Object.keys(LOG.events).length, 5],
    ["forty_events", () => Object.keys(LOG.events).length, 40],
    ["five_places", () => Object.keys(LOG.places).length, 5],
    ["how_we_know", () => LOG.ladders, 1],
    ["chain", () => LOG.chains, 1],
    ["lineage", () => LOG.lineages, 1],
    ["trace", () => LOG.traces, 1],
    ["recall", () => LOG.recalls, 5],
    ["tour_done", () => Object.keys(LOG.done).filter((k) => k.startsWith("tour:")).length, 1],
    ["ecliptic", () => LOG.tours.ecliptic || 0, () => (META.ecliptic.length)],
    ["both_tongues", () => LOG.arabic, 1],
  ];
  function checkMilestones() {
    for (const [key, val, goal] of MILESTONES) {
      const g = typeof goal === "function" ? goal() : goal;
      if (!LOG.done[key] && val() >= g) {
        LOG.done[key] = new Date().toISOString().slice(0, 10);
        saveLog();
        toast(t("ms.unlocked", { name: t("ms." + key) }));
      }
    }
  }
  function drawerLog() {
    const seen = Object.keys(LOG.seen).length, ev = Object.keys(LOG.events).length, pl = Object.keys(LOG.places).length;
    const out = [h("p", { class: "section-title" }, t("log.title")), h("p", { class: "muted" }, t("log.note")),
      h("div", { class: "stats" }, h("div", null, h("b", null, fmt(seen)), h("span", null, t("log.people", { n: fmt(META.counts.kinds.person) }))),
        h("div", null, h("b", null, fmt(ev)), h("span", null, t("log.events", { n: fmt(META.counts.kinds.event) }))),
        h("div", null, h("b", null, fmt(pl)), h("span", null, t("log.places", { n: fmt(META.counts.kinds.place) }))))];
    out.push(h("p", { class: "section-title" }, t("log.milestones")));
    for (const [key, val, goal] of MILESTONES) {
      const g = typeof goal === "function" ? goal() : goal, v = Math.min(val(), g), done = LOG.done[key];
      out.push(h("div", { class: "milestone" + (done ? " done" : "") }, h("span", { class: "seal", "aria-hidden": "true" }, done ? "✓" : ""),
        h("div", null, h("b", null, t("ms." + key)), h("small", null, t("ms." + key + ".how")), done ? h("small", null, t("log.done_on", { date: done })) : h("div", { class: "bar-meter" }, h("span", { style: `width:${(v / g * 100).toFixed(0)}%` })))));
    }
    const clearBox = h("div", { class: "row", style: "margin-top:14px" });
    const ask = () => clearBox.replaceChildren(h("span", { class: "muted" }, t("log.clear_ask")),
      h("button", { type: "button", class: "chip small", onclick: () => { LOG = { seen: {}, events: {}, places: {}, ladders: 0, chains: 0, traces: 0, tours: {}, lineages: 0, recalls: 0, arabic: 0, done: {} }; saveLog(); renderDrawer(); } }, t("log.clear_yes")),
      h("button", { type: "button", class: "chip small", onclick: () => renderDrawer() }, t("log.clear_no")));
    clearBox.append(h("button", { type: "button", class: "chip small", onclick: ask }, t("log.clear")));
    out.push(clearBox);
    return out;
  }

  // ------------------------------------------------------------------ the key
  function keyGlyph(kind, style) { const cv = h("canvas", { width: 28, height: 28, "aria-hidden": "true" }); drawGlyph(cv.getContext("2d"), kind, style); return cv; }
  function drawerKey() {
    const row = (g, title, text) => h("div", { class: "key-row" }, g, h("p", null, h("b", null, title), " ", text));
    const c = META.counts;
    const out = [h("p", { class: "section-title" }, t("key.marks"))];
    out.push(row(keyGlyph("light"), t("key.light"), t("key.light_text")));
    out.push(row(keyGlyph("person", [COL.person[0], 0, 1]), t("key.person"), t("key.person_text")));
    out.push(row(keyGlyph("event", [COL.event, 1, 0]), t("kind.plural.event") + ".", t("key.event_text")));
    out.push(row(keyGlyph("place", [COL.place, 2, 0]), t("kind.plural.place") + ".", t("key.place_text")));
    out.push(row(keyGlyph("story", [COL.story, 3, 0]), t("kind.plural.story") + ".", t("key.story_text")));
    out.push(row(keyGlyph("group", [COL.group, 4, 0]), t("kind.plural.group") + ".", t("key.group_text")));
    out.push(row(keyGlyph("person", [COL.dark, 5, 0]), t("key.dark"), t("key.dark_text")));
    out.push(h("p", { class: "section-title" }, t("key.brightness")));
    ["sahabi", "tabii", "tabi_al_tabiin"].forEach((g, k) => out.push(row(keyGlyph("person", [COL.person[k], 0, 1]), t("gen." + g), "")));
    out.push(row(keyGlyph("person", [COL.person[3], 0, 0]), t("gen.none"), t("key.gen_note")));
    out.push(h("p", { class: "section-title" }, t("key.lines")));
    for (const cls of CLASS_ORDER) out.push(h("div", { class: "key-row" }, h("span", { class: "sw", style: `display:block;height:2px;margin-top:12px;background:rgb(${LINE[cls].map((x) => Math.round(x * 255)).join(",")})` }), h("p", null, t("class." + cls))));
    out.push(h("p", { class: "section-title" }, t("key.positions")));
    for (const v of VIEWS) out.push(h("p", null, h("b", null, t("view." + v)), " · ", t("caption." + v)));
    out.push(h("p", { class: "section-title" }, t("key.data")));
    out.push(h("p", null, t("key.data_text", { nodes: fmt(c.nodes), claims: fmt(c.assertions), records: fmt(c.records), text: fmt(c.in_text), dated: fmt(c.dated_events), events: fmt(c.events), located: fmt(c.located), places: fmt(c.places) })));
    out.push(h("p", { class: "note warn" }, t("key.status_text", { reviewed: fmt(c.reviewed) })));
    out.push(h("p", { class: "note" }, t("key.duplicates")));
    out.push(h("p", { class: "section-title" }, t("key.sources")));
    out.push(h("ul", { class: "plain claims" }, META.sources.map((s) => h("li", null, s.label, " ", s.ai ? h("span", { class: "tag ai" }, t("source.ai_short")) : h("span", { class: "tag" }, t("source.person"))))));
    out.push(h("p", { class: "section-title" }, t("key.lists")));
    for (const L of META.lists) out.push(h("div", { class: "note" }, h("p", null, h("b", null, t("list." + L.key)), " · ", t("list.proposed")), h("p", { class: "cite" }, L.src)));
    out.push(h("p", { class: "section-title" }, t("key.rules")));
    for (const r of ["provenance", "depiction", "ai", "rank", "outlive"]) out.push(h("p", null, t("rule." + r)));
    out.push(h("p", { class: "section-title" }, t("key.licence")));
    out.push(h("p", { class: "muted" }, t("key.licence_text")));
    return out;
  }

  // ------------------------------------------------------------------ captions, the here line, language and depth
  function caption() {
    let s = t("caption." + S.view);
    if (S.view === "map") s += " " + t("caption.map_count", { n: fmt(META.counts.located), total: fmt(META.counts.places) });
    if (S.view === "lineage" && S.lineageOf >= 0) s = t("caption.lineage_of", { name: nameOf(S.lineageOf) }) + " " + s;
    $("caption").textContent = s;
  }
  function here() {
    let s = t("view." + S.view);
    if (S.guide) s += " · " + t("guide.progress", { k: fmt(S.guide.k + 1), n: fmt(S.guide.T.stops.length) });
    else if (S.trace.path) s += " · " + t("here.trace");
    else if (S.focus >= 0) s += " · " + nameOf(S.focus);
    else s += " · " + t("here.all", { n: fmt(n) });
    $("here").textContent = s;
  }
  function applyStatic() {
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("[data-i18n-ph]").forEach((el) => el.setAttribute("placeholder", t(el.dataset.i18nPh)));
    document.querySelectorAll("[data-i18n-aria]").forEach((el) => el.setAttribute("aria-label", t(el.dataset.i18nAria)));
    document.title = t("page.title");
  }
  function setLang(l, quiet) {
    LANG = l; STR = l === "ar" ? AR : EN;
    document.documentElement.lang = l; document.documentElement.dir = l === "ar" ? "rtl" : "ltr";
    $("lang").setAttribute("lang", l === "ar" ? "en" : "ar");
    applyStatic();
    store.set("marsad-atlas-lang", l);
    if (l === "ar") { LOG.arabic++; saveLog(); if (!quiet) checkMilestones(); }
    if (SEARCH) { buildSearch(); rerender(); }
  }
  function setDepth(d) {
    S.depth = d; document.documentElement.dataset.depth = d;
    document.querySelectorAll(".depth button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.depth === d)));
    store.set("marsad-atlas-depth", d);
    rerender();
  }
  function rerender() {
    buildLabels(); R.requestDraw();
    caption(); here();
    if (!$("record").hidden && S.focus >= 0 && !S.trace.path) renderRecord(S.focus);
    if (S.guide) renderStop();
    if (!$("drawer").hidden) renderDrawer();
    if (!$("welcome").hidden) welcomeCounts();
  }
  function welcomeCounts() {
    const c = META.counts;
    $("welcome-counts").textContent = t("welcome.counts", { people: fmt(c.kinds.person), events: fmt(c.kinds.event), places: fmt(c.kinds.place), claims: fmt(c.assertions) });
  }
  function stageTop() { document.documentElement.style.setProperty("--stage-top", ($("stage").offsetTop + 8) + "px"); insets(); }
  function insets() { // tell the renderer which part of the sky the plates cover
    if (!R) return;
    const st = $("stage").getBoundingClientRect(), x = { l: 0, r: 0, t: 0, b: 0 };
    const phone = st.width < 761;
    for (const id of ["record", "guide", "drawer"]) {
      const el = $(id);
      if (el.hidden) continue;
      const r = el.getBoundingClientRect();
      if (r.width === 0) continue;
      if (phone || id === "guide") x.b = Math.max(x.b, st.bottom - r.top);
      else if (r.left + r.width / 2 > st.left + st.width / 2) x.r = Math.max(x.r, st.right - r.left);
      else x.l = Math.max(x.l, r.right - st.left);
    }
    x.t = 44; // the view switcher
    x.b = Math.min(x.b, st.height * 0.7);
    R.setInset(x);
  }

  // ------------------------------------------------------------------ start
  async function start() {
    let data;
    try { data = await unpack(); }
    catch (e) { $("loading").replaceChildren(h("p", null, t("error.unpack"))); return; }
    model(data);
    buildMsCite();
    let lang = /^#ar$/.test(location.hash) ? "ar" : store.get("marsad-atlas-lang", "en");
    if (lang === "ar") setLang("ar", true);
    const depth = store.get("marsad-atlas-depth", "discover");
    S.depth = ["discover", "study", "research"].includes(depth) ? depth : "discover";
    document.documentElement.dataset.depth = S.depth;
    document.querySelectorAll(".depth button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.depth === S.depth)));
    api.lightIndex = LIGHT;
    try {
      R = window.AtlasSky({ glCanvas: $("gl"), ovCanvas: $("ov"), n, api });
    } catch (e) {
      $("loading").replaceChildren(h("p", null, t("error.webgl")));
      return;
    }
    buildSearch();
    buildTours();
    const v = viewPositions("sky");
    S.visible = v.vis;
    R.setPositions(v.pos);
    R.flyTo(viewCamera("sky"), 0);
    restyle();
    caption(); here(); stageTop();
    window.addEventListener("resize", stageTop);
    $("loading").hidden = true;
    wireSearch();
    document.querySelectorAll(".views button").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));
    document.querySelectorAll(".depth button").forEach((b) => b.addEventListener("click", () => setDepth(b.dataset.depth)));
    document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => { TAB = b.dataset.tab; renderDrawer(); }));
    $("lang").addEventListener("click", () => setLang(LANG === "ar" ? "en" : "ar"));
    $("open-atlas").addEventListener("click", () => ($("drawer").hidden ? openDrawer() : closeDrawer()));
    $("close-atlas").addEventListener("click", closeDrawer);
    $("close-record").addEventListener("click", () => { closeRecord(); if (!S.guide) clearFocus(); });
    $("zoom-in").addEventListener("click", () => R.zoom(0.7));
    $("zoom-out").addEventListener("click", () => R.zoom(1.4));
    $("zoom-fit").addEventListener("click", () => R.flyTo(viewCamera(S.view), 800));
    $("guide-prev").addEventListener("click", () => goStop(S.guide.k - 1));
    $("guide-next").addEventListener("click", () => goStop(S.guide.k + 1));
    $("guide-play").addEventListener("click", togglePlay);
    $("guide-end").addEventListener("click", endTour);
    $("guide-min").addEventListener("click", () => {
      const g = $("guide"), folded = g.classList.toggle("folded");
      $("guide-min").setAttribute("aria-expanded", String(!folded));
      $("guide-min").textContent = folded ? t("guide.unfold") : t("guide.fold");
      insets();
    });
    $("welcome-guide").addEventListener("click", () => { store.set("marsad-atlas-welcomed", 1); startTour(TOURS[0], 0); });
    $("welcome-explore").addEventListener("click", () => { store.set("marsad-atlas-welcomed", 1); $("welcome").hidden = true; });
    if (!store.get("marsad-atlas-welcomed", 0)) { welcomeCounts(); $("welcome").hidden = false; }
    if (lang === "ar") checkMilestones();
    window.__atlas = { S, t, focus, startTour, setView, setLang, setDepth, trace, search, TOURS: () => TOURS, n: () => n, openDrawer, renderDrawer, R: () => R, endTour, goStop };
    document.documentElement.dataset.ready = "1";
  }
  if (!("DecompressionStream" in window)) { $("loading").replaceChildren(h("p", null, t("error.unpack"))); return; }
  start();
})();
