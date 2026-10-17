/* Sky Atlas: the page, part 1 of 8 — helpers, data, the model, state and the look of a
   mark. The build joins the parts, in order, inside one function scope. Every sentence
   a reader sees is an interface string or a recorded claim with its source; the page
   computes positions and orders, never facts. */
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
// copying works only inside a click; where the browser refuses, the text is shown selected
function copyText(s, where) {
  const done = () => toast(t("copy.done"));
  const fallback = () => {
    const ta = h("textarea", { class: "copy-box", readonly: true, rows: 4, "aria-label": t("copy.manual") });
    ta.value = s;
    const box = h("div", { class: "note" }, h("p", null, t("copy.manual")), ta);
    (where || $("record-body")).prepend(box);
    ta.focus(); ta.select();
  };
  try { navigator.clipboard.writeText(s).then(done, fallback); } catch (e) { fallback(); }
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
let deg, adjStart, adj, KIND;
const KINDS = ["person", "group", "place", "event", "story"];
const CLASS_ORDER = ["participation", "transmission", "social_political", "spatial", "kinship"];
const LIST = { rashidun: new Map(), ten: new Map() };
const FLAG_OPP = 1, FLAG_TURNED = 2, FLAG_BACK = 4;
let CHAIN_D = null, CHAIN_MAX = 1;   // distance from the Prophet ﷺ in recorded narration
let DUPES = null;                    // entries that share one written name
let YEARS = [609, 656];              // the first and last recorded year

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
  let y0 = Infinity, y1 = -Infinity;
  for (let i = 0; i < n; i++) { const a = nf("yr", i), b = nf("yr2", i); if (a !== undefined) { y0 = Math.min(y0, a); y1 = Math.max(y1, b ?? a); } }
  if (y0 < Infinity) YEARS = [Math.floor(y0), Math.ceil(y1)];
  chainDistances();
  findDuplicates();
}
const nf = (field, i) => (ND[field] ? ND[field][i] : undefined);
const cf = (field, c) => (CL[field] ? CL[field][c] : undefined);
const firstMs = (i) => nf("ms", i);
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
const yearSpan = (i) => { const a = nf("yr", i); return a === undefined ? null : [a, nf("yr2", i) ?? a]; };

// distance in recorded narration: the recorded chains (first narrator 1, each link one
// more, the collector last) and every "narrated from" / "transmitted to" claim, counted
// out from the Prophet ﷺ
function chainDistances() {
  const d = new Int16Array(n);
  const set = (i, v) => { if (i === null || i === undefined || i === LIGHT) return; if (!d[i] || v < d[i]) d[i] = v; };
  for (const ch of D.chains) {
    if (ch.links.length) set(ch.links[0][0], 1);
    ch.links.forEach((ln, k) => set(ln[1], k + 2));
    if (ch.collector !== undefined) set(ch.collector, ch.links.length + 2);
  }
  // nearer -> further edges from the claims
  const out = new Map();
  const edge = (a, b) => { if (!out.has(a)) out.set(a, []); out.get(a).push(b); };
  for (let c = 0; c < nc; c++) {
    const p = pk(c);
    if (p === "narrated_from") edge(CL.o[c], CL.s[c]);
    else if (p === "transmitted_to") edge(CL.s[c], CL.o[c]);
  }
  for (const b of out.get(LIGHT) || []) set(b, 1);
  let front = [];
  for (let i = 0; i < n; i++) if (d[i]) front.push(i);
  front.sort((a, b) => d[a] - d[b]);
  while (front.length) { // breadth first: a shorter recorded route always wins
    const next = [];
    for (const a of front) for (const b of out.get(a) || []) if (b !== LIGHT && (!d[b] || d[a] + 1 < d[b])) { d[b] = d[a] + 1; next.push(b); }
    front = next;
  }
  CHAIN_D = d;
  CHAIN_MAX = Math.max(1, ...d);
}

// entries whose written name is the same once qualifiers in brackets are set aside: shown
// as "same written name", never judged to be one person
function baseName(i) { return norm(ND.n[i].replace(/\s*\([^)]*\)/g, "")); }
function findDuplicates() {
  const groups = new Map();
  for (let i = 0; i < n; i++) {
    if (i === LIGHT) continue;
    const key = KIND[i] + "|" + baseName(i);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(i);
  }
  DUPES = new Map();
  let g = 0, e = 0;
  for (const arr of groups.values()) if (arr.length > 1) { g++; e += arr.length; for (const i of arr) DUPES.set(i, arr); }
  DUPES.stats = { groups: g, entries: e };
}

