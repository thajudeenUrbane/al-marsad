/* al-Marṣad Observatory: the flat (2D) renderer. One canvas; the five precomputed
 * frames are blended by weight and drawn with type hues, shapes, line styles and the
 * "not yet reviewed" texture (docs/04 §3). Inlined before observatory.js, which calls
 * window.MarsadRenderer(api) once and uses the object it returns. */
window.MarsadRenderer = function (api) {
  "use strict";
  const { S, N, L, C, FR, FRAMES, CLASSES, KINDS, DASH, n, byId, reduceMotion, nodeA, nodeHollow, nodeLvl, linkLvl,
    visible, selectedPath, focusNode, runTrace, interrogateLinks, back, clearFocus, syncFrameControls, updateHere,
    writeHash } = api;
  // ------------------------------------------------------------------ colours (defined once, in CSS)
  const css = getComputedStyle(document.documentElement);
  const cv = (name) => css.getPropertyValue(name).trim();
  const COL = {
    bg: cv("--bg"), ink: cv("--ink"), muted: cv("--muted"), line: cv("--line"),
    lineHi: cv("--line-hi"), ring: cv("--ring"), hatch: cv("--hatch"), deco: cv("--deco"),
  };
  KINDS.forEach((k) => { COL[k] = cv("--c-" + k); });
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
    DPR = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(W * DPR); canvas.height = Math.round(H * DPR);
    makePatterns();
    S.baseK = fitAll().k;
    if (S.camMode !== "free") S.cam = S.camMode === "focus" ? fitEgo() : fitAll();
    requestDraw();
  }

  // ------------------------------------------------------------------ camera
  function bbox(indices, withDeco) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const add = (x, y) => { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; };
    for (const i of indices) if (visible(i)) add(P[2 * i], P[2 * i + 1]);
    if (withDeco) {
      FRAMES.forEach((f, fi) => {
        if (S.weights[fi] < 0.25) return;
        for (const d of FR[f].deco) {
          if (d.t === "text") add(d.x, d.y);
          else if (d.t === "line") { add(d.x1, d.y1); add(d.x2, d.y2); }
          else if (d.t === "circle") { add(d.x - d.r, d.y - d.r); add(d.x + d.r, d.y + d.r); }
        }
      });
    }
    if (x0 === Infinity) return { x0: -500, y0: -500, x1: 500, y1: 500 };
    return { x0, y0, x1, y1 };
  }
  // On a phone the open bottom sheet covers the lower part of the canvas (once the canvas
  // is scrolled to the top); fitting leaves that part out so the focus stays visible.
  function bottomInset() {
    const pn = byId("obs-panel");
    if (!pn || pn.dataset.open !== "true" || getComputedStyle(pn).position !== "fixed") return 0;
    const visible = window.innerHeight - pn.getBoundingClientRect().height;
    const offset = canvas.getBoundingClientRect().top - byId("obs-stage-wrap").getBoundingClientRect().top;
    return Math.max(0, Math.min(H * 0.6, offset + H - visible));
  }
  function fitTo(b, pad) {
    const bw = Math.max(b.x1 - b.x0, 60), bh = Math.max(b.y1 - b.y0, 60);
    const p = pad === undefined ? 30 : pad, top = p + 44, ins = bottomInset();
    const k = Math.max(0.02, Math.min(60, Math.min((W - 2 * p) / bw, (H - top - p - ins) / bh)));
    return { x: (b.x0 + b.x1) / 2, y: (b.y0 + b.y1) / 2 - (top - p - ins) / 2 / k, k };
  }
  const allIdx = Array.from({ length: n }, (_, i) => i);
  const fitAll = () => fitTo(bbox(allIdx, true));
  function fitEgo() {
    if (api.emph() && api.emph().size) {
      const f = fitTo(bbox(api.emph()), 60);
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
  let settleTimer = 0;
  function frame(now) {
    drawQueued = false;
    const moving = !!anim || !!(gesture && gesture.moved) || now - lastWheel < 120;
    if (anim) {
      const p = Math.min(1, (now - anim.t0) / anim.dur), e = ease(p);
      S.weights = anim.wFrom.map((w, f) => w + (anim.wTo[f] - w) * e);
      blend();
      const target = S.camMode === "fit" ? fitAll() : S.camMode === "focus" ? fitEgo() : null;
      if (target) S.cam = lerpCam(anim.camFrom, target, e);
      if (p >= 1) { anim = null; S.weights = S.weights.map((w) => Math.round(w * 1000) / 1000); S.baseK = fitAll().k; syncFrameControls(); updateHere(); }
    }
    draw(moving);
    if (anim) requestDraw();
    else if (moving) { clearTimeout(settleTimer); settleTimer = setTimeout(requestDraw, 140); }
  }

  // ------------------------------------------------------------------ drawing
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
    // frame text keeps its pixel size near the fit zoom and shrinks when zoomed far out,
    // so stacked headings never run into the rows they label
    const f0 = Math.max(0.55, Math.min(1, S.cam.k / 0.6));
    FRAMES.forEach((f, fi) => {
      const w = S.weights[fi];
      if (w < 0.02) return;
      for (const d of FR[f].deco) {
        const a = w * (d.o === undefined ? 1 : d.o);
        ctx.globalAlpha = a;
        if (d.t === "text") {
          ctx.font = FONT(Math.max(7, (d.z || 11) * f0), d.w || 400);
          ctx.fillStyle = COL.deco;
          ctx.textAlign = d.a === "middle" ? "center" : d.a === "end" ? "right" : "left";
          ctx.textBaseline = "alphabetic";
          ctx.fillText(d.s, sx(d.x), sy(d.y) + (d.dy || 0) * f0);
        } else if (d.t === "line") {
          ctx.strokeStyle = COL.deco; ctx.lineWidth = 1; ctx.setLineDash([]);
          ctx.beginPath(); ctx.moveTo(sx(d.x1), sy(d.y1) + (d.dy || 0) * f0); ctx.lineTo(sx(d.x2), sy(d.y2) + (d.dy || 0) * f0); ctx.stroke();
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
    const alphaFor = [0, 0.035 + 0.05 * wNet, 0.1 + 0.3 * wNet, 0.3 + 0.6 * wNet, 1];
    const widthFor = [0, 1.2, 1.4, 2.1, 3];
    for (let lv = 1; lv <= 4; lv++) {
      for (const cls of CLASSES) {
        let any = false;
        ctx.beginPath();
        for (let li = 0; li < L.length; li++) {
          if (linkLvl[li] !== lv || L[li].c !== cls) continue;
          const l = L[li];
          const x1 = sx(P[2 * l.a]), y1 = sy(P[2 * l.a + 1]), x2 = sx(P[2 * l.b]), y2 = sy(P[2 * l.b + 1]);
          if (cls === "kinship" && !FAST) {
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
        ctx.setLineDash(FAST ? [] : DASH[cls]);
        // every link is unreviewed today: drawn with the grain texture (docs/04 §3)
        ctx.strokeStyle = FAST ? (lv >= 3 ? COL.lineHi : COL.line) : (lv >= 3 ? grainPatternHi : grainPattern);
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
      if (FAST) continue;
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
    const push = (i, pri) => { if (i >= 0 && nodeA[i] > 0.5) out.push([pri, i, 1]); };
    // map labels and chain names stay readable even when dimmed: they are the frame's structure
    const pushStructural = (i, pri) => { if (i >= 0 && nodeA[i] > 0) out.push([pri, i, nodeA[i] > 0.5 ? 1 : 0.6]); };
    if (S.hover >= 0) push(S.hover, 9);
    push(S.focus, 8);
    if (path) { push(S.trace.a, 7); push(S.trace.b, 7); for (const hop of path.hops) push(hop.to, 6); }
    if (api.emph()) {
      let k = 0;
      for (const i of api.emph()) {
        if (disc && N[i].k !== "story" && k++ > 10) continue;
        push(i, disc && N[i].k === "story" ? 5 : 4);
      }
    }
    for (let i = 0; i < n; i++) {
      if (!nodeA[i]) continue;
      const kind = N[i].k;
      if (wd[2] > 0.5 && kind === "place" && FR.geo.region[i] === "map") pushStructural(i, 6.5);
      if (wd[4] > 0.5 && FR.isnad.region[i] === "chain") pushStructural(i, 6.5);
      if (nodeA[i] < 0.5) continue;
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
    // the label budget follows the canvas area, so a phone gets fewer than a desktop
    const max = Math.min(FAST ? 12 : S.lens === "discover" ? 40 : 160, Math.max(10, Math.round((W * H) / 6000)));
    ctx.textBaseline = "middle"; ctx.textAlign = "left";
    for (const [pri, i, alpha] of cands) {
      if (seen.has(i)) continue;
      seen.add(i);
      if (count >= max && pri < 6) break;
      const font = FONT(pri >= 8 ? 13 : 12, pri >= 7 ? 600 : 400);
      const text = N[i].n;
      const w = textW(text, font);
      const nx = sx(P[2 * i]), y = sy(P[2 * i + 1]);
      // a label that would run off the right edge is set to the left of its mark
      const flip = nx + r + 5 + w > W - 4 && nx - r - 5 - w > 4;
      const x = flip ? nx - r - 5 - w : nx + r + 5;
      if (x > W || y < 0 || y > H || x + w < 0) continue;
      const box = [x - 2, y - 8, x + w + 2, y + 8];
      if (pri < 7 && placed.some((b) => b[0] < box[2] && b[2] > box[0] && b[1] < box[3] && b[3] > box[1])) continue;
      placed.push(box);
      ctx.font = font;
      ctx.globalAlpha = alpha;
      if (!FAST) { ctx.lineWidth = 3.5; ctx.strokeStyle = COL.bg; ctx.lineJoin = "round"; ctx.strokeText(text, x, y); }
      ctx.fillStyle = pri >= 4 ? COL.ink : COL.muted;
      ctx.fillText(text, x, y);
      count++;
    }
    ctx.globalAlpha = 1;
  }

  // While the view moves (morph, pan, pinch, wheel) a cheaper frame is drawn: plain
  // strokes, no texture overlays, no text outlines, only the most important labels.
  // The full frame, with every texture, follows as soon as the motion stops.
  let FAST = false;
  function draw(fast) {
    FAST = !!fast;
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

  // ------------------------------------------------------------------ input
  const pointers = new Map();
  // a finger tap opens the panel under the finger; cancelling the touch end stops the
  // browser's follow-up click from landing on a button in it
  canvas.addEventListener("touchend", (e) => { if (e.cancelable) e.preventDefault(); }, { passive: false });
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
  let lastWheel = -1e9;
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    lastWheel = performance.now();
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
  window.addEventListener("resize", resize);

  return {
    start() {
      resize();
      if (S.camMode !== "free") S.cam = S.camMode === "focus" ? fitEgo() : fitAll();
    },
    requestDraw,
    animateTo,
    isAnimating: () => !!anim,
    stopAnim() { anim = null; },
    blend,
    // the visible part of the canvas changed (bottom sheet, morph): fit again unless moving
    refit() {
      if (anim || S.camMode === "free") return;
      S.cam = S.camMode === "focus" ? fitEgo() : fitAll();
      requestDraw();
    },
    rebase() { S.baseK = fitAll().k; },
    cameraState: () => ({ x: Math.round(S.cam.x), y: Math.round(S.cam.y), zoom: Math.round(S.cam.k * 1000) / 1000 }),
    applyCamera(c) {
      if (typeof c.zoom !== "number") return false;
      S.cam = { x: +c.x || 0, y: +c.y || 0, k: c.zoom };
      return true;
    },
    clearCaches() { fontCache.clear(); },
  };
};
