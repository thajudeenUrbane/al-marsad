/* Sky Atlas, part 2 of 8 — the eight views. Each gives every mark a position (or leaves
   it out), the labels its scale needs, and the lines drawn under it. A mark a view
   cannot place from recorded data goes on that view's labelled shelf, never onto the
   axis, the map, the dial or the chain. */
const VIEWS = ["sky", "stories", "time", "map", "globe", "book", "chains", "lineage"];
const BLEND = ["sky", "stories", "time", "map", "globe", "book", "chains"];  // the views the blend slider runs through
const BOOK_W = 2600;
const GEO_K = 62;
const geo = (lon, lat) => [(lon - 41) * GEO_K, -(lat - 22) * GEO_K];
const R_GLOBE = 640;
function onGlobe(lon, lat, r) {
  const la = lat * Math.PI / 180, lo = (lon - 41) * Math.PI / 180, rr = r || R_GLOBE;
  return [rr * Math.cos(la) * Math.sin(lo), rr * Math.sin(la), rr * Math.cos(la) * Math.cos(lo)];
}
const TIME_X = (y) => (y - 628) * 80;
const VCACHE = {};

// a labelled grid, by kind, for the marks a view cannot place; plane "xy" runs down the
// screen, plane "xz" runs towards the viewer on the ground
function shelf(items, put, labels, o) {
  if (!items.length) return o.y0;
  const cell = o.cell || 10, per = Math.max(1, Math.floor(o.width / cell));
  const by = {}; for (const k of KINDS) by[k] = [];
  for (const i of items) by[KIND[i]].push(i);
  let row = 0;
  const at = (c, r) => (o.plane === "xz" ? [o.x0 + c * cell, o.y || 0, o.y0 + r * cell] : [o.x0 + c * cell, o.y0 - r * cell, 0]);
  labels.push({ p: o.plane === "xz" ? [o.x0, o.y || 0, o.y0 - 70] : [o.x0, o.y0 + 70, 0], text: o.title, kind: "shelf" });
  for (const k of KINDS) {
    const arr = by[k].sort((a, b) => (ND.n[a] < ND.n[b] ? -1 : ND.n[a] > ND.n[b] ? 1 : 0));
    if (!arr.length) continue;
    labels.push({ p: at(-0.5, row - 3.2), text: t("shelf.kind." + k, { n: fmt(arr.length) }), kind: "shelfkind" });
    arr.forEach((i, j) => { const p = at(j % per, row + Math.floor(j / per)); put(i, p[0], p[1], p[2], true); });
    row += Math.ceil(arr.length / per) + 7;
  }
  return o.plane === "xz" ? o.y0 + row * cell : o.y0 - row * cell;
}