const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[ʿʾ'’‘`ʼ]/g, "")
  .replace(/[ً-ْٰ]/g, "").replace(/[أإآٱ]/g, "ا").replace(/ة/g, "ه").replace(/ى/g, "ي")
  .toLowerCase().replace(/\bibn\b/g, "b.").replace(/\bbin\b/g, "b.").replace(/[-]/g, " ").replace(/\s+/g, " ").trim();

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
const sentence = (c) => `${nameOf(CL.s[c])} ${predText(c)} ${nameOf(CL.o[c])}`;

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
const textOrder = (i) => (KIND[i] === "event" ? (nf("mt", i) ?? firstMs(i)) : firstMs(i)) ?? 1e9;
const byText = (arr) => arr.slice().sort((a, b) => textOrder(a) - textOrder(b) || nameOf(a).localeCompare(nameOf(b), LANG));

// a citation in short (volume and page) and in full
function citation(c, full) {
  const cs = cf("cs", c), cp = cf("cp", c);
  if (!cs) return null;
  if (full) return (cp !== undefined ? META.citp[cp] + ", " : "") + cs;
  return t("cite.short", { where: cs.split(";")[0] });
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
  depth: "discover", view: "sky", focus: -1, hover: -1, lit: null, litLines: null, lineClasses: null,
  show: { lines: true, names: true, background: true, turning: false, orbit: false, scenery: true, cluster: false,
    hollow: false, big: false, light: "generation",
    kinds: { person: true, group: true, place: true, event: true, story: true } },
  guide: null, trace: { from: -1, to: -1, path: null, threads: null, k: 0, lineage: false }, lineageOf: -1, visible: null,
  labels: [], markers: [], period: null, play: null, preset: null, blend: null, history: [], compare: -1,
  speak: false, classroom: false, flash: null,
};
let R = null;
const LOG_KEY = "marsad-atlas-log-v1";
const LOG_DEFAULT = () => ({ seen: {}, events: {}, places: {}, ladders: 0, chains: 0, traces: 0, tours: {}, lineages: 0,
  recalls: 0, arabic: 0, done: {}, views: {}, chainSet: {}, compares: 0, spoken: 0 });
let LOG = Object.assign(LOG_DEFAULT(), store.get(LOG_KEY, null) || {});
const STAR_KEY = "marsad-atlas-stars-v1";
let STARS = store.get(STAR_KEY, []) || [];  // the learner's own star chart: entry IDs, in the order saved

// ------------------------------------------------------------------ colours and shapes
const COL = {
  person: [[0.86, 0.92, 1.0], [1.0, 0.86, 0.66], [1.0, 0.74, 0.52], [0.78, 0.79, 0.84]],
  event: [0.89, 0.71, 0.36], place: [0.34, 0.78, 0.72], story: [0.87, 0.56, 0.65], group: [0.65, 0.59, 0.91],
  dark: [0.1, 0.09, 0.09],
};
const LINE = { participation: [0.89, 0.71, 0.36], kinship: [0.86, 0.74, 0.8], social_political: [0.65, 0.59, 0.91], spatial: [0.34, 0.78, 0.72], transmission: [0.72, 0.9, 1.0] };
const SHAPE = { person: 0, event: 1, place: 2, story: 3, group: 4 };
const mix = (a, b, f) => [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
function markStyle(i) {
  const k = KIND[i];
  if (k === "person") {
    if (isOpp(i) && !(S.show.turning && isTurned(i))) return [COL.dark, 5, 0];
    if (S.show.light === "chain") { // brightness by place in recorded narration
      const d = CHAIN_D[i];
      if (!d) return [COL.person[3], 0, 0];
      const f = CHAIN_MAX > 1 ? (d - 1) / (CHAIN_MAX - 1) : 0;
      return [mix(COL.person[0], COL.person[2], f), 0, 1 - 0.5 * f];
    }
    if (S.show.light === "none") return [COL.person[0], 0, 0];
    const tb = nf("tb", i);
    if (tb === undefined) return [COL.person[3], 0, 0];
    return [COL.person[tb], 0, [1, 0.7, 0.5][tb]];
  }
  return [COL[k], SHAPE[k], 0];
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
  if (kind === "hollow") { g.lineWidth = 1.8; g.arc(14, 14, 7, 0, 7); g.stroke(); return; }
  if (kind === "absent") { g.strokeStyle = "#e07a5f"; g.lineWidth = 1.6; g.arc(14, 14, 9, 0.3, 2.6); g.stroke(); g.beginPath(); g.arc(14, 14, 9, 3.4, 5.9); g.stroke(); g.beginPath(); g.moveTo(7, 21); g.lineTo(21, 7); g.stroke(); return; }
  if (kind === "cluster") { g.fillStyle = "#0e1426"; g.strokeStyle = "#dce8ff"; g.lineWidth = 1.3; g.arc(14, 14, 11, 0, 7); g.fill(); g.stroke(); g.fillStyle = "#dce8ff"; g.font = "600 10px system-ui"; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText("12", 14, 14.5); return; }
  if (kind === "test") { g.fillStyle = "rgba(140,163,204,0.8)"; for (const [x, y] of [[8, 9], [17, 6], [20, 17], [11, 19], [14, 13]]) g.fillRect(x, y, 2, 2); return; }
  if (shape === 0) g.arc(14, 14, 7, 0, 7);
  else if (shape === 1) { for (let k = 0; k < 8; k++) { const a = k * Math.PI / 4 - Math.PI / 2, r = k % 2 ? 3 : 11; g.lineTo(14 + Math.cos(a) * r, 14 + Math.sin(a) * r); } g.closePath(); }
  else if (shape === 2) { g.moveTo(14, 4); g.lineTo(24, 14); g.lineTo(14, 24); g.lineTo(4, 14); g.closePath(); }
  else if (shape === 3) { for (let k = 0; k < 6; k++) { const a = k * Math.PI / 3; g.lineTo(14 + Math.cos(a) * 9, 14 + Math.sin(a) * 9); } g.closePath(); g.lineWidth = 3; g.stroke(); return; }
  else if (shape === 4) { g.moveTo(14, 5); g.lineTo(23, 21); g.lineTo(5, 21); g.closePath(); }
  else if (shape === 5) { g.arc(14, 14, 8, 0, 7); g.fillStyle = "#1a1716"; g.fill(); g.lineWidth = 1.6; g.strokeStyle = "#d46446"; g.stroke(); return; }
  g.fill();
}
function saveLog() { store.set(LOG_KEY, LOG); }
