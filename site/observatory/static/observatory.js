/* al-Marṣad Observatory, tier L1 (docs/04 §1–3, §6; docs/05 §1–2, §9–10).
 * One canvas; five precomputed frames blended by weight; five verbs (focus, trace,
 * scrub, interrogate, ask). Everything shown comes from the data inlined in this page.
 * Nothing is fetched, nothing is laid out at run time, nothing moves unless the
 * visitor changes the view. */
(function () {
  "use strict";
  const byId = (id) => document.getElementById(id);
  const DATA = JSON.parse(byId("obs-data").textContent);
  const I18N = JSON.parse(byId("obs-i18n").textContent);
  const N = DATA.nodes, L = DATA.links, C = DATA.claims, SRC = DATA.sources, STR = DATA.strings;
  const REP = DATA.reports, CHAINS = DATA.chains, FR = DATA.frames, META = DATA.meta;
  const PRESETS = DATA.presets || [];
  const FRAMES = ["network", "time", "geo", "stories", "isnad"];
  const VIEWSTATE_FRAME = { network: "network", time: "time", geo: "geo", stories: "affinity", isnad: "isnad" };
  const KINDS = ["person", "group", "place", "event", "story"];
  const CLASSES = ["participation", "kinship", "social_political", "spatial", "transmission"];
  const LENSES = ["discover", "study", "research"];
  const n = N.length;
  const mq = (q) => (window.matchMedia ? window.matchMedia(q).matches : false);
  const reduceMotion = mq("(prefers-reduced-motion: reduce)");

  // ------------------------------------------------------------------ state
  const S = {
    lens: "study",
    weights: [1, 0, 0, 0, 0],
    focus: -1,
    links: null,            // link indices being interrogated (one pair, any classes)
    nodeLadder: false,      // "How do we know?" on the focused node
    panel: "intro",         // intro | focus | link | trace
    hover: -1,
    trace: { a: -1, b: -1, paths: [], total: 0, sel: 0, open: false },
    picking: false,
    scrub: { on: false, y0: FR.time.axis.y0, y1: FR.time.axis.y1 },
    hidden: new Set(),
    preset: null, hl: null, hlClass: null,
    cam: { x: 0, y: 0, k: 1 }, camMode: "fit", baseK: 1,
    evidence: "expanded",
    history: [],
  };

  // ------------------------------------------------------------------ i18n
  function t(key, vars) {
    let s = I18N[key];
    if (S.lens === "discover" && I18N[key + ".plain"] !== undefined) s = I18N[key + ".plain"];
    if (s === undefined) return key;
    if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] === undefined || vars[k] === null ? m : String(vars[k])));
    return s;
  }
  const fmt = (x) => Number(x).toLocaleString("en");

  // ------------------------------------------------------------------ colours (defined once, in CSS)
  const css = getComputedStyle(document.documentElement);
  const cv = (name) => css.getPropertyValue(name).trim();
  const COL = {
    bg: cv("--bg"), ink: cv("--ink"), muted: cv("--muted"), line: cv("--line"),
    lineHi: cv("--line-hi"), ring: cv("--ring"), hatch: cv("--hatch"), deco: cv("--deco"),
  };
  KINDS.forEach((k) => { COL[k] = cv("--c-" + k); });

  // ------------------------------------------------------------------ graph helpers
  const adj = Array.from({ length: n }, () => []);
  L.forEach((l, li) => { adj[l.a].push(li); if (l.b !== l.a) adj[l.b].push(li); });
  const otherEnd = (li, i) => (L[li].a === i ? L[li].b : L[li].a);
  const FP = FRAMES.map((f) => Float32Array.from(FR[f].pos));
  const P = new Float32Array(n * 2);
  const timeMarks = FR.time.marks || {};

  function blend() {
    const w = S.weights;
    for (let i = 0; i < 2 * n; i++) {
      let v = 0;
      for (let f = 0; f < FRAMES.length; f++) if (w[f] > 0) v += w[f] * FP[f][i];
      P[i] = v;
    }
  }
  const dominant = () => S.weights.indexOf(Math.max(...S.weights));

  // search options: "Name — Kind", made unique
  const optionLabel = [];
  const byOption = new Map();
  N.forEach((nd, i) => {
    let lab = `${nd.n} — ${I18N["kind." + nd.k]}`;
    if (byOption.has(lab)) { let k = 2; while (byOption.has(`${lab} (${k})`)) k++; lab = `${lab} (${k})`; }
    optionLabel[i] = lab;
    byOption.set(lab, i);
  });
  const byId_ = new Map(N.map((nd, i) => [nd.id, i]));

  // ------------------------------------------------------------------ DOM helper
  function h(tag, props, ...kids) {
    const el = document.createElement(tag);
    if (props) {
      for (const k of Object.keys(props)) {
        const v = props[k];
        if (v === null || v === undefined || v === false) continue;
        if (k === "class") el.className = v;
        else if (k === "text") el.textContent = v;
        else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
        else el.setAttribute(k, v === true ? "" : String(v));
      }
    }
    for (const kid of kids.flat(3)) {
      if (kid === null || kid === undefined || kid === false) continue;
      el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }

  // ------------------------------------------------------------------ canvas
  const canvas = byId("obs-canvas");
  const ctx = canvas.getContext("2d");
  let W = 300, H = 300, DPR = 1;
  let hatchPattern = null, grainPattern = null, grainPatternHi = null;

  function makePatterns() {
    const hc = document.createElement("canvas");
    hc.width = hc.height = 6;
    const g = hc.getContext("2d");
    g.strokeStyle = COL.hatch; g.lineWidth = 1.6;
    g.beginPath(); g.moveTo(-1, 7); g.lineTo(7, -1); g.moveTo(-1, 1); g.lineTo(1, -1); g.moveTo(5, 7); g.lineTo(7, 5); g.stroke();
    hatchPattern = ctx.createPattern(hc, "repeat");
    const mk = (col) => {
      const c = document.createElement("canvas");
      c.width = c.height = 4;
      const q = c.getContext("2d");
      q.fillStyle = col;
      [[0, 0], [2, 0], [1, 1], [3, 1], [0, 2], [2, 2], [3, 3], [1, 3]].forEach(([x, y], k) => {
        q.globalAlpha = k % 3 === 0 ? 0.35 : 1; q.fillRect(x, y, 1, 1);
      });
      return ctx.createPattern(c, "repeat");
    };
    grainPattern = mk(COL.line);
    grainPatternHi = mk(COL.lineHi);
  }

  function resize() {
    const r = canvas.getBoundingClientRect();
    W = Math.max(200, r.width); H = Math.max(200, r.height);
    DPR = Math.min(2.5, window.devicePixelRatio || 1);
    canvas.width = Math.round(W * DPR); canvas.height = Math.round(H * DPR);
    makePatterns();
    S.baseK = fitAll().k;
    if (S.camMode !== "free") S.cam = S.camMode === "focus" ? fitEgo() : fitAll();
    requestDraw();
  }

  // ------------------------------------------------------------------ emphasis
  const nodeA = new Float32Array(n);
  const nodeHollow = new Uint8Array(n);
  const nodeLvl = new Uint8Array(n);     // 0 plain, 1 highlighted, 2 focus or trace end
  const linkLvl = new Uint8Array(L.length); // 0 hidden, 1 dim, 2 normal, 3 highlight, 4 thread
  let emphNodes = null;

  function presence(i) {
    if (!S.scrub.on) return 1;
    const mk = N[i].mk;
    if (!mk || !mk.length) return 0;
    for (const m of mk) if (m[0] < S.scrub.y1 + 1 && m[1] > S.scrub.y0) return 1;
    return -1;
  }
  const visible = (i) => !S.hidden.has(N[i].k);

  function selectedPath() {
    const tr = S.trace;
    return tr.paths && tr.paths.length ? tr.paths[Math.min(tr.sel, tr.paths.length - 1)] : null;
  }

  function computeEmphasis() {
    const path = selectedPath();
    let nodes = null, links = null;
    if (path) {
      nodes = new Set([S.trace.a, S.trace.b]); links = new Set();
      for (const hop of path.hops) { nodes.add(hop.from); nodes.add(hop.to); links.add(hop.li); }
    } else if (S.hl) {
      nodes = new Set(S.hl); if (S.focus >= 0) nodes.add(S.focus);
      links = new Set();
      L.forEach((l, li) => {
        if (nodes.has(l.a) && nodes.has(l.b) && (!S.hlClass || S.hlClass.includes(l.c))) links.add(li);
      });
    } else if (S.focus >= 0) {
      nodes = new Set([S.focus]); links = new Set();
      for (const li of adj[S.focus]) { const o = otherEnd(li, S.focus); if (visible(o)) { nodes.add(o); links.add(li); } }
    }
    emphNodes = nodes;
    for (let i = 0; i < n; i++) {
      nodeHollow[i] = 0; nodeLvl[i] = 0;
      if (!visible(i)) { nodeA[i] = 0; continue; }
      let a = 1;
      if (nodes) a = nodes.has(i) ? 1 : 0.16;
      const pr = presence(i);
      if (pr < 0) a = Math.min(a, 0.13);
      else if (pr === 0) nodeHollow[i] = 1;
      nodeA[i] = a;
      if (nodes && nodes.has(i)) nodeLvl[i] = 1;
    }
    if (S.focus >= 0) nodeLvl[S.focus] = 2;
    if (path) { nodeLvl[S.trace.a] = 2; nodeLvl[S.trace.b] = 2; }
    L.forEach((l, li) => {
      if (!visible(l.a) || !visible(l.b)) { linkLvl[li] = 0; return; }
      let lv = 2;
      if (links) lv = links.has(li) ? (path ? 4 : 3) : 1;
      if (!path && (presence(l.a) < 0 || presence(l.b) < 0)) lv = Math.min(lv, 1);
      linkLvl[li] = lv;
    });
  }

  // ------------------------------------------------------------------ camera
  function bbox(indices) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const i of indices) {
      if (!visible(i)) continue;
      const x = P[2 * i], y = P[2 * i + 1];
      if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
    }
    if (x0 === Infinity) return { x0: -500, y0: -500, x1: 500, y1: 500 };
    return { x0, y0, x1, y1 };
  }
  function fitTo(b, pad) {
    const bw = Math.max(b.x1 - b.x0, 60), bh = Math.max(b.y1 - b.y0, 60);
    const p = pad === undefined ? 34 : pad;
    const k = Math.min((W - 2 * p) / bw, (H - 2 * p) / bh);
    return { x: (b.x0 + b.x1) / 2, y: (b.y0 + b.y1) / 2, k: Math.max(0.02, Math.min(60, k)) };
  }
  const allIdx = Array.from({ length: n }, (_, i) => i);
  const fitAll = () => fitTo(bbox(allIdx));
  function fitEgo() {
    if (emphNodes && emphNodes.size) {
      const f = fitTo(bbox(emphNodes), 60);
      return { x: f.x, y: f.y, k: Math.min(f.k, S.baseK * 6) };
    }
    return fitAll();
  }
  const sx = (x) => (x - S.cam.x) * S.cam.k + W / 2;
  const sy = (y) => (y - S.cam.y) * S.cam.k + H / 2;

  // ------------------------------------------------------------------ animation
  let anim = null, drawQueued = false;
  function requestDraw() {
    if (!drawQueued) { drawQueued = true; requestAnimationFrame(frame); }
  }
  const ease = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
  function lerpCam(a, b, e) {
    const lk = Math.log(a.k) + (Math.log(b.k) - Math.log(a.k)) * e;
    return { x: a.x + (b.x - a.x) * e, y: a.y + (b.y - a.y) * e, k: Math.exp(lk) };
  }
  function animateTo(weights, camMode) {
    if (camMode) S.camMode = camMode;
    const wFrom = S.weights.slice(), wTo = weights ? weights.slice() : S.weights.slice();
    const camFrom = Object.assign({}, S.cam);
    if (reduceMotion) {
      S.weights = wTo; blend(); S.baseK = fitAll().k;
      if (S.camMode === "fit") S.cam = fitAll(); else if (S.camMode === "focus") S.cam = fitEgo();
      syncFrameControls(); requestDraw(); return;
    }
    anim = { t0: performance.now(), dur: 700, wFrom, wTo, camFrom };
    requestDraw();
  }
  function frame(now) {
    drawQueued = false;
    if (anim) {
      const p = Math.min(1, (now - anim.t0) / anim.dur), e = ease(p);
      S.weights = anim.wFrom.map((w, f) => w + (anim.wTo[f] - w) * e);
      blend();
      const target = S.camMode === "fit" ? fitAll() : S.camMode === "focus" ? fitEgo() : null;
      if (target) S.cam = lerpCam(anim.camFrom, target, e);
      if (p >= 1) { anim = null; S.weights = S.weights.map((w) => Math.round(w * 1000) / 1000); S.baseK = fitAll().k; syncFrameControls(); updateHere(); }
    }
    draw();
    if (anim) requestDraw();
  }

  // ------------------------------------------------------------------ drawing
  const DASH = { participation: [], kinship: [], social_political: [7, 4], spatial: [8, 3, 1.5, 3], transmission: [] };
  const fontCache = new Map();
  function textW(s, font) {
    const key = font + "|" + s;
    let w = fontCache.get(key);
    if (w === undefined) { ctx.font = font; w = ctx.measureText(s).width; fontCache.set(key, w); }
    return w;
  }
  const FONT = (px, wt) => `${wt || 400} ${px}px system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", sans-serif`;

  function nodeRadius() {
    const z = Math.sqrt(S.cam.k / (S.baseK || S.cam.k));
    return 4.6 * Math.max(0.75, Math.min(2.4, z));
  }

  function shapePath(path, kind, x, y, r) {
    switch (kind) {
      case "person": path.moveTo(x + r, y); path.arc(x, y, r, 0, Math.PI * 2); break;
      case "place": path.rect(x - r * 0.88, y - r * 0.88, r * 1.76, r * 1.76); break;
      case "event": path.moveTo(x, y - r * 1.2); path.lineTo(x + r * 1.2, y); path.lineTo(x, y + r * 1.2); path.lineTo(x - r * 1.2, y); path.closePath(); break;
      case "group": path.moveTo(x, y - r * 1.2); path.lineTo(x + r * 1.1, y + r * 0.8); path.lineTo(x - r * 1.1, y + r * 0.8); path.closePath(); break;
      default: // story: hexagon
        for (let k = 0; k < 6; k++) {
          const a = Math.PI / 6 + (k * Math.PI) / 3;
          const px = x + r * 1.1 * Math.cos(a), py = y + r * 1.1 * Math.sin(a);
          if (k === 0) path.moveTo(px, py); else path.lineTo(px, py);
        }
        path.closePath();
    }
  }

  function drawDeco() {
    FRAMES.forEach((f, fi) => {
      const w = S.weights[fi];
      if (w < 0.02) return;
      for (const d of FR[f].deco) {
        const a = w * (d.o === undefined ? 1 : d.o);
        ctx.globalAlpha = a;
        if (d.t === "text") {
          ctx.font = FONT(d.z || 11, d.w || 400);
          ctx.fillStyle = COL.deco;
          ctx.textAlign = d.a === "middle" ? "center" : d.a === "end" ? "right" : "left";
          ctx.textBaseline = "alphabetic";
          ctx.fillText(d.s, sx(d.x), sy(d.y));
        } else if (d.t === "line") {
          ctx.strokeStyle = COL.deco; ctx.lineWidth = 1; ctx.setLineDash([]);
          ctx.beginPath(); ctx.moveTo(sx(d.x1), sy(d.y1)); ctx.lineTo(sx(d.x2), sy(d.y2)); ctx.stroke();
        } else if (d.t === "circle") {
          ctx.strokeStyle = COL.deco; ctx.lineWidth = 1; ctx.setLineDash([]);
          ctx.beginPath(); ctx.arc(sx(d.x), sy(d.y), d.r * S.cam.k, 0, Math.PI * 2); ctx.stroke();
        }
      }
    });
    ctx.globalAlpha = 1;
  }

  function drawTimeMarks() {
    const w = S.weights[1];
    if (w < 0.02) return;
    const fp = FP[1];
    for (const key in timeMarks) {
      const i = +key;
      if (!nodeA[i]) continue;
      const y = sy(fp[2 * i + 1]);
      ctx.globalAlpha = w * 0.6 * nodeA[i];
      ctx.fillStyle = COL[N[i].k];
      for (const m of timeMarks[key]) {
        const x0 = sx(m[0]), x1 = sx(m[1]);
        ctx.fillRect(x0, y - 1.5, Math.max(1.5, x1 - x0), 3);
        ctx.fillRect(x0, y - 4, 1, 8); ctx.fillRect(Math.max(x0 + 1, x1 - 1), y - 4, 1, 8);
      }
    }
    ctx.globalAlpha = 1;
  }

  function drawLinks() {
    const wNet = S.weights[0];
    const alphaFor = [0, 0.035 + 0.05 * wNet, 0.1 + 0.3 * wNet, 0.9, 1];
    const widthFor = [0, 1.2, 1.4, 2.1, 3];
    for (let lv = 1; lv <= 4; lv++) {
      for (const cls of CLASSES) {
        let any = false;
        ctx.beginPath();
        for (let li = 0; li < L.length; li++) {
          if (linkLvl[li] !== lv || L[li].c !== cls) continue;
          const l = L[li];
          const x1 = sx(P[2 * l.a]), y1 = sy(P[2 * l.a + 1]), x2 = sx(P[2 * l.b]), y2 = sy(P[2 * l.b + 1]);
          if (cls === "kinship") {
            const dx = x2 - x1, dy = y2 - y1, d = Math.hypot(dx, dy) || 1, ox = (-dy / d) * 1.6, oy = (dx / d) * 1.6;
            ctx.moveTo(x1 + ox, y1 + oy); ctx.lineTo(x2 + ox, y2 + oy);
            ctx.moveTo(x1 - ox, y1 - oy); ctx.lineTo(x2 - ox, y2 - oy);
          } else {
            ctx.moveTo(x1, y1); ctx.lineTo(x2, y2);
          }
          any = true;
        }
        if (!any) continue;
        ctx.globalAlpha = alphaFor[lv];
        ctx.lineWidth = cls === "kinship" ? Math.max(1, widthFor[lv] * 0.7) : cls === "transmission" ? widthFor[lv] + 0.8 : widthFor[lv];
        ctx.setLineDash(DASH[cls]);
        // every link is unreviewed today: drawn with the grain texture (docs/04 §3)
        ctx.strokeStyle = lv >= 3 ? grainPatternHi : grainPattern;
        ctx.stroke();
      }
    }
    ctx.setLineDash([]);
    // direction marks on transmission links (from narrator to narrator)
    ctx.fillStyle = COL.lineHi;
    for (let li = 0; li < L.length; li++) {
      if (L[li].c !== "transmission" || !linkLvl[li]) continue;
      const c = C[L[li].cl[0]];
      const x1 = sx(P[2 * c.s]), y1 = sy(P[2 * c.s + 1]), x2 = sx(P[2 * c.o]), y2 = sy(P[2 * c.o + 1]);
      const d = Math.hypot(x2 - x1, y2 - y1);
      if (d < 18) continue;
      const ux = (x2 - x1) / d, uy = (y2 - y1) / d, mx = x1 + (x2 - x1) * 0.6, my = y1 + (y2 - y1) * 0.6;
      ctx.globalAlpha = linkLvl[li] >= 3 ? 1 : 0.2 + 0.6 * S.weights[4] + 0.2 * S.weights[0];
      ctx.beginPath(); ctx.moveTo(mx + ux * 6, my + uy * 6); ctx.lineTo(mx - uy * 4, my + ux * 4); ctx.lineTo(mx + uy * 4, my - ux * 4); ctx.closePath(); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function drawNodes() {
    const r = nodeRadius();
    const buckets = new Map();
    for (let i = 0; i < n; i++) {
      if (!nodeA[i]) continue;
      const key = N[i].k + "|" + nodeA[i].toFixed(2) + "|" + nodeHollow[i];
      let b = buckets.get(key);
      if (!b) { b = { kind: N[i].k, a: nodeA[i], hollow: nodeHollow[i], path: new Path2D() }; buckets.set(key, b); }
      const x = sx(P[2 * i]), y = sy(P[2 * i + 1]);
      if (x < -20 || y < -20 || x > W + 20 || y > H + 20) continue;
      shapePath(b.path, N[i].k, x, y, r);
    }
    const order = [...buckets.values()].sort((p, q) => p.a - q.a);
    for (const b of order) {
      ctx.globalAlpha = b.a;
      if (b.hollow) {
        ctx.lineWidth = 1.4; ctx.strokeStyle = COL[b.kind]; ctx.stroke(b.path);
        continue;
      }
      ctx.fillStyle = COL[b.kind]; ctx.fill(b.path);
      // texture: unreviewed (every record today)
      ctx.fillStyle = hatchPattern; ctx.fill(b.path);
      ctx.lineWidth = 1; ctx.strokeStyle = COL.bg; ctx.stroke(b.path);
    }
    ctx.globalAlpha = 1;
    // rings: focus, trace ends, hover (crisp outlines, no glow)
    const ring = (i, rad, width, dash) => {
      if (i < 0 || !nodeA[i]) return;
      ctx.beginPath(); ctx.setLineDash(dash || []); ctx.lineWidth = width; ctx.strokeStyle = COL.ring;
      ctx.arc(sx(P[2 * i]), sy(P[2 * i + 1]), rad, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
    };
    for (let i = 0; i < n; i++) if (nodeLvl[i] === 2 && i !== S.focus) ring(i, r + 5, 1.6, [3, 2]);
    ring(S.focus, r + 5, 2.2);
    if (S.trace.a >= 0 && S.picking) ring(S.trace.a, r + 8, 1.4, [2, 3]);
    ring(S.hover, r + 3, 1);
  }

  function labelCandidates() {
    const out = [];
    const wd = S.weights;
    const zoomRel = S.cam.k / (S.baseK || S.cam.k);
    const disc = S.lens === "discover";
    const path = selectedPath();
    const push = (i, pri) => { if (i >= 0 && nodeA[i] > 0.5) out.push([pri, i]); };
    if (S.hover >= 0) push(S.hover, 9);
    push(S.focus, 8);
    if (path) { push(S.trace.a, 7); push(S.trace.b, 7); for (const hop of path.hops) push(hop.to, 6); }
    if (emphNodes) {
      let k = 0;
      for (const i of emphNodes) {
        if (disc && N[i].k !== "story" && k++ > 10) continue;
        push(i, disc && N[i].k === "story" ? 5 : 4);
      }
    }
    for (let i = 0; i < n; i++) {
      if (!nodeA[i] || nodeA[i] < 0.5) continue;
      const kind = N[i].k;
      const reg2 = FR.geo.region[i], reg4 = FR.isnad.region[i], reg3 = FR.stories.region[i];
      if (wd[2] > 0.5 && kind === "place" && reg2 === "map") push(i, 3);
      if (wd[4] > 0.5 && reg4 === "chain") push(i, 3);
      if (wd[3] > 0.5 && kind === "story") push(i, disc ? 3 : 2);
      if (wd[1] > 0.5 && kind === "event" && FR.time.region[i] === "axis") push(i, 2);
      if (zoomRel > 1.9 && (!disc || kind === "story" || kind === "place" || kind === "event")) push(i, 1);
    }
    out.sort((p, q) => q[0] - p[0] || p[1] - q[1]);
    return out;
  }

  function drawLabels() {
    const r = nodeRadius();
    const placed = [];
    const seen = new Set();
    const cands = labelCandidates();
    let count = 0;
    const max = S.lens === "discover" ? 40 : 160;
    ctx.textBaseline = "middle"; ctx.textAlign = "left";
    for (const [pri, i] of cands) {
      if (seen.has(i)) continue;
      seen.add(i);
      if (count >= max && pri < 6) break;
      const font = FONT(pri >= 8 ? 13 : 12, pri >= 7 ? 600 : 400);
      const text = N[i].n;
      const w = textW(text, font);
      const x = sx(P[2 * i]) + r + 5, y = sy(P[2 * i + 1]);
      if (x > W || y < 0 || y > H || x + w < 0) continue;
      const box = [x - 2, y - 8, x + w + 2, y + 8];
      if (pri < 7 && placed.some((b) => b[0] < box[2] && b[2] > box[0] && b[1] < box[3] && b[3] > box[1])) continue;
      placed.push(box);
      ctx.font = font;
      ctx.globalAlpha = 1;
      ctx.lineWidth = 3.5; ctx.strokeStyle = COL.bg; ctx.lineJoin = "round";
      ctx.strokeText(text, x, y);
      ctx.fillStyle = pri >= 4 ? COL.ink : COL.muted;
      ctx.fillText(text, x, y);
      count++;
    }
  }

  function draw() {
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.globalAlpha = 1;
    ctx.fillStyle = COL.bg;
    ctx.fillRect(0, 0, W, H);
    drawDeco();
    drawTimeMarks();
    drawLinks();
    drawNodes();
    drawLabels();
  }

  // ------------------------------------------------------------------ hit testing
  function nodeAt(x, y) {
    const r = nodeRadius() + 6;
    let best = -1, bd = r * r;
    for (let i = 0; i < n; i++) {
      if (!nodeA[i]) continue;
      const dx = sx(P[2 * i]) - x, dy = sy(P[2 * i + 1]) - y, d = dx * dx + dy * dy;
      if (d < bd || (d === bd && best >= 0 && nodeA[i] > nodeA[best])) { bd = d; best = i; }
    }
    return best;
  }
  function linkAt(x, y) {
    let best = -1, bd = 36;
    for (let li = 0; li < L.length; li++) {
      if (linkLvl[li] < 2) continue;
      const l = L[li];
      const x1 = sx(P[2 * l.a]), y1 = sy(P[2 * l.a + 1]), x2 = sx(P[2 * l.b]), y2 = sy(P[2 * l.b + 1]);
      const dx = x2 - x1, dy = y2 - y1, len2 = dx * dx + dy * dy || 1;
      const u = Math.max(0, Math.min(1, ((x - x1) * dx + (y - y1) * dy) / len2));
      const ex = x1 + u * dx - x, ey = y1 + u * dy - y, d = ex * ex + ey * ey;
      if (d < bd) { bd = d; best = li; }
    }
    return best;
  }

  // ------------------------------------------------------------------ verbs
  function snapshot() {
    return { focus: S.focus, links: S.links, nodeLadder: S.nodeLadder, panel: S.panel,
      trace: Object.assign({}, S.trace), preset: S.preset, hl: S.hl, hlClass: S.hlClass };
  }
  function pushHistory() {
    S.history.push(snapshot());
    if (S.history.length > 60) S.history.shift();
    byId("obs-back").disabled = false;
  }
  function back() {
    const s = S.history.pop();
    byId("obs-back").disabled = S.history.length === 0;
    if (!s) return;
    Object.assign(S, { focus: s.focus, links: s.links, nodeLadder: s.nodeLadder, panel: s.panel,
      trace: s.trace, preset: s.preset, hl: s.hl, hlClass: s.hlClass });
    byId("obs-preset").value = S.preset || "";
    S.camMode = S.focus >= 0 || S.hl || selectedPath() ? "focus" : "fit";
    update(true);
  }

  function focusNode(i, record) {
    if (i < 0 || i >= n) return;
    if (record !== false) pushHistory();
    S.focus = i; S.links = null; S.nodeLadder = false; S.panel = "focus";
    if (S.hl && !S.hl.includes(i)) { S.hl = null; S.hlClass = null; S.preset = null; byId("obs-preset").value = ""; }
    S.camMode = "focus";
    update(true);
    announce(t("announce.focus", { name: N[i].n, kind: t("kind." + N[i].k), links: adj[i].length }));
    openSheet();
  }
  function interrogateLinks(lis, record) {
    if (record !== false) pushHistory();
    S.links = lis; S.panel = "link";
    update(false);
    openSheet();
    const l = L[lis[0]];
    announce(t("announce.ladder", { a: N[l.a].n, b: N[l.b].n }));
  }
  function interrogateNode(i) {
    pushHistory();
    S.focus = i; S.nodeLadder = true; S.panel = "focus"; S.links = null;
    update(false);
    openSheet();
  }
  function clearFocus() {
    pushHistory();
    S.focus = -1; S.links = null; S.nodeLadder = false; S.panel = "intro";
    S.hl = null; S.hlClass = null; S.preset = null; byId("obs-preset").value = "";
    S.trace = { a: -1, b: -1, paths: [], total: 0, sel: 0, open: false }; S.picking = false;
    S.camMode = "fit";
    update(true);
    closeSheet();
  }
  function home() {
    pushHistory();
    S.focus = -1; S.links = null; S.nodeLadder = false; S.panel = "intro";
    S.hl = null; S.hlClass = null; S.preset = null; byId("obs-preset").value = "";
    S.trace = { a: -1, b: -1, paths: [], total: 0, sel: 0, open: false }; S.picking = false;
    S.scrub.on = false; S.hidden.clear();
    syncScrub(); syncLegend();
    const w = [0, 0, 0, 0, 0]; w[S.lens === "discover" ? 3 : 0] = 1;
    computeEmphasis();
    animateTo(w, "fit");
    update(false);
    closeSheet();
    announce(t("announce.home"));
  }

  // Trace: all shortest paths between two nodes over recorded links (hidden types skipped)
  function findPaths(a, b) {
    if (a < 0 || b < 0 || a === b) return { paths: [], total: 0, none: a === b };
    const dist = new Int32Array(n).fill(-1);
    const preds = Array.from({ length: n }, () => []);
    dist[a] = 0;
    let frontier = [a];
    while (frontier.length && dist[b] < 0) {
      const next = [];
      for (const u of frontier) {
        for (const li of adj[u]) {
          const v = otherEnd(li, u);
          if (!visible(v)) continue;
          if (dist[v] < 0) { dist[v] = dist[u] + 1; next.push(v); }
          if (dist[v] === dist[u] + 1) preds[v].push([u, li]);
        }
      }
      frontier = next;
    }
    if (dist[b] < 0) return { paths: [], total: 0, none: true };
    const raw = [];
    let total = 0;
    (function walk(v, acc) {
      if (v === a) { total++; if (raw.length < 400) raw.push(acc.slice().reverse()); return; }
      if (total > 5000) return;
      const ps = preds[v].slice().sort((x, y) => N[x[0]].n.localeCompare(N[y[0]].n) || x[1] - y[1]);
      for (const [u, li] of ps) { acc.push({ from: u, to: v, li }); walk(u, acc); acc.pop(); }
    })(b, []);
    const scored = raw.map((hops) => {
      let score = 0;
      for (const hop of hops) {
        const cl = L[hop.li].cl.map((ci) => C[ci]);
        if (cl.some((c) => c.k === "a" && c.st)) score += 1;
        if (cl.some((c) => c.b !== undefined || c.cit)) score += 0.25;
        if (cl.some((c) => c.rep !== undefined)) score += 0.5;
      }
      return { hops, score, key: hops.map((x) => N[x.to].n).join("|") };
    });
    scored.sort((p, q) => q.score - p.score || p.key.localeCompare(q.key));
    return { paths: scored.slice(0, 6), total, none: false };
  }
  function runTrace(a, b, record) {
    if (record !== false) pushHistory();
    const res = findPaths(a, b);
    S.trace = { a, b, paths: res.paths, total: res.total, sel: 0, open: true, none: res.none };
    S.picking = false; S.panel = "trace"; S.links = null;
    S.camMode = "focus";
    update(true);
    openSheet();
    announce(res.paths.length ? t("announce.trace", { n: res.total, steps: res.paths[0].hops.length, a: N[a].n, b: N[b].n }) : t("trace.none", { a: N[a].n, b: N[b].n }));
  }
  function startTraceFrom(i) {
    pushHistory();
    S.trace = { a: i, b: -1, paths: [], total: 0, sel: 0, open: true };
    S.picking = true; S.panel = "trace";
    update(false);
    openSheet();
    announce(t("announce.pick", { name: N[i].n }));
  }

  function applyPreset(key, record) {
    const p = PRESETS.find((x) => x.key === key);
    if (!p) { if (key === "") clearFocus(); return; }
    if (record !== false) pushHistory();
    S.preset = p.key; S.hl = p.hl.slice(); S.hlClass = p.cls || null;
    S.focus = p.focus === undefined || p.focus === null ? -1 : p.focus;
    S.links = null; S.nodeLadder = false; S.panel = S.focus >= 0 ? "focus" : "intro";
    S.trace = { a: -1, b: -1, paths: [], total: 0, sel: 0, open: false }; S.picking = false;
    if (p.win) { S.scrub = { on: true, y0: p.win[0], y1: p.win[1] }; } else { S.scrub.on = false; }
    syncScrub();
    byId("obs-preset").value = p.key;
    const w = [0, 0, 0, 0, 0]; w[FRAMES.indexOf(p.frame)] = 1;
    computeEmphasis();
    animateTo(w, "focus");
    update(false);
    openSheet();
    announce(t("announce.preset", { name: t("preset." + p.key), n: S.hl.length }));
  }

  // ------------------------------------------------------------------ panel pieces
  function swatch(kind) { return h("span", { class: "sw sw-" + kind, "aria-hidden": "true" }); }
  function nodeBtn(i, cls) {
    return h("button", { type: "button", class: "nb " + (cls || ""), onclick: () => focusNode(i) },
      swatch(N[i].k), h("span", { class: "nb-name" }, N[i].n),
      S.lens === "research" ? h("span", { class: "rid" }, N[i].id) : null);
  }
  function statusChip(st) {
    return h("span", { class: "st " + (st ? "st-" + st : "st-none") }, t(st ? "status." + st : "status.none"));
  }
  function srcLabel(ix) {
    if (ix === null || ix === undefined) return t("src.unknown");
    const s = SRC[ix];
    if (s.kind === "work") return s.ai ? t("src.work_ai", { label: s.label }) : s.label;
    return s.ai ? t("src.agent_software", { label: s.label }) : t("src.agent_person", { label: s.label });
  }
  const readerHref = (i) => (META.readerBase || "../") + N[i].u;
  function readerLink(i) {
    return h("a", { class: "reader", href: readerHref(i) }, t("panel.read_page", { name: N[i].n }));
  }
  function nameOrBtn(i, focus) { return i === focus ? h("strong", null, N[i].n) : nodeBtn(i, "inline"); }
  function claimSentence(c, focus) {
    return h("span", { class: "claim" }, nameOrBtn(c.s, focus), " ", h("span", { class: "pred" }, c.p), " ", nameOrBtn(c.o, focus),
      c.r ? h("span", { class: "role" }, " — " + c.r) : null);
  }
  function dateText(i) {
    const d = N[i].d;
    if (!d || !d.length) return null;
    return d.map((x) => x[2]).filter(Boolean).join("; ");
  }
  function howBtn(onclick, label) {
    return h("button", { type: "button", class: "how", onclick }, label || t("verb.how"));
  }

  function chainList(ch) {
    const ol = h("ol", { class: "chain" });
    if (!ch.links.length) return ol;
    ol.append(h("li", null, nodeBtn(ch.links[0][0], "inline")));
    for (const ln of ch.links) {
      ol.append(h("li", { class: "chain-hop" }, h("span", { class: "muted" }, t("ladder.chain_hop", { mode: ln[3] || "—", check: ln[4] || "—" }))));
      ol.append(h("li", null, nodeBtn(ln[1], "inline")));
    }
    if (ch.collector !== null && ch.collector !== undefined) {
      ol.append(h("li", { class: "chain-hop" }, h("span", { class: "muted" }, t("ladder.chain_collector"))));
      ol.append(h("li", null, nodeBtn(ch.collector, "inline")));
    }
    return ol;
  }

  function ladder(ci) {
    const c = C[ci];
    const ol = h("ol", { class: "ladder" });
    const rung = (key, ...body) => ol.append(h("li", null, h("span", { class: "rung" }, t("ladder." + key)), h("div", { class: "rung-body" }, ...body)));
    rung("claim", claimSentence(c, -1), c.q ? h("div", { class: "muted" }, t("ladder.qualifiers", { list: c.q.join(", ") })) : null);
    rung("status", statusChip(c.st), " ", h("span", { class: "muted" }, t(c.st ? "ladder.status_note" : (c.k === "t" ? "ladder.status_none_chain" : "ladder.status_none"))));
    rung("recorded_by", srcLabel(c.src));
    if (c.w !== undefined || c.cit) {
      rung("source", c.cit ? h("div", null, c.cit) : null, c.w !== undefined ? h("div", null, srcLabel(c.w)) : null,
        c.sty !== undefined ? h("div", null, readerLink(c.sty)) : null);
    } else {
      rung("source", h("span", { class: "muted" }, t("ladder.no_passage")));
    }
    if (c.b !== undefined) rung("basis", h("q", null, STR[c.b]));
    if (c.k === "t") rung("transmission", t("ladder.mode", { mode: c.mode || "—" }), c.chk ? h("div", { class: "muted" }, t("ladder.check", { result: c.chk, basis: c.chkb || "—" })) : null);
    if (c.rep !== undefined) {
      const r = REP[c.rep];
      rung("report", h("div", null, r.label || "—"),
        r.genre ? h("div", { class: "muted" }, t("ladder.genre", { value: r.genre })) : null,
        r.asc ? h("div", { class: "muted" }, t("ladder.ascription", { value: r.asc })) : null,
        r.cit ? h("div", null, t("ladder.located_in", { value: r.cit })) : null,
        h("div", { class: "muted" }, t("ladder.report_recorded", { src: srcLabel(r.rec), cov: r.cov || "—" })));
      const ch = CHAINS.find((x) => x.rep === c.rep);
      if (ch) rung("chain", h("div", { class: "muted" }, t("ladder.chain_note", { label: ch.label || "—" })), chainList(ch));
      if (r.grades.length) {
        rung("grading", ...r.grades.map((g) => h("div", null,
          t("ladder.grade", { grade: g.grade || "—", by: g.by || "—", tradition: g.tradition || "—" }),
          g.why ? h("div", { class: "muted" }, t("ladder.grade_why", { value: g.why })) : null,
          h("div", { class: "muted" }, t("ladder.grade_recorded", { src: srcLabel(g.rec) })))));
      }
    }
    rung("not_yet", h("span", { class: "muted" }, t(c.rep !== undefined ? "ladder.not_yet_some" : "ladder.not_yet_all")));
    const reads = [c.s, c.o];
    if (c.sty !== undefined && !reads.includes(c.sty)) reads.push(c.sty);
    rung("read", ...reads.map((i) => h("div", null, readerLink(i))));
    return ol;
  }

  function ladderForLinks(lis) {
    const cis = [];
    for (const li of lis) for (const ci of L[li].cl) cis.push(ci);
    const l = L[lis[0]];
    const wrap = h("div", { class: "ladder-wrap" });
    wrap.append(h("h2", { id: "panel-title", tabindex: "-1" }, t("ladder.title_link", { a: N[l.a].n, b: N[l.b].n })));
    wrap.append(h("p", { class: "muted" }, t("ladder.intro", { n: cis.length })));
    cis.forEach((ci, k) => {
      wrap.append(h("h3", null, t("ladder.claim_n", { k: k + 1, n: cis.length })));
      wrap.append(ladder(ci));
    });
    const back = S.focus >= 0 ? h("button", { type: "button", class: "btn", onclick: () => { pushHistory(); S.links = null; S.panel = "focus"; update(false); } }, t("panel.back_to", { name: N[S.focus].n })) : null;
    if (back) wrap.prepend(back);
    return wrap;
  }

  function rowsFor(i) {
    const rows = [];
    for (const li of adj[i]) {
      const o = otherEnd(li, i);
      if (!visible(o)) continue;
      for (const ci of L[li].cl) rows.push({ ci, li, o });
    }
    return rows;
  }
  function byOther(rows) {
    const m = new Map();
    for (const r of rows) { if (!m.has(r.o)) m.set(r.o, []); m.get(r.o).push(r); }
    return m;
  }

  function otherRow(i, o, rs, extra) {
    const preds = [...new Set(rs.map((r) => C[r.ci].p + (C[r.ci].s === i ? "" : " " + t("panel.inverse_mark"))))];
    const statuses = [...new Set(rs.map((r) => C[r.ci].st || ""))];
    const lis = [...new Set(rs.map((r) => r.li))];
    return h("li", { class: "row" },
      h("div", { class: "row-main" }, nodeBtn(o), extra ? h("span", { class: "muted row-extra" }, extra) : null),
      h("div", { class: "row-sub" }, h("span", { class: "pred" }, preds.join("; ")), " ", statuses.map((s) => statusChip(s || null)),
        " ", howBtn(() => interrogateLinks(lis))));
  }

  function facet(id, title, count, body, note) {
    return h("section", { class: "facet", "aria-labelledby": "fh-" + id },
      h("h3", { id: "fh-" + id }, title, count !== null && count !== undefined ? h("span", { class: "count" }, " " + fmt(count)) : null),
      note ? h("p", { class: "muted" }, note) : null, body);
  }

  function evidenceSummary(i, rows) {
    const seen = new Set();
    const st = new Map(), rec = new Map(), works = new Map();
    for (const r of rows) {
      if (seen.has(r.ci)) continue;
      seen.add(r.ci);
      const c = C[r.ci];
      const sk = c.st ? "status." + c.st : "status.none";
      st.set(sk, (st.get(sk) || 0) + 1);
      const rl = srcLabel(c.src); rec.set(rl, (rec.get(rl) || 0) + 1);
      if (c.w !== undefined) { const wl = srcLabel(c.w); works.set(wl, (works.get(wl) || 0) + 1); }
    }
    const list = (m) => h("ul", { class: "plain" }, [...m.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([k, v]) => h("li", null, h("span", { class: "count" }, fmt(v)), " ", k)));
    const nd = N[i];
    return h("div", null,
      h("p", null, t("panel.record", { cov: t("coverage." + (nd.cov || "none")) }), " ", h("span", { class: "muted" }, t("coverage.explain." + (nd.cov || "none")))),
      h("p", { class: "muted" }, t("panel.record_by", { list: nd.rec.map(srcLabel).join("; ") || t("src.unknown") })),
      h("h4", null, t("panel.by_status")),
      h("ul", { class: "plain" }, [...st.entries()].map(([k, v]) => h("li", null, h("span", { class: "count" }, fmt(v)), " ", h("span", { class: "st " + (k === "status.none" ? "st-none" : "st-" + k.split(".")[1]) }, t(k))))),
      h("h4", null, t("panel.by_recorder")), list(rec),
      works.size ? h("div", null, h("h4", null, t("panel.by_work")), list(works)) : null,
      howBtn(() => interrogateNode(i), t("verb.how_node", { name: nd.n })));
  }

  function relationshipsFacet(i, rows) {
    const body = h("div", null);
    let total = 0;
    for (const cls of CLASSES) {
      const rs = rows.filter((r) => C[r.ci].c === cls && (N[r.o].k === "person" || N[r.o].k === "group"));
      if (!rs.length) continue;
      const m = byOther(rs);
      total += m.size;
      const ul = h("ul", { class: "rows" });
      for (const [o, list] of [...m.entries()].sort((a, b) => N[a[0]].n.localeCompare(N[b[0]].n))) ul.append(otherRow(i, o, list));
      body.append(h("h4", null, lineSample(cls), t("class." + cls), h("span", { class: "count" }, " " + fmt(m.size))), ul);
    }
    if (!total) body.append(h("p", { class: "muted" }, t("panel.none_recorded")));
    return facet("rel", t(N[i].k === "person" ? "facet.relationships" : "facet.people"), total, body);
  }
  function eventsFacet(i, rows) {
    const m = byOther(rows.filter((r) => N[r.o].k === "event"));
    const ul = h("ul", { class: "rows" });
    const items = [...m.entries()].map(([o, list]) => ({ o, list, d: N[o].mk && N[o].mk.length ? N[o].mk[0][0] : Infinity }));
    items.sort((a, b) => a.d - b.d || N[a.o].n.localeCompare(N[b.o].n));
    for (const it of items) ul.append(otherRow(i, it.o, it.list, dateText(it.o) || t("panel.no_date")));
    return facet("events", t("facet.events"), m.size, m.size ? ul : h("p", { class: "muted" }, t("panel.none_recorded")));
  }
  function placesFacet(i, rows) {
    const m = byOther(rows.filter((r) => N[r.o].k === "place"));
    const ul = h("ul", { class: "rows" });
    for (const [o, list] of [...m.entries()].sort((a, b) => N[a[0]].n.localeCompare(N[b[0]].n))) {
      ul.append(otherRow(i, o, list, N[o].geo ? t("panel.located", { conf: N[o].geo[2] || "—" }) : t("panel.not_located")));
    }
    let extra = null;
    if (N[i].k === "place") extra = h("p", null, N[i].geo ? t("panel.coords", { lon: N[i].geo[0], lat: N[i].geo[1], conf: N[i].geo[2] || "—" }) : t("panel.no_coords"));
    return facet("places", t("facet.places"), m.size, h("div", null, extra, m.size ? ul : h("p", { class: "muted" }, t("panel.none_recorded"))));
  }
  function storiesFacet(i, rows) {
    const m = byOther(rows.filter((r) => N[r.o].k === "story"));
    const ul = h("ul", { class: "rows" });
    const items = [...m.entries()].sort((a, b) => (N[a[0]].no || 999) - (N[b[0]].no || 999));
    for (const [o, list] of items) ul.append(otherRow(i, o, list, N[o].no ? t("panel.story_no", { no: N[o].no, part: N[o].part || "—" }) : null));
    let extra = null;
    if (N[i].k === "story") {
      extra = h("div", null,
        h("p", null, t("panel.story_meta", { no: N[i].no || "—", part: N[i].part || "—", label: N[i].partl || "" })),
        N[i].work !== undefined ? h("p", { class: "muted" }, srcLabel(N[i].work)) : null,
        h("p", null, readerLink(i)));
    }
    return facet("stories", t("facet.stories"), m.size, h("div", null, extra, m.size ? ul : h("p", { class: "muted" }, t("panel.none_recorded"))),
      N[i].k === "story" ? null : t("facet.stories_note"));
  }
  function timeFacet(i) {
    const nd = N[i];
    const body = h("div", null);
    if (nd.d && nd.d.length) {
      body.append(h("ul", { class: "plain" }, nd.d.map((d) => h("li", null, d[2] || "—", d[3] && d[3].length ? h("div", { class: "muted" }, d[3].join(" · ")) : null))));
    }
    if (nd.death) body.append(h("p", null, t("panel.death", { value: nd.death.map((d) => d[2]).join("; ") })));
    if (nd.k === "person") {
      if (nd.tb) body.append(h("p", null, t("panel.generation", { value: nd.tb })));
      else body.append(h("p", { class: "muted" }, t("panel.generation_none")));
      if (nd.mk && nd.mk.length) body.append(h("p", { class: "muted" }, t("panel.time_from_events", { n: nd.mk.length })));
      else body.append(h("p", { class: "muted" }, t("panel.no_date_person")));
    } else if (!nd.d || !nd.d.length) {
      body.append(h("p", { class: "muted" }, t("panel.no_date")));
    }
    if (nd.disp) for (const d of nd.disp) body.append(h("div", { class: "dispute" }, h("strong", null, t("panel.dispute")), " ", d.q || "—", d.pos.length ? h("ul", { class: "plain" }, d.pos.map((p) => h("li", null, p))) : null));
    return facet("time", t(nd.k === "person" ? "facet.generation" : "facet.time"), null, body);
  }

  function nodeLadderView(i) {
    const nd = N[i];
    const ol = h("ol", { class: "ladder" });
    const rung = (key, ...body) => ol.append(h("li", null, h("span", { class: "rung" }, t("ladder." + key)), h("div", { class: "rung-body" }, ...body)));
    rung("record", t("panel.record", { cov: t("coverage." + (nd.cov || "none")) }), h("div", { class: "muted" }, t("coverage.explain." + (nd.cov || "none"))));
    rung("recorded_by", nd.rec.map(srcLabel).join("; ") || t("src.unknown"));
    if (nd.k === "story") rung("source", nd.cit || "—", nd.work !== undefined ? h("div", null, srcLabel(nd.work)) : null);
    if (nd.k === "place") rung("location", nd.geo ? t("panel.coords", { lon: nd.geo[0], lat: nd.geo[1], conf: nd.geo[2] || "—" }) : t("panel.no_coords"));
    if (nd.d) rung("dates", ...nd.d.map((d) => h("div", null, d[2] || "—", d[3] && d[3].length ? h("div", { class: "muted" }, d[3].join(" · ")) : null)));
    if (nd.gaps) rung("gaps", ...nd.gaps.map((g) => h("div", null, g)));
    if (nd.sch) rung("scholarly", nd.sch);
    const rows = rowsFor(i);
    const seen = new Set();
    const det = h("div", null);
    for (const r of rows) {
      if (seen.has(r.ci)) continue;
      seen.add(r.ci);
      const c = C[r.ci];
      det.append(h("details", { class: "claim-det", open: S.evidence === "expanded" && seen.size <= 3 ? true : null },
        h("summary", null, claimSentence(c, i), " ", statusChip(c.st)), ladder(r.ci)));
    }
    rung("claims", h("p", { class: "muted" }, t("ladder.claims_count", { n: seen.size })), det);
    rung("read", readerLink(i));
    return h("div", null,
      h("button", { type: "button", class: "btn", onclick: () => { pushHistory(); S.nodeLadder = false; update(false); } }, t("panel.back_to", { name: nd.n })),
      h("h2", { id: "panel-title", tabindex: "-1" }, t("ladder.title_node", { name: nd.n })), ol);
  }

  function focusView(i) {
    const nd = N[i];
    const rows = rowsFor(i);
    const head = h("header", { class: "focus-head" },
      h("p", { class: "kind" }, swatch(nd.k), " ", t("kind." + nd.k), nd.sub && nd.sub !== "group" ? " · " + t("kind." + nd.sub) : null,
        S.lens === "research" ? h("span", { class: "rid" }, " " + t("panel.id", { id: nd.id })) : null),
      h("h2", { id: "panel-title", tabindex: "-1" }, nd.n),
      nd.sch && S.lens !== "discover" ? h("p", { class: "muted" }, t("panel.scholarly", { value: nd.sch })) : null,
      h("div", { class: "actions" },
        howBtn(() => interrogateNode(i), t("verb.how")),
        h("button", { type: "button", class: "btn", onclick: () => startTraceFrom(i) }, t("verb.trace_from")),
        h("a", { class: "btn", href: readerHref(i) }, t("panel.reader"))));
    const facets = {
      evidence: () => facet("evidence", t("facet.evidence"), null, evidenceSummary(i, rows)),
      rel: () => relationshipsFacet(i, rows),
      events: () => eventsFacet(i, rows),
      places: () => placesFacet(i, rows),
      stories: () => storiesFacet(i, rows),
      time: () => timeFacet(i),
    };
    const order = S.lens === "discover" ? ["stories", "rel", "events", "places", "time", "evidence"] : ["evidence", "rel", "events", "places", "stories", "time"];
    return h("div", null, head, order.map((k) => facets[k]()));
  }

  function threadView(path) {
    const ol = h("ol", { class: "thread" });
    ol.append(h("li", { class: "t-node" }, nodeBtn(S.trace.a)));
    for (const hop of path.hops) {
      const cl = L[hop.li].cl;
      ol.append(h("li", { class: "t-hop" },
        h("ul", { class: "plain" }, cl.map((ci) => h("li", null, claimSentence(C[ci], -1), " ", statusChip(C[ci].st),
          h("div", { class: "muted" }, srcLabel(C[ci].w !== undefined ? C[ci].w : C[ci].src))))),
        howBtn(() => interrogateLinks([hop.li]))));
      ol.append(h("li", { class: "t-node" }, nodeBtn(hop.to)));
    }
    return ol;
  }

  function traceView() {
    const tr = S.trace;
    const inA = h("input", { id: "trace-a", list: "obs-names", autocomplete: "off", value: tr.a >= 0 ? optionLabel[tr.a] : "" });
    const inB = h("input", { id: "trace-b", list: "obs-names", autocomplete: "off", value: tr.b >= 0 ? optionLabel[tr.b] : "" });
    const go = () => {
      const a = byOption.get(inA.value), b = byOption.get(inB.value);
      if (a === undefined || b === undefined) { announce(t("trace.pick_both")); return; }
      runTrace(a, b);
    };
    const form = h("form", { class: "trace-form", onsubmit: (e) => { e.preventDefault(); go(); } },
      h("label", { for: "trace-a" }, t("trace.from")), inA,
      h("label", { for: "trace-b" }, t("trace.to")), inB,
      h("div", { class: "actions" },
        h("button", { type: "submit", class: "btn primary" }, t("trace.find")),
        h("button", { type: "button", class: "btn", onclick: () => { const v = inA.value; inA.value = inB.value; inB.value = v; } }, t("trace.swap")),
        h("button", { type: "button", class: "btn", onclick: () => clearFocus() }, t("trace.clear"))));
    const out = h("div", { class: "trace-out" });
    if (S.picking) out.append(h("p", { class: "note" }, t("trace.picking", { name: N[tr.a].n })));
    if (tr.a >= 0 && tr.b >= 0) {
      if (!tr.paths.length) out.append(h("p", null, t("trace.none", { a: N[tr.a].n, b: N[tr.b].n })));
      else {
        out.append(h("p", null, t("trace.found", { n: fmt(tr.total), steps: tr.paths[0].hops.length, shown: tr.paths.length })));
        out.append(h("p", { class: "muted" }, t("trace.rank_note")));
        tr.paths.forEach((p, k) => {
          const sel = k === tr.sel;
          out.append(h("section", { class: "thread-box" + (sel ? " sel" : "") },
            h("h3", null, h("button", { type: "button", class: "btn", "aria-pressed": sel ? "true" : "false", onclick: () => { S.trace.sel = k; update(true); } },
              t("trace.thread_n", { k: k + 1, steps: p.hops.length }))),
            sel ? threadView(p) : h("p", { class: "muted" }, p.hops.map((x) => N[x.to].n).slice(0, -1).join(" · ") || t("trace.direct"))));
        });
        out.append(h("button", { type: "button", class: "btn", onclick: () => copyText(location.href, t("trace.link_copied")) }, t("trace.copy_link")));
      }
    }
    return h("div", null, h("h2", { id: "panel-title", tabindex: "-1" }, t("trace.title")), h("p", { class: "muted" }, t("trace.intro")), form, out);
  }

  function introView() {
    const c = META.counts;
    return h("div", null,
      h("h2", { id: "panel-title", tabindex: "-1" }, t("intro.title")),
      h("p", null, t("intro.how")),
      PRESETS.length ? h("section", { class: "facet" }, h("h3", null, t("presets.title")),
        h("ul", { class: "plain presets" }, PRESETS.map((p) => h("li", null,
          h("button", { type: "button", class: "btn", onclick: () => applyPreset(p.key) }, t("preset." + p.key)),
          h("div", { class: "muted" }, t("preset." + p.key + ".about")))))) : null,
      h("section", { class: "facet" }, h("h3", null, t("reality.title")),
        h("ul", { class: "plain" },
          h("li", null, t("reality.kinds", { person: fmt(c.kinds.person), event: fmt(c.kinds.event), place: fmt(c.kinds.place), story: fmt(c.kinds.story), group: fmt(c.kinds.group) })),
          h("li", null, t("reality.claims", { n: fmt(c.assertions), proposed: fmt(c.status.proposed || 0), reviewed: fmt(c.reviewed) })),
          h("li", null, t("reality.records", { n: fmt(c.records) })),
          h("li", null, t("reality.dates", { dated: fmt(c.dated_events), events: fmt(c.events) })),
          h("li", null, t("reality.tabaqa", { n: fmt(c.tabaqa) })),
          h("li", null, t("reality.located", { n: fmt(c.located), places: fmt(c.places) })),
          h("li", null, t("reality.chains", { n: fmt(c.chains), links: fmt(c.chain_links) })),
          h("li", null, t("reality.never")))));
  }

  // ------------------------------------------------------------------ panel and sheet
  const panel = byId("obs-panel"), panelBody = byId("obs-panel-body");
  function renderPanel() {
    panelBody.replaceChildren();
    let view;
    if (S.panel === "link" && S.links) view = ladderForLinks(S.links);
    else if (S.panel === "trace") view = traceView();
    else if (S.focus >= 0 && S.nodeLadder) view = nodeLadderView(S.focus);
    else if (S.focus >= 0) view = focusView(S.focus);
    else view = introView();
    if (S.preset && S.panel !== "trace") {
      panelBody.append(h("p", { class: "note" }, t("presets.active", { name: t("preset." + S.preset) }), " ",
        h("span", { class: "muted" }, t("preset." + S.preset + ".about"))));
    }
    panelBody.append(view);
    if (S.lens === "research") panelBody.append(researchBox());
  }
  function openSheet() {
    panel.dataset.open = "true";
    const title = byId("panel-title");
    if (title && document.activeElement !== byId("obs-search") && document.activeElement !== canvas) title.focus({ preventScroll: true });
  }
  function closeSheet() { panel.dataset.open = "false"; }

  // ------------------------------------------------------------------ research: view-state (docs/04 §6)
  function viewState() {
    const mw = {};
    FRAMES.forEach((f, k) => { mw[VIEWSTATE_FRAME[f]] = Math.round(S.weights[k] * 1000) / 1000; });
    const path = selectedPath();
    return {
      corpus_version: META.version,
      focus: S.focus >= 0 ? [N[S.focus].id] : [],
      relationships: S.links ? S.links.map((li) => ({ between: [N[L[li].a].id, N[L[li].b].id], class: L[li].c })) : [],
      trace: S.trace.a >= 0 && S.trace.b >= 0 ? { from: N[S.trace.a].id, to: N[S.trace.b].id, thread: S.trace.sel, steps: path ? path.hops.length : null } : null,
      time: { axis: "event", window: S.scrub.on ? [S.scrub.y0, S.scrub.y1] : null },
      morph_weights: mw,
      camera: S.camMode === "free" ? { x: Math.round(S.cam.x), y: Math.round(S.cam.y), zoom: Math.round(S.cam.k * 1000) / 1000 } : { fit: S.camMode },
      layers: KINDS.filter((k) => !S.hidden.has(k)),
      filters: { lens: S.lens, hidden_types: [...S.hidden], vantage: S.preset },
      evidence_mode: S.evidence,
    };
  }
  function applyViewState(v) {
    if (!v || typeof v !== "object") return;
    if (LENSES.includes(v.filters && v.filters.lens)) S.lens = v.filters.lens;
    if (v.morph_weights) {
      const w = FRAMES.map((f) => Math.max(0, +v.morph_weights[VIEWSTATE_FRAME[f]] || 0));
      const s = w.reduce((a, b) => a + b, 0);
      if (s > 0) S.weights = w.map((x) => x / s);
    }
    S.hidden = new Set(((v.filters && v.filters.hidden_types) || []).filter((k) => KINDS.includes(k)));
    if (v.time && Array.isArray(v.time.window)) S.scrub = { on: true, y0: +v.time.window[0], y1: +v.time.window[1] };
    if (v.filters && v.filters.vantage && PRESETS.some((p) => p.key === v.filters.vantage)) {
      const p = PRESETS.find((x) => x.key === v.filters.vantage);
      S.preset = p.key; S.hl = p.hl.slice(); S.hlClass = p.cls || null;
    }
    const f = v.focus && v.focus.length ? byId_.get(v.focus[0]) : undefined;
    if (f !== undefined) { S.focus = f; S.panel = "focus"; }
    if (v.relationships && v.relationships.length) {
      const lis = [];
      for (const r of v.relationships) {
        const a = byId_.get(r.between && r.between[0]), b = byId_.get(r.between && r.between[1]);
        L.forEach((l, li) => { if (((l.a === a && l.b === b) || (l.a === b && l.b === a)) && l.c === r.class) lis.push(li); });
      }
      if (lis.length) { S.links = lis; S.panel = "link"; }
    }
    if (v.trace && v.trace.from && v.trace.to) {
      const a = byId_.get(v.trace.from), b = byId_.get(v.trace.to);
      if (a !== undefined && b !== undefined) {
        const res = findPaths(a, b);
        S.trace = { a, b, paths: res.paths, total: res.total, sel: Math.min(+v.trace.thread || 0, Math.max(0, res.paths.length - 1)), open: true };
        S.panel = "trace";
      }
    }
    if (v.evidence_mode === "folded" || v.evidence_mode === "expanded") S.evidence = v.evidence_mode;
    if (v.camera && typeof v.camera.zoom === "number") { S.cam = { x: +v.camera.x || 0, y: +v.camera.y || 0, k: v.camera.zoom }; S.camMode = "free"; }
    else S.camMode = S.focus >= 0 || S.hl || S.trace.paths.length ? "focus" : "fit";
  }
  const b64e = (s) => btoa(unescape(encodeURIComponent(s))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const b64d = (s) => decodeURIComponent(escape(atob(s.replace(/-/g, "+").replace(/_/g, "/"))));
  let hashTimer = 0;
  function writeHash() {
    clearTimeout(hashTimer);
    hashTimer = setTimeout(() => {
      try { history.replaceState(null, "", "#v=" + b64e(JSON.stringify(viewState()))); } catch (e) { /* sandboxed: the JSON box still has the state */ }
    }, 250);
  }
  function readHash() {
    const hs = location.hash || "";
    try {
      if (hs.startsWith("#v=")) { applyViewState(JSON.parse(b64d(hs.slice(3)))); return true; }
      const m = /lens=(discover|study|research)/.exec(hs);
      if (m) S.lens = m[1];
    } catch (e) { /* an unreadable link opens the default view */ }
    return false;
  }
  function copyText(text, done) {
    const fallback = () => {
      const ta = h("textarea", { class: "sr-only", "aria-hidden": "true" }); ta.value = text; document.body.append(ta); ta.select();
      try { document.execCommand("copy"); } catch (e) { /* nothing more to try */ }
      ta.remove(); announce(done);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(() => announce(done), fallback);
    else fallback();
  }
  function researchBox() {
    const json = JSON.stringify(viewState(), null, 2);
    const c = META.counts;
    const weights = h("div", { class: "weights" }, FRAMES.map((f, k) => {
      const inp = h("input", { type: "range", min: "0", max: "1", step: "0.01", value: String(Math.round(S.weights[k] * 100) / 100), id: "w-" + f,
        oninput: () => {
          const w = FRAMES.map((g) => +byId("w-" + g).value);
          const s = w.reduce((a, b) => a + b, 0) || 1;
          S.weights = w.map((x) => x / s); blend(); if (S.camMode === "fit") S.cam = fitAll(); syncFrameControls(); requestDraw(); updateHere(); writeHash();
        } });
      return h("div", { class: "weight" }, h("label", { for: "w-" + f }, t("frame." + f)), inp);
    }));
    return h("section", { class: "facet research", "aria-labelledby": "fh-research" },
      h("h3", { id: "fh-research" }, t("research.title")),
      h("h4", null, t("research.weights")), weights,
      h("h4", null, t("research.viewstate")),
      h("p", { class: "muted" }, t("research.viewstate_note")),
      h("pre", { class: "json", tabindex: "0" }, json),
      h("div", { class: "actions" },
        h("button", { type: "button", class: "btn", onclick: () => copyText(json, t("research.copied")) }, t("research.copy")),
        h("button", { type: "button", class: "btn", onclick: () => copyText(location.href, t("research.link_copied")) }, t("research.copy_link"))),
      h("h4", null, t("research.counts")),
      h("ul", { class: "plain" },
        h("li", null, t("research.count_nodes", { n: fmt(c.nodes), links: fmt(c.links) })),
        h("li", null, t("research.count_claims", { a: fmt(c.assertions), r: fmt(c.records) })),
        h("li", null, t("research.count_status", { list: Object.entries(c.status).map(([k, v]) => `${k}: ${fmt(v)}`).join(", ") })),
        h("li", null, t("research.version", { v: META.version }))),
      h("h4", null, t("research.sources")),
      h("ul", { class: "plain" }, SRC.map((s, k) => h("li", null, srcLabel(k)))));
  }

  // ------------------------------------------------------------------ orientation and text alternative
  function frameName() {
    const w = S.weights;
    const d = dominant();
    if (w[d] > 0.985) return t("frame." + FRAMES[d]);
    return FRAMES.map((f, k) => [f, w[k]]).filter((x) => x[1] > 0.01).sort((a, b) => b[1] - a[1])
      .map(([f, x]) => t("here.blend_part", { frame: t("frame." + f), pct: Math.round(x * 100) })).join(" + ");
  }
  function shownCount() {
    let shown = 0;
    for (let i = 0; i < n; i++) if (visible(i)) shown++;
    return shown;
  }
  function updateHere() {
    const parts = [t("here.lens", { lens: t("lens." + S.lens) }), t("here.frame", { frame: frameName() })];
    if (S.focus >= 0) parts.push(t("here.focus", { name: N[S.focus].n }));
    if (S.trace.a >= 0 && S.trace.b >= 0) parts.push(t("here.trace", { a: N[S.trace.a].n, b: N[S.trace.b].n }));
    if (S.preset) parts.push(t("here.vantage", { name: t("preset." + S.preset) }));
    parts.push(S.scrub.on ? t("here.period", { y0: S.scrub.y0, y1: S.scrub.y1 }) : t("here.period_all"));
    byId("obs-here").textContent = parts.join(" · ");
    const shown = shownCount();
    const hidden = [...S.hidden].map((k) => t("kind.plural." + k)).join(", ");
    byId("obs-scale").textContent = t("scale.showing", { shown: fmt(shown), total: fmt(n) }) + (hidden ? " " + t("scale.hidden", { list: hidden }) : "")
      + (S.scrub.on ? " " + t("scale.period", { inside: fmt(countPresence(1)), undated: fmt(countPresence(0)) }) : "");
    canvas.setAttribute("aria-label", t("canvas.label", { frame: frameName(), shown: fmt(shown), total: fmt(n) }));
  }
  function countPresence(v) { let k = 0; for (let i = 0; i < n; i++) if (visible(i) && presence(i) === v) k++; return k; }

  function regionCounts(f) {
    const m = new Map();
    for (let i = 0; i < n; i++) { if (!visible(i)) continue; const r = FR[f].region[i]; m.set(r, (m.get(r) || 0) + 1); }
    return m;
  }
  function updateTextAlt() {
    const box = byId("obs-textalt-body");
    box.replaceChildren();
    const d = FRAMES[dominant()];
    const shown = shownCount();
    const kinds = KINDS.filter((k) => !S.hidden.has(k)).map((k) => t("textalt.kind_count", { n: fmt(N.filter((x) => x.k === k).length), kind: t("kind.plural." + k) })).join(", ");
    let linkCount = 0; for (let li = 0; li < L.length; li++) if (linkLvl[li]) linkCount++;
    box.append(h("p", null, t("textalt.summary", { frame: frameName(), lens: t("lens." + S.lens), shown: fmt(shown), total: fmt(n), kinds, links: fmt(linkCount) })));
    if (S.hidden.size) box.append(h("p", null, t("textalt.hidden", { list: [...S.hidden].map((k) => t("kind.plural." + k)).join(", ") })));
    else box.append(h("p", null, t("textalt.nothing_hidden")));
    if (S.scrub.on) box.append(h("p", null, t("textalt.period", { y0: S.scrub.y0, y1: S.scrub.y1, inside: fmt(countPresence(1)), outside: fmt(countPresence(-1)), undated: fmt(countPresence(0)) })));
    box.append(h("p", null, t("textalt.status", { n: fmt(META.counts.assertions) })));
    const rc = regionCounts(d);
    const regionText = [...rc.entries()].map(([r, k]) => t("textalt.region." + d + "." + r, { n: fmt(k) })).join(" ");
    box.append(h("p", null, t("textalt.frame." + d), " ", regionText));
    if (d === "isnad") {
      for (const ch of CHAINS) {
        const names = [];
        if (ch.links.length) names.push(N[ch.links[0][0]].n);
        for (const ln of ch.links) names.push(N[ln[1]].n);
        box.append(h("p", null, t("textalt.chain", { label: ch.label || "—", list: names.join(" → ") })));
      }
    }
    if (S.focus >= 0) {
      const i = S.focus;
      const rows = rowsFor(i);
      const groups = new Map();
      for (const r of rows) {
        const k = N[r.o].k === "person" || N[r.o].k === "group" ? "class." + C[r.ci].c : "kind.plural." + N[r.o].k;
        if (!groups.has(k)) groups.set(k, new Set());
        groups.get(k).add(`${C[r.ci].p} ${N[r.o].n} (${t(C[r.ci].st ? "status." + C[r.ci].st : "status.none")})`);
      }
      box.append(h("h3", null, t("textalt.focus", { name: N[i].n, kind: t("kind." + N[i].k) })));
      const ul = h("ul", null);
      for (const [k, set] of groups) ul.append(h("li", null, t(k) + ": " + [...set].join("; ")));
      if (N[i].tb) ul.append(h("li", null, t("panel.generation", { value: N[i].tb })));
      if (N[i].d) ul.append(h("li", null, t("textalt.dates", { value: N[i].d.map((x) => x[2]).join("; ") })));
      if (!rows.length) ul.append(h("li", null, t("panel.none_recorded")));
      box.append(ul);
    }
    const path = selectedPath();
    if (path) {
      box.append(h("h3", null, t("textalt.thread", { a: N[S.trace.a].n, b: N[S.trace.b].n, steps: path.hops.length })));
      const ol = h("ol", null);
      for (const hop of path.hops) {
        const cl = L[hop.li].cl.map((ci) => C[ci]);
        ol.append(h("li", null, cl.map((c) => `${N[c.s].n} ${c.p} ${N[c.o].n} (${t(c.st ? "status." + c.st : "status.none")})`).join("; ")));
      }
      box.append(ol);
    }
    // every item, grouped by where this view puts it; each is a button (keyboard route to every node)
    const det = h("details", { class: "all-items" }, h("summary", null, t("textalt.all_items", { n: fmt(shown) })));
    for (const [r] of rc) {
      const items = [];
      for (let i = 0; i < n; i++) if (visible(i) && FR[d].region[i] === r) items.push(i);
      items.sort((a, b) => N[a].n.localeCompare(N[b].n));
      det.append(h("h4", null, t("textalt.region_title." + d + "." + r, { n: fmt(items.length) })));
      det.append(h("ul", { class: "items" }, items.map((i) => h("li", null, nodeBtn(i, "inline")))));
    }
    box.append(det);
  }

  let announceTimer = 0;
  function announce(msg) {
    clearTimeout(announceTimer);
    announceTimer = setTimeout(() => { byId("obs-announce").textContent = msg; }, 60);
  }

  // ------------------------------------------------------------------ controls
  function syncFrameControls() {
    const d = dominant();
    FRAMES.forEach((f, k) => {
      const b = byId("frame-" + f);
      if (b) b.setAttribute("aria-pressed", S.weights[k] > 0.985 ? "true" : "false");
    });
    // slider position: exact for one frame or two neighbours, else the dominant frame
    const nz = S.weights.map((w, k) => [w, k]).filter((x) => x[0] > 0.001);
    let v = d;
    if (nz.length === 2 && Math.abs(nz[0][1] - nz[1][1]) === 1) v = nz[0][1] + nz[1][0];
    const slider = byId("obs-morph");
    slider.value = String(Math.round(v * 100) / 100);
    slider.setAttribute("aria-valuetext", frameName());
  }
  function sliderWeights(v) {
    const w = [0, 0, 0, 0, 0];
    const f0 = Math.floor(v), f1 = Math.min(4, f0 + 1), fr = v - f0;
    w[f0] += 1 - fr; if (f1 !== f0) w[f1] += fr;
    return w;
  }
  function syncScrub() {
    byId("scrub-on").checked = S.scrub.on;
    byId("scrub-from").value = String(S.scrub.y0);
    byId("scrub-to").value = String(S.scrub.y1);
    byId("scrub-from-out").textContent = t("scrub.year", { y: S.scrub.y0 });
    byId("scrub-to-out").textContent = t("scrub.year", { y: S.scrub.y1 });
    byId("scrub-from").disabled = byId("scrub-to").disabled = !S.scrub.on;
  }
  function syncLegend() {
    for (const k of KINDS) {
      const b = byId("type-" + k);
      if (b) b.setAttribute("aria-pressed", S.hidden.has(k) ? "false" : "true");
    }
  }
  function syncLens() {
    for (const l of LENSES) {
      const r = byId("lens-" + l);
      if (r) r.checked = S.lens === l;
    }
    document.documentElement.dataset.lens = S.lens;
  }

  function lineSample(cls) {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 36 10"); svg.setAttribute("class", "ls"); svg.setAttribute("aria-hidden", "true");
    const line = (y) => {
      const l = document.createElementNS(ns, "line");
      l.setAttribute("x1", "1"); l.setAttribute("x2", "35"); l.setAttribute("y1", String(y)); l.setAttribute("y2", String(y));
      l.setAttribute("class", "ls-" + cls);
      if (DASH[cls].length) l.setAttribute("stroke-dasharray", DASH[cls].join(" "));
      svg.append(l);
    };
    if (cls === "kinship") { line(3.4); line(6.6); } else line(5);
    if (cls === "transmission") {
      const p = document.createElementNS(ns, "path");
      p.setAttribute("d", "M22 5 L16 1.8 L16 8.2 Z"); p.setAttribute("class", "ls-arrow"); svg.append(p);
    }
    return svg;
  }

  function buildLegend() {
    const types = byId("legend-types");
    for (const k of KINDS) {
      types.append(h("li", null, h("button", { type: "button", id: "type-" + k, class: "type-toggle", "aria-pressed": "true",
        onclick: () => { if (S.hidden.has(k)) S.hidden.delete(k); else S.hidden.add(k); syncLegend(); update(true); announce(t(S.hidden.has(k) ? "announce.hidden" : "announce.shown", { kind: t("kind.plural." + k) })); } },
      swatch(k), " ", t("legend.kind." + k), h("span", { class: "count" }, " " + fmt(META.counts.kinds[k] || 0)))));
    }
    const lines = byId("legend-lines");
    for (const cls of CLASSES) lines.append(h("li", null, lineSample(cls), " ", t("class." + cls), h("span", { class: "muted" }, " — " + t("legend.class." + cls))));
  }

  // ------------------------------------------------------------------ update
  function update(moveCamera) {
    computeEmphasis();
    if (moveCamera) {
      if (S.camMode === "free") S.camMode = S.focus >= 0 || S.hl || selectedPath() ? "focus" : "fit";
      if (!anim) animateTo(null);
    }
    renderPanel();
    updateHere();
    updateTextAlt();
    writeHash();
    requestDraw();
  }

  // ------------------------------------------------------------------ input
  const pointers = new Map();
  let gesture = null;
  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.offsetX, y: e.offsetY });
    if (pointers.size === 1) gesture = { type: "pan", x0: e.offsetX, y0: e.offsetY, cam0: Object.assign({}, S.cam), moved: false };
    else if (pointers.size === 2) {
      const [p, q] = [...pointers.values()];
      gesture = { type: "pinch", d0: Math.hypot(p.x - q.x, p.y - q.y) || 1, m0: { x: (p.x + q.x) / 2, y: (p.y + q.y) / 2 }, cam0: Object.assign({}, S.cam), moved: true };
    }
  });
  canvas.addEventListener("pointermove", (e) => {
    if (pointers.has(e.pointerId)) pointers.set(e.pointerId, { x: e.offsetX, y: e.offsetY });
    if (gesture && gesture.type === "pan" && pointers.size === 1) {
      const dx = e.offsetX - gesture.x0, dy = e.offsetY - gesture.y0;
      if (!gesture.moved && Math.hypot(dx, dy) > 5) gesture.moved = true;
      if (gesture.moved) {
        anim = null;
        S.camMode = "free";
        S.cam = { x: gesture.cam0.x - dx / S.cam.k, y: gesture.cam0.y - dy / S.cam.k, k: S.cam.k };
        requestDraw();
      }
    } else if (gesture && gesture.type === "pinch" && pointers.size === 2) {
      const [p, q] = [...pointers.values()];
      const d = Math.hypot(p.x - q.x, p.y - q.y) || 1, m = { x: (p.x + q.x) / 2, y: (p.y + q.y) / 2 };
      const k = Math.max(0.02, Math.min(80, gesture.cam0.k * (d / gesture.d0)));
      const wx = (gesture.m0.x - W / 2) / gesture.cam0.k + gesture.cam0.x, wy = (gesture.m0.y - H / 2) / gesture.cam0.k + gesture.cam0.y;
      anim = null; S.camMode = "free";
      S.cam = { x: wx - (m.x - W / 2) / k, y: wy - (m.y - H / 2) / k, k };
      requestDraw();
    } else if (e.pointerType === "mouse" && !gesture) {
      const i = nodeAt(e.offsetX, e.offsetY);
      if (i !== S.hover) { S.hover = i; canvas.style.cursor = i >= 0 ? "pointer" : "grab"; requestDraw(); }
    }
  });
  const endPointer = (e) => {
    const g = gesture;
    pointers.delete(e.pointerId);
    if (g && g.type === "pan" && !g.moved && e.type === "pointerup") tap(e.offsetX, e.offsetY);
    if (pointers.size === 1) { const [p] = [...pointers.values()]; gesture = { type: "pan", x0: p.x, y0: p.y, cam0: Object.assign({}, S.cam), moved: true }; }
    else if (pointers.size === 0) { gesture = null; if (g && g.moved) { updateHere(); writeHash(); } }
  };
  canvas.addEventListener("pointerup", endPointer);
  canvas.addEventListener("pointercancel", endPointer);
  canvas.addEventListener("pointerleave", () => { if (S.hover >= 0) { S.hover = -1; requestDraw(); } });
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    zoomAt(e.offsetX, e.offsetY, Math.exp(-e.deltaY * (e.deltaMode === 1 ? 0.05 : 0.0016)));
  }, { passive: false });
  function zoomAt(x, y, f) {
    const k = Math.max(0.02, Math.min(80, S.cam.k * f));
    const wx = (x - W / 2) / S.cam.k + S.cam.x, wy = (y - H / 2) / S.cam.k + S.cam.y;
    anim = null; S.camMode = "free";
    S.cam = { x: wx - (x - W / 2) / k, y: wy - (y - H / 2) / k, k };
    requestDraw();
    writeHash();
  }
  function tap(x, y) {
    const i = nodeAt(x, y);
    if (i >= 0) {
      if (S.picking && S.trace.a >= 0 && i !== S.trace.a) { runTrace(S.trace.a, i); return; }
      focusNode(i);
      return;
    }
    const li = linkAt(x, y);
    if (li >= 0) {
      const l = L[li];
      const lis = [];
      L.forEach((m, k) => { if (m.a === l.a && m.b === l.b) lis.push(k); });
      interrogateLinks(lis);
    }
  }
  canvas.addEventListener("keydown", (e) => {
    const step = 60 / S.cam.k;
    let handled = true;
    switch (e.key) {
      case "ArrowLeft": S.cam.x -= step; S.camMode = "free"; break;
      case "ArrowRight": S.cam.x += step; S.camMode = "free"; break;
      case "ArrowUp": S.cam.y -= step; S.camMode = "free"; break;
      case "ArrowDown": S.cam.y += step; S.camMode = "free"; break;
      case "+": case "=": zoomAt(W / 2, H / 2, 1.25); break;
      case "-": case "_": zoomAt(W / 2, H / 2, 0.8); break;
      case "0": S.camMode = S.focus >= 0 ? "focus" : "fit"; animateTo(null); break;
      case "Escape": if (S.links || S.nodeLadder) back(); else if (S.focus >= 0 || S.trace.a >= 0 || S.hl) clearFocus(); break;
      case "Enter": case " ": {
        const i = nodeAt(W / 2, H / 2) >= 0 ? nodeAt(W / 2, H / 2) : nearestToCentre();
        if (i >= 0) focusNode(i);
        break;
      }
      default: handled = false;
    }
    if (handled) { e.preventDefault(); requestDraw(); }
  });
  function nearestToCentre() {
    let best = -1, bd = Infinity;
    for (let i = 0; i < n; i++) {
      if (!nodeA[i] || nodeA[i] < 0.5) continue;
      const d = Math.hypot(sx(P[2 * i]) - W / 2, sy(P[2 * i + 1]) - H / 2);
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  }
  document.addEventListener("keydown", (e) => {
    const tag = (e.target && e.target.tagName) || "";
    if (e.key === "/" && !/INPUT|TEXTAREA|SELECT/.test(tag)) { e.preventDefault(); byId("obs-search").focus(); }
  });

  // header and controls
  byId("obs-back").addEventListener("click", back);
  byId("obs-home").addEventListener("click", home);
  byId("obs-close").addEventListener("click", () => { if (S.focus >= 0 || S.panel !== "intro") clearFocus(); else closeSheet(); });
  const search = byId("obs-search");
  const doSearch = () => {
    const i = byOption.get(search.value);
    if (i !== undefined) { focusNode(i); search.value = ""; }
    else {
      const q = search.value.trim().toLowerCase();
      if (!q) return;
      const hit = N.findIndex((nd) => nd.n.toLowerCase().includes(q));
      if (hit >= 0) { focusNode(hit); search.value = ""; } else announce(t("search.none", { q: search.value }));
    }
  };
  byId("obs-search-form").addEventListener("submit", (e) => { e.preventDefault(); doSearch(); });
  search.addEventListener("change", () => { if (byOption.has(search.value)) doSearch(); });
  for (const l of LENSES) {
    byId("lens-" + l).addEventListener("change", () => {
      S.lens = l; syncLens(); fontCache.clear();
      S.evidence = l === "discover" ? "folded" : "expanded";
      relabelStatic();
      update(false);
      announce(t("announce.lens", { lens: t("lens." + l) }));
    });
  }
  FRAMES.forEach((f, k) => {
    byId("frame-" + f).addEventListener("click", () => {
      const w = [0, 0, 0, 0, 0]; w[k] = 1;
      if (S.camMode === "free") S.camMode = S.focus >= 0 || S.hl || selectedPath() ? "focus" : "fit";
      animateTo(w);
      announce(t("announce.frame", { frame: t("frame." + f) }));
      setTimeout(() => { updateHere(); updateTextAlt(); writeHash(); }, reduceMotion ? 0 : 720);
    });
  });
  byId("obs-morph").addEventListener("input", (e) => {
    anim = null;
    S.weights = sliderWeights(+e.target.value);
    blend();
    if (S.camMode === "fit") S.cam = fitAll(); else if (S.camMode === "focus") S.cam = fitEgo();
    e.target.setAttribute("aria-valuetext", frameName());
    FRAMES.forEach((f, k) => byId("frame-" + f).setAttribute("aria-pressed", S.weights[k] > 0.985 ? "true" : "false"));
    updateHere();
    requestDraw();
  });
  byId("obs-morph").addEventListener("change", () => { S.baseK = fitAll().k; updateTextAlt(); writeHash(); });
  byId("scrub-on").addEventListener("change", (e) => { S.scrub.on = e.target.checked; syncScrub(); update(false); });
  const scrubInput = () => {
    let a = +byId("scrub-from").value, b = +byId("scrub-to").value;
    if (a > b) [a, b] = [b, a];
    S.scrub.y0 = a; S.scrub.y1 = b;
    byId("scrub-from-out").textContent = t("scrub.year", { y: a });
    byId("scrub-to-out").textContent = t("scrub.year", { y: b });
    computeEmphasis(); updateHere(); requestDraw();
  };
  byId("scrub-from").addEventListener("input", scrubInput);
  byId("scrub-to").addEventListener("input", scrubInput);
  byId("scrub-from").addEventListener("change", () => update(false));
  byId("scrub-to").addEventListener("change", () => update(false));
  byId("obs-preset").addEventListener("change", (e) => applyPreset(e.target.value));
  byId("obs-trace").addEventListener("click", () => {
    pushHistory();
    S.panel = "trace"; S.trace.open = true;
    if (S.focus >= 0 && S.trace.a < 0) { S.trace.a = S.focus; S.picking = true; }
    update(false); openSheet();
  });
  window.addEventListener("resize", resize);

  // static strings that depend on the lens (plain words in Discover)
  function relabelStatic() {
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  }

  // ------------------------------------------------------------------ start
  function start() {
    const preset = byId("obs-preset");
    for (const p of PRESETS) preset.append(h("option", { value: p.key }, t("preset." + p.key)));
    const dl = byId("obs-names");
    N.forEach((nd, i) => dl.append(h("option", { value: optionLabel[i] })));
    buildLegend();
    const sf = byId("scrub-from"), st = byId("scrub-to");
    for (const el of [sf, st]) { el.min = String(FR.time.axis.y0); el.max = String(FR.time.axis.y1); el.step = "1"; }
    const fromHash = readHash();
    if (!fromHash && S.lens === "discover") S.weights = [0, 0, 0, 1, 0];
    S.evidence = S.lens === "discover" ? "folded" : "expanded";
    syncLens(); relabelStatic(); syncScrub(); syncLegend();
    blend();
    computeEmphasis();
    resize();
    if (S.camMode !== "free") S.cam = S.camMode === "focus" ? fitEgo() : fitAll();
    syncFrameControls();
    renderPanel(); updateHere(); updateTextAlt();
    if (S.focus >= 0 || S.panel !== "intro") panel.dataset.open = "true";
    byId("obs-back").disabled = true;
    document.documentElement.dataset.ready = "true";
    requestDraw();
  }
  start();
})();