function viewData(view) {
  if (view !== "lineage" && view !== "globe" && VCACHE[view]) return VCACHE[view];
  const pos = new Float32Array(n * 3), vis = new Uint8Array(n), onShelf = new Uint8Array(n), labels = [];
  let extra = null;
  const put = (i, x, y, z, sh) => { pos[3 * i] = x; pos[3 * i + 1] = y; pos[3 * i + 2] = z; vis[i] = 1; if (sh) onShelf[i] = 1; };
  const jit = (i, s) => hash01(ND.id[i], s);
  const placed = () => { const out = []; for (let i = 0; i < n; i++) if (!vis[i] && i !== LIGHT) out.push(i); return out; };

  if (view === "sky") {
    pos.set(D.pos); vis.fill(1);
  } else if (view === "stories") {
    // the 50 Stories on a dial in reading order, grouped by part
    const R0 = 700;
    const stories = []; for (let i = 0; i < n; i++) if (KIND[i] === "story") stories.push(i);
    stories.sort((a, b) => (nf("no", a) ?? 1e9) - (nf("no", b) ?? 1e9));
    const parts = [];
    for (const i of stories) { const p = nf("part", i); if (!parts.length || parts[parts.length - 1].p !== p) parts.push({ p, l: nf("partl", i), items: [] }); parts[parts.length - 1].items.push(i); }
    const gap = 1.5, slots = stories.length + gap * parts.length;
    let slot = 0;
    const angle = (s) => -Math.PI / 2 + (s + 0.5) / slots * Math.PI * 2;
    for (const P of parts) {
      const start = slot;
      for (const i of P.items) { const a = angle(slot); put(i, R0 * Math.cos(a), -R0 * Math.sin(a), 0); slot++; }
      const mid = angle((start + slot - 1) / 2);
      labels.push({ p: [(R0 + 90) * Math.cos(mid), -(R0 + 90) * Math.sin(mid), 0], text: t("stories.part", { n: fmt(P.p ?? 0) }), kind: "part", full: P.l });
      slot += gap;
    }
    labels.push({ p: [0, R0 + 190, 0], text: t("stories.title"), kind: "title" });
    // everything tied to a story sits inside the dial, near its stories
    const groups = new Map();
    for (let i = 0; i < n; i++) {
      if (KIND[i] === "story" || i === LIGHT) continue;
      const st = [...neighbours(i)].filter((j) => KIND[j] === "story").sort((a, b) => a - b);
      if (!st.length) continue;
      const key = st.join(",");
      if (!groups.has(key)) groups.set(key, { st, items: [] });
      groups.get(key).items.push(i);
    }
    for (const { st, items } of groups.values()) {
      let ax = 0, ay = 0;
      for (const s of st) { ax += pos[3 * s]; ay += pos[3 * s + 1]; }
      ax /= st.length; ay /= st.length;
      const d = Math.hypot(ax, ay), lim = R0 * 0.8;
      if (d > lim) { ax *= lim / d; ay *= lim / d; }
      items.sort((a, b) => ND.k[a] - ND.k[b] || (ND.id[a] < ND.id[b] ? -1 : 1));
      items.forEach((i, j) => { const r = j ? 11 * Math.sqrt(j) : 0, a = j * 2.39996; put(i, ax + r * Math.cos(a), ay + r * Math.sin(a), (jit(i, 3) - 0.5) * 20); });
    }
    shelf(placed(), put, labels, { x0: -1200, y0: -R0 - 260, width: 2400, title: t("shelf.stories") });
  } else if (view === "time") {
    // recorded date ranges; people at the dated events they took part in
    const bars = [], bcol = [];
    for (let i = 0; i < n; i++) {
      if (i === LIGHT) continue;
      const sp = yearSpan(i);
      if (!sp) continue;
      const x = TIME_X(sp[0]), k = KIND[i];
      let y;
      if (k === "event" || k === "story") y = k === "story" ? -90 : 0;
      else if (k === "place") y = -180 - jit(i, 1) * 80;
      else y = 50 + jit(i, 1) * 420;
      put(i, k === "person" ? x + (jit(i, 2) - 0.5) * 30 : x, y, k === "person" ? (jit(i, 3) - 0.5) * 30 : 0);
      if ((k === "event" || k === "story") && sp[1] - sp[0] > 0.04) { // a recorded range, drawn as a bar, not a point
        bars.push(x, y, 0, TIME_X(sp[1]), y, 0);
        const c = COL[k]; bcol.push(c[0], c[1], c[2], 0.55, c[0], c[1], c[2], 0.55);
      }
    }
    // a generation is recorded but no date: a band of its own, ordered by generation only
    let k2 = [0, 0, 0];
    const band = [];
    for (let i = 0; i < n; i++) if (!vis[i] && i !== LIGHT && KIND[i] === "person" && nf("tb", i) !== undefined) band.push(i);
    band.sort((a, b) => nf("tb", a) - nf("tb", b) || (ND.n[a] < ND.n[b] ? -1 : 1));
    for (const i of band) { const tb = nf("tb", i); put(i, -1500 + (k2[tb]++) * 24, -330 - tb * 70, 0); }
    if (band.length) {
      labels.push({ p: [-1500, -270, 0], text: t("time.band"), kind: "shelf" });
      META.tb.forEach((g, k) => labels.push({ p: [-1560, -330 - k * 70, 0], text: t("gen." + g), kind: "shelfkind", align: "right" }));
    }
    shelf(placed(), put, labels, { x0: -1800, y0: -620, width: 3600, title: t("shelf.time") });
    extra = { pos: new Float32Array(bars), col: new Float32Array(bcol) };
  } else if (view === "map") {
    const groups = new Map();
    for (let i = 0; i < n; i++) {
      if (i === LIGHT) continue;
      const g = nf("geo", i);
      if (g) { const p = geo(g[0], g[1]); put(i, p[0], 0, p[1]); continue; }
      const pl = nf("pl", i);
      if (pl !== undefined && nf("geo", pl)) { if (!groups.has(pl)) groups.set(pl, []); groups.get(pl).push(i); }
    }
    for (const [pl, items] of groups) { // gathered round their recorded place, in a fixed order
      const c = geo(nf("geo", pl)[0], nf("geo", pl)[1]);
      items.sort((a, b) => ND.k[a] - ND.k[b] || (ND.id[a] < ND.id[b] ? -1 : 1));
      items.forEach((i, k) => { const r = 16 + 6.5 * Math.sqrt(k + 1), a = k * 2.39996; put(i, c[0] + Math.cos(a) * r, 4 + (KIND[i] === "event" ? 10 : 0), c[1] + Math.sin(a) * r); });
    }
    shelf(placed(), put, labels, { plane: "xz", x0: -1300, y0: geo(0, -4)[1], width: 2600, title: t("shelf.map") });
    extra = landLines();
  } else if (view === "globe") {
    const groups = new Map();
    for (let i = 0; i < n; i++) {
      if (i === LIGHT) continue;
      const g = nf("geo", i);
      if (g) { const p = onGlobe(g[0], g[1], R_GLOBE + 2); put(i, p[0], p[1], p[2]); continue; }
      const pl = nf("pl", i);
      if (pl !== undefined && nf("geo", pl)) { if (!groups.has(pl)) groups.set(pl, []); groups.get(pl).push(i); }
    }
    for (const [pl, items] of groups) {
      const [lon, lat] = nf("geo", pl);
      items.sort((a, b) => ND.k[a] - ND.k[b] || (ND.id[a] < ND.id[b] ? -1 : 1));
      items.forEach((i, k) => { // round the place, on the surface
        const r = (0.5 + 0.22 * Math.sqrt(k + 1)), a = k * 2.39996;
        const p = onGlobe(lon + Math.cos(a) * r / Math.max(0.3, Math.cos(lat * Math.PI / 180)), lat + Math.sin(a) * r, R_GLOBE + (KIND[i] === "event" ? 8 : 4));
        put(i, p[0], p[1], p[2]);
      });
    }
    shelf(placed(), put, labels, { plane: "xz", y: -R_GLOBE - 260, x0: -1300, y0: -200, width: 2600, title: t("shelf.map") });
    extra = globeLines();
  } else if (view === "book") {
    const max = META.ms_max || 1;
    for (let i = 0; i < n; i++) {
      if (i === LIGHT) continue;
      const ms = firstMs(i), k = KIND[i];
      if (ms === undefined) { put(i, -BOOK_W / 2 - 120 - jit(i, 1) * 240, -560 + jit(i, 2) * 1120, (jit(i, 3) - 0.5) * 40); continue; }
      const x = -BOOK_W / 2 + (ms / max) * BOOK_W;
      if (k === "event") put(i, -BOOK_W / 2 + ((nf("mt", i) ?? ms) / max) * BOOK_W, 0, 0);
      else if (k === "place") put(i, x, -60 - jit(i, 1) * 180, (jit(i, 3) - 0.5) * 30);
      else if (k === "group") put(i, x, -290, 0);
      else if (isBack(i)) put(i, x, 470 + jit(i, 1) * 260, (jit(i, 3) - 0.5) * 30);
      else put(i, x, 50 + jit(i, 1) * 360, (jit(i, 3) - 0.5) * 30);
    }
  } else if (view === "chains") {
    // the recorded chains, narrator by narrator, then everyone else in recorded narration,
    // in layers by their distance from the Prophet ﷺ
    let low = 450;
    D.chains.forEach((ch, c) => {
      const x = -1500 + c * 170, seq = [];
      if (ch.links.length) seq.push(ch.links[0][0]);
      for (const ln of ch.links) if (!seq.includes(ln[1])) seq.push(ln[1]);
      labels.push({ p: [x, 520, 0], text: t("chains.chain_n", { n: fmt(c + 1) }), kind: "chain", chain: c });
      seq.forEach((i, k) => { if (!vis[i] && i !== LIGHT) put(i, x, 450 - k * 80, 0); });
      if (ch.collector !== undefined && !vis[ch.collector]) {
        const y = 450 - seq.length * 80 - 30;
        put(ch.collector, x, y, 0);
        labels.push({ p: [x + 12, y - 10, 0], text: t("chains.collector"), kind: "note", align: "left" });
        low = Math.min(low, y);
      }
      low = Math.min(low, 450 - seq.length * 80);
    });
    const layers = new Map(), loose = [];
    for (let i = 0; i < n; i++) {
      if (vis[i] || i === LIGHT) continue;
      if (CHAIN_D[i]) { if (!layers.has(CHAIN_D[i])) layers.set(CHAIN_D[i], []); layers.get(CHAIN_D[i]).push(i); }
      else if ([...claimsOf(i)].some((c) => pclass(c) === "transmission")) loose.push(i);
    }
    const lx = 350, per = 90, sp = 15;
    let y = 380;
    for (const d of [...layers.keys()].sort((a, b) => a - b)) {
      const arr = sortPeople(layers.get(d));
      labels.push({ p: [lx - 30, y, 0], text: t("chains.layer", { n: fmt(d) }), kind: "shelfkind", align: "right" });
      arr.forEach((i, k) => put(i, lx + (k % per) * sp, y - Math.floor(k / per) * sp, 0));
      y -= Math.ceil(arr.length / per) * sp + 70;
    }
    if (loose.length) {
      labels.push({ p: [lx - 30, y, 0], text: t("chains.loose"), kind: "shelfkind", align: "right" });
      sortPeople(loose).forEach((i, k) => put(i, lx + (k % per) * sp, y - Math.floor(k / per) * sp, 0));
      y -= Math.ceil(loose.length / per) * sp + 70;
    }
    labels.push({ p: [lx, 470, 0], text: t("chains.layers"), kind: "title", align: "left" });
    labels.push({ p: [-1500, 600, 0], text: t("chains.title", { n: fmt(D.chains.length) }), kind: "title", align: "left" });
    shelf(placed(), put, labels, { x0: -1600, y0: Math.min(low, y) - 220, width: 3300, title: t("shelf.chains") });
  } else if (view === "lineage") {
    if (S.lineageOf >= 0) { const tree = lineage(S.lineageOf); for (const [i, [x, y]] of tree.at) put(i, x, y, 0); }
  }
  // the light: at the centre of the Sky; elsewhere above the scale, so it marks no page,
  // date or place (in Lineage, where the Prophet ﷺ stands in the tree)
  if (!vis[LIGHT]) {
    const L = { sky: [0, 0, 0], stories: [0, 0, 0], time: [0, 760, 0], map: [0, 520, 0], globe: [0, R_GLOBE * 1.45, 0],
      book: [-BOOK_W / 2 - 240, 900, 0], chains: [lx(), 680, 0], lineage: [0, 900, 0] }[view];
    put(LIGHT, L[0], L[1], L[2]);
  }
  const out = { pos, vis, labels, extra, shelf: onShelf };
  if (view !== "lineage" && view !== "globe") VCACHE[view] = out;
  return out;
}
const lx = () => 1020;

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
  for (let lon = 20; lon <= 70; lon += 10) { const p = geo(lon, -5), q = geo(lon, 50); pts.push(p[0], 0, p[1], q[0], 0, q[1]); cols.push(0.34, 0.78, 0.72, 0.07, 0.34, 0.78, 0.72, 0.07); }
  for (let lat = 0; lat <= 50; lat += 10) { const p = geo(15, lat), q = geo(75, lat); pts.push(p[0], 0, p[1], q[0], 0, q[1]); cols.push(0.34, 0.78, 0.72, 0.07, 0.34, 0.78, 0.72, 0.07); }
  landCache = { pos: new Float32Array(pts), col: new Float32Array(cols) };
  return landCache;
}

// the record's dated events at located places, one after another: an arc shows the order
// of the record, not a route
let MOVES = null;
function moves() {
  if (MOVES) return MOVES;
  const ev = [];
  for (let i = 0; i < n; i++) {
    const pl = nf("pl", i), sp = yearSpan(i);
    if (KIND[i] === "event" && pl !== undefined && nf("geo", pl) && sp) ev.push({ i, y: sp[0], p: pl });
  }
  ev.sort((a, b) => a.y - b.y || a.i - b.i);
  MOVES = [];
  let prev = null;
  for (const e of ev) { if (prev && prev.p !== e.p) MOVES.push({ a: prev.p, b: e.p, y: e.y, from: prev.i, to: e.i }); prev = e; }
  return MOVES;
}
let globeLand = null;
function globeLines() {
  if (!globeLand) {
    const pts = [], cols = [];
    for (const ring of LAND) for (let k = 0; k + 3 < ring.length; k += 2) {
      const a = ring.slice(k, k + 2), b = ring.slice(k + 2, k + 4);
      if (Math.abs(a[0] - b[0]) > 90) continue;
      pts.push(...onGlobe(a[0], a[1], R_GLOBE * 1.002), ...onGlobe(b[0], b[1], R_GLOBE * 1.002));
      cols.push(0.34, 0.66, 0.66, 0.55, 0.34, 0.66, 0.66, 0.55);
    }
    for (let lon = -180; lon < 180; lon += 15) for (let lat = -75; lat < 75; lat += 5) { pts.push(...onGlobe(lon, lat, R_GLOBE * 1.001), ...onGlobe(lon, lat + 5, R_GLOBE * 1.001)); cols.push(0.34, 0.78, 0.72, 0.08, 0.34, 0.78, 0.72, 0.08); }
    for (let lat = -60; lat <= 60; lat += 15) for (let lon = -180; lon < 180; lon += 5) { pts.push(...onGlobe(lon, lat, R_GLOBE * 1.001), ...onGlobe(lon + 5, lat, R_GLOBE * 1.001)); cols.push(0.34, 0.78, 0.72, 0.08, 0.34, 0.78, 0.72, 0.08); }
    globeLand = { pts, cols };
  }
  const pts = globeLand.pts.slice(), cols = globeLand.cols.slice();
  const upto = S.play ? S.play.y + 1 : Infinity;
  for (const m of moves()) {
    if (m.y > upto) continue;
    const A = nf("geo", m.a), B = nf("geo", m.b);
    let prev = null;
    for (let s = 0; s <= 24; s++) { // along the great circle, lifted in the middle
      const f = s / 24;
      const pa = onGlobe(A[0], A[1], 1), pb = onGlobe(B[0], B[1], 1);
      const om = Math.acos(Math.max(-1, Math.min(1, pa[0] * pb[0] + pa[1] * pb[1] + pa[2] * pb[2]))) || 1e-6;
      const ka = Math.sin((1 - f) * om) / Math.sin(om), kb = Math.sin(f * om) / Math.sin(om);
      const lift = R_GLOBE * (1.01 + 0.16 * Math.sin(Math.PI * f));
      const p = [(pa[0] * ka + pb[0] * kb) * lift, (pa[1] * ka + pb[1] * kb) * lift, (pa[2] * ka + pb[2] * kb) * lift];
      if (prev) { pts.push(...prev, ...p); cols.push(0.92, 0.74, 0.38, 0.9, 0.92, 0.74, 0.38, 0.9); }
      prev = p;
    }
  }
  return { pos: new Float32Array(pts), col: new Float32Array(cols) };
}

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
let lineageCache = { f: -2, T: null };
function lineage(f) {
  if (lineageCache.f === f) return lineageCache.T;
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
    for (const x of front) for (const c of sortPeople(kin(x).children.map((z) => z[0]), "az")) if (add(c, lv)) next.push(c);
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
  const T = { at, levels, width, up: Math.max(0, ...[...levels.keys()]), down: Math.min(0, ...[...levels.keys()]) };
  lineageCache = { f, T };
  return T;
}

function viewCamera(view) {
  if (view === "sky") return { target: [0, 0, 0], dist: 2650, yaw: 0.62, pitch: 0.3 };
  if (view === "stories") return { target: [0, -120, 0], dist: 2900, yaw: 0, pitch: 0 };
  if (view === "book") return { target: [0, 120, 0], dist: 3600, yaw: 0, pitch: 0 };
  if (view === "time") return { target: [150, 60, 0], dist: 3700, yaw: 0, pitch: 0 };
  if (view === "map") return { target: [0, 0, 260], dist: 2200, yaw: 0, pitch: 1.0 };
  if (view === "globe") return { target: [0, 60, 0], dist: 2350, yaw: 0, pitch: 0.32 };
  if (view === "chains") return { target: [-80, -150, 0], dist: 3900, yaw: 0, pitch: 0 };
  if (view === "lineage") {
    if (S.lineageOf < 0) return { target: [0, 0, 0], dist: 1600, yaw: 0, pitch: 0 };
    const T = lineage(S.lineageOf);
    const mid = (T.up + T.down) / 2 * 92, span = Math.max((T.up - T.down) * 92 + 200, T.width * 0.7);
    return { target: [0, mid, 0], dist: Math.max(700, Math.min(5200, span * 1.5)), yaw: 0, pitch: 0 };
  }
}
const VIEWPOINTS = { face: [0, 0], angle: [0.62, 0.32], edge: [Math.PI / 2, 0.02], below: [0.3, -1.1] };
