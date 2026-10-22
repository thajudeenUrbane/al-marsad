/* Sky Atlas, part 3 of 10 — showing a view, blending views, the look of every mark at
   this moment (focus, period, history, filters), the names, and what is drawn over and
   under the sky. */
let CUR = null;          // the current view's data (or a blend of two)
function setView(view, opts) {
  opts = opts || {};
  if (view === "lineage") {
    const f = opts.of !== undefined ? opts.of : S.focus;
    if (f < 0 || KIND[f] !== "person") { toast(t("lineage.need")); return; }
    S.lineageOf = f; LOG.lineages++;
  }
  if (opts.record !== false) pushHistory();
  S.view = view; S.blend = null;
  LOG.views[view] = 1; saveLog(); checkMilestones(); checkQuests();
  CUR = viewData(view);
  S.visible = CUR.vis;
  R.morphTo(CUR.pos, opts.instant ? 0 : 1000);
  R.setExtra(CUR.extra);
  R.setGlobe(view === "globe" ? { c: [0, 0, 0], r: R_GLOBE } : null);
  if (opts.camera !== false) R.flyTo(viewCamera(view), opts.instant ? 0 : 1100);
  const bi = BLEND.indexOf(view);
  if (bi >= 0) $("blend").value = String(bi);
  syncViewTabs();
  restyle();
  caption(); here(); refreshText();
}
function syncViewTabs() {
  document.querySelectorAll(".views button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.view === S.view)));
}
// the blend slider: the same marks between two neighbouring views, worked out in advance
let blendRaf = 0;
function setBlend(v) {
  S.blend = v;
  if (blendRaf) return;
  blendRaf = requestAnimationFrame(() => {
    blendRaf = 0;
    const x = Math.max(0, Math.min(BLEND.length - 1, S.blend)), k = Math.min(BLEND.length - 2, Math.floor(x)), f = x - k;
    const A = viewData(BLEND[k]), B = viewData(BLEND[k + 1]);
    const pos = new Float32Array(n * 3), vis = new Uint8Array(n);
    for (let i = 0; i < n; i++) {
      // a mark a view leaves out stays where the other view puts it
      const wa = A.vis[i] ? (B.vis[i] ? 1 - f : 1) : 0;
      for (let j = 0; j < 3; j++) pos[3 * i + j] = A.vis[i] && B.vis[i] ? A.pos[3 * i + j] * (1 - f) + B.pos[3 * i + j] * f : (wa ? A.pos[3 * i + j] : B.pos[3 * i + j]);
      vis[i] = (A.vis[i] && (f < 0.98 || B.vis[i])) || (B.vis[i] && (f > 0.02 || A.vis[i])) ? 1 : 0;
    }
    const near = f < 0.5 ? BLEND[k] : BLEND[k + 1];
    S.view = near;
    const shelfAB = new Uint8Array(n); for (let i = 0; i < n; i++) shelfAB[i] = A.shelf[i] | B.shelf[i];
    CUR = { pos, vis, labels: (f < 0.5 ? A : B).labels, extra: (f < 0.08 ? A : f > 0.92 ? B : null) ? (f < 0.5 ? A : B).extra : null, shelf: shelfAB };
    S.visible = vis;
    R.setPositions(pos);
    R.setExtra(CUR.extra);
    R.setGlobe(near === "globe" && (f < 0.02 || f > 0.98) ? { c: [0, 0, 0], r: R_GLOBE } : null);
    syncViewTabs();
    restyle(); caption(); here();
  });
}

// ------------------------------------------------------------------ the look of every mark now
function visibleNow(i) {
  if (i === LIGHT) return false;
  if (S.visible && !S.visible[i]) return false;
  if (!S.show.kinds[KIND[i]]) return false;
  if (!S.show.background && isBack(i) && !(S.lit && S.lit.has(i))) return false;
  return true;
}
const hollowOn = () => !!(S.period || S.play || S.show.hollow);
function timeAlpha(i) { // dated marks outside the period, or not yet lit in history, dim; undated never do
  const sp = yearSpan(i);
  if (!sp) return 1;
  if (S.play && sp[0] > S.play.y + 1) return 0.06;
  if (S.period && (sp[1] < S.period[0] || sp[0] > S.period[1] + 1)) return 0.1;
  return 1;
}
let pairsCache = null;
function linkPairs() { // one line per pair and kind of relationship
  if (pairsCache) return pairsCache;
  const seen = new Set(), out = [];
  for (let c = 0; c < nc; c++) {
    const a = Math.min(CL.s[c], CL.o[c]), b = Math.max(CL.s[c], CL.o[c]);
    if (a === b) continue;
    const key = a * 72000 + b * 8 + CLASS_ORDER.indexOf(pclass(c));
    if (seen.has(key)) continue;
    seen.add(key); out.push([a, b, pclass(c)]);
  }
  pairsCache = out;
  return out;
}
let shownCount = 0, linesCount = 0;
function restyle() {
  const cols = new Float32Array(n * 4), shapes = new Float32Array(n), glows = new Float32Array(n);
  const hollow = hollowOn();
  shownCount = 0;
  for (let i = 0; i < n; i++) {
    const [c, s, g] = markStyle(i);
    let a = visibleNow(i) ? 1 : 0;
    if (a) shownCount++;
    if (a && S.lit && !S.lit.has(i)) a = 0.11;
    if (a && (S.play || S.period)) a = Math.min(a, timeAlpha(i));
    if (a && KIND[i] === "person" && nf("tb", i) === undefined && !isOpp(i) && S.show.light === "generation") a *= 0.86;
    cols.set([c[0], c[1], c[2], a], 4 * i);
    shapes[i] = s + (hollow && !yearSpan(i) ? 10 : 0);
    glows[i] = a > 0.5 ? g : 0;
  }
  R.setStyle(cols, shapes, glows);
  const pairs = [], lc = [];
  if (S.show.lines) {
    const flat = S.view !== "sky";
    for (const [a, b, cls] of linkPairs()) {
      if (!visibleNow(a) && a !== LIGHT) continue;
      if (!visibleNow(b) && b !== LIGHT) continue;
      if (S.lineClasses && !S.lineClasses.includes(cls)) continue;
      // a mark waiting on a shelf draws no lines, unless it is lit
      if (CUR && CUR.shelf && (CUR.shelf[a] || CUR.shelf[b]) && !(S.lit && S.lit.has(a) && S.lit.has(b))) continue;
      let al;
      const touchesLight = a === LIGHT || b === LIGHT;
      if (S.litLines) al = S.litLines.has(a * 100000 + b) ? 0.75 : 0;
      else if (S.lit) al = (S.lit.has(a) && S.lit.has(b)) ? (touchesLight ? 0.18 : 0.34) : 0;
      else al = touchesLight ? 0 : (flat ? 0.018 : 0.04);
      if (S.view === "lineage" && cls !== "kinship") al = 0;
      if (S.view === "chains" && cls !== "transmission") al = 0;
      if (S.view === "chains" && cls === "transmission" && !S.lit) al = 0.22;
      if (al > 0 && (S.play || S.period)) al *= Math.min(timeAlpha(a === LIGHT ? b : a), timeAlpha(b === LIGHT ? a : b));
      if (al <= 0.003) continue;
      if (touchesLight && (S.view === "map" || S.view === "globe")) continue;
      const col = LINE[cls];
      pairs.push(a, b); lc.push(col[0], col[1], col[2], al);
    }
  }
  linesCount = pairs.length / 2;
  R.setLines(new Int32Array(pairs), new Float32Array(lc));
  buildLabels();
  R.requestDraw();
  const el = $("ov");
  if (el) el.setAttribute("aria-label", t("stage.label_n", { view: t("view." + S.view), shown: fmt(shownCount), total: fmt(n) }));
}
function emphasise(set, lines) { S.lit = set; S.litLines = lines || null; restyle(); }

function buildLabels() {
  const L = [];
  const rtl = LANG === "ar", big = S.show.big ? 1.18 : 1;
  const add = (i, pri, o) => {
    if (i < 0 || i === LIGHT || !visibleNow(i)) return;
    const x = Object.assign({ i, pri, text: nameOf(i), rtl }, o || {});
    x.size = (x.size || 12.5) * big;
    L.push(x);
  };
  if (S.show.names) {
    if (S.lit) {
      const arr = sortPeople([...S.lit].filter((i) => i !== LIGHT));
      arr.slice(0, 160).forEach((i, k) => add(i, 60 - k * 0.2, { color: KIND[i] === "event" ? "#f0cf8a" : undefined }));
    } else {
      for (let i = 0; i < n; i++) {
        const k = KIND[i];
        if (k === "event" && (S.view !== "sky" || firstMs(i) !== undefined)) add(i, 20 + Math.min(deg[i], 400) / 100, { color: "#f0cf8a", size: 12 });
        else if (LIST.ten.has(i)) add(i, 30 - LIST.ten.get(i) * 0.1, { bold: true });
        else if (k === "story" && (S.view === "sky" || S.view === "stories")) add(i, S.view === "stories" ? 35 : 10, { color: "#efb3c4", size: 11.5 });
        else if (k === "place" && (S.view === "map" || S.view === "globe") && nf("geo", i)) add(i, 40, { color: "#8fe0d5", bold: true });
        else if (S.view === "chains" && CHAIN_D[i] && CHAIN_D[i] <= 2) add(i, 12 - CHAIN_D[i]);
      }
      if (S.view === "time" || S.view === "book") for (let i = 0; i < n; i++) if (KIND[i] === "person" && deg[i] > 40 && !isBack(i)) add(i, 5 + deg[i] / 200);
    }
    if (S.view === "lineage") for (let i = 0; i < n; i++) if (S.visible && S.visible[i]) add(i, 15, { size: 11.5 });
    if (S.view === "chains") for (const ch of D.chains) for (const ln of ch.links) { add(ln[0], 25, { size: 11.5 }); add(ln[1], 25, { size: 11.5 }); }
  }
  if (S.guide) for (const m of S.markers) add(m.i, m.now ? 98 : 90, { bold: true, force: !!m.now, color: "#ffe1a0" });
  if (S.focus >= 0) add(S.focus, 100, { bold: true, force: true, size: 14, color: "#fff4d6" });
  if (S.compare >= 0 && S.compare !== S.focus) add(S.compare, 99, { bold: true, force: true, size: 13.5, color: "#c9bdf5" });
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
  onLine: (pair) => openPair(pair[0], pair[1]),
  onCluster: (c) => { R.flyTo({ target: [c.X, c.Y, c.Z], dist: R.camera().dist * 0.4 }, 800); announce(t("cluster.open", { n: fmt(c.n) })); },
  clusterOn: () => S.show.cluster,
  clusterable: (i) => !(S.lit && S.lit.has(i)) && i !== S.focus && !S.markers.some((m) => m.i === i),
  onHover: (i, x, y) => {
    if (i === S.hover) { moveTip(x, y); return; }
    S.hover = i;
    const tip = $("tip");
    if (i < 0) { tip.hidden = true; R.requestDraw(); return; }
    tip.replaceChildren(h("b", null, nameOf(i)), h("span", null, kindText(i) + (contextLine(i) ? " · " + contextLine(i) : "")));
    tip.hidden = false; moveTip(x, y);
    R.requestDraw();
  },
  onFit: () => R.flyTo(viewCamera(S.view), 800),
  onPerf: (ms, fps, mode, count) => {
    const el = $("perf");
    if (el.hidden) return;
    el.textContent = t("perf.line", { ms: ms.toFixed(1), fps: fps ? Math.round(fps) : "—", n: fmt(count), mode: t("perf." + mode) });
  },
  turnRate: () => (S.view === "globe" ? 1 / R_GLOBE * 0.9 : 0.0055),
  tick: (now) => {
    let again = false;
    if (S.show.orbit && !reduced) { R.nudge(0.0016); again = true; }
    if (S.flash && now - S.flash.t0 < 900) again = true;
    return again;
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
  const fs = S.show.big ? 14 : 12;
  ctx.font = `${fs}px ${api.fontName}`;
  const line = (a, b, style, w, dash) => {
    const p = v.project(a), q = v.project(b);
    if (!p || !q) return;
    ctx.strokeStyle = style; ctx.lineWidth = w || 1; ctx.setLineDash(dash || []);
    ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]); ctx.stroke();
    ctx.setLineDash([]);
  };
  const label = (pt, s, color, align, font) => {
    const p = v.project(pt); if (!p) return;
    if (v.behindGlobe && R && S.view === "globe" && v.behindGlobe(pt[0], pt[1], pt[2])) return;
    ctx.font = font || `${fs}px ${api.fontName}`;
    ctx.fillStyle = color || "rgba(236,230,214,0.6)"; ctx.textAlign = align || "center"; ctx.textBaseline = "top";
    ctx.fillText(s, p[0], p[1]);
  };
  const ring = (pts) => {
    ctx.beginPath(); let started = false;
    for (const pt of pts) { const p = v.project(pt); if (!p) { started = false; continue; } if (!started) { ctx.moveTo(p[0], p[1]); started = true; } else ctx.lineTo(p[0], p[1]); }
    ctx.stroke();
  };
  if (S.blend === null || Math.abs(S.blend - Math.round(S.blend)) < 0.02) {
    if (S.view === "sky" && !R.isMoving()) {
      ctx.setLineDash([2, 5]); ctx.strokeStyle = "rgba(226,180,92,0.28)"; ctx.lineWidth = 1;
      ring(Array.from({ length: 481 }, (_, k) => spiral(k / 480)));
      ctx.setLineDash([]);
      if (!S.lit) {
        label(spiral(0), t("sky.ecliptic.start"), "rgba(240,207,138,0.85)");
        label(spiral(1), t("sky.ecliptic.end"), "rgba(240,207,138,0.85)");
      }
      ctx.strokeStyle = "rgba(223,143,166,0.2)";
      ring(Array.from({ length: 161 }, (_, k) => { const a = k / 160 * Math.PI * 2, x = Math.cos(a) * 700, y = Math.sin(a) * 700; return [x, y * Math.sin(0.4091), y * Math.cos(0.4091)]; }));
    } else if (S.view === "stories") {
      ctx.strokeStyle = "rgba(223,143,166,0.25)";
      ring(Array.from({ length: 161 }, (_, k) => { const a = k / 160 * Math.PI * 2; return [Math.cos(a) * 700, Math.sin(a) * 700, 0]; }));
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
      line([TIME_X(YEARS[0] - 4), 0, 0], [TIME_X(YEARS[1] + 4), 0, 0], "rgba(226,180,92,0.5)", 1.2);
      for (let y = Math.floor((YEARS[0] - 4) / 5) * 5; y <= YEARS[1] + 4; y += 5) {
        line([TIME_X(y), -14, 0], [TIME_X(y), 14, 0], "rgba(226,180,92,0.5)");
        label([TIME_X(y), -26, 0], String(y) + (y === 610 ? " " + t("time.ce") : ""));
      }
      line([TIME_X(622), -40, 0], [TIME_X(622), 560, 0], "rgba(226,180,92,0.22)", 1, [3, 5]);
      label([TIME_X(622), 580, 0], t("time.ah1"), "rgba(240,207,138,0.8)");
      label([TIME_X(600), 300, 0], t("time.lane.people"), "rgba(220,232,255,0.6)");
      label([TIME_X(600), 640, 0], t("time.axis_title"), "rgba(240,207,138,0.8)");
      if (S.period) { for (const y of S.period) line([TIME_X(y), -40, 0], [TIME_X(y), 520, 0], "rgba(255,225,160,0.6)", 1.2); }
      if (S.play) line([TIME_X(S.play.y + 1), -40, 0], [TIME_X(S.play.y + 1), 520, 0], "rgba(255,225,160,0.85)", 1.6);
    } else if (S.view === "lineage" && S.lineageOf >= 0) {
      const T = lineage(S.lineageOf);
      for (const [i, [x, y]] of T.at) for (const [p] of kin(i).parents) if (T.at.has(p)) {
        const [px, py] = T.at.get(p);
        if (py === y + 92) line([x, y, 0], [px, py, 0], "rgba(223,190,200,0.4)", 1.2);
      }
      for (const lv of T.levels.keys()) if (lv !== 0) label([-(T.width / 2) - 120, lv * 92 + 8, 0], t(lv > 0 ? "lineage.up" : "lineage.down", { n: fmt(Math.abs(lv)) }), "rgba(236,230,214,0.45)");
    }
    // each view's own labels: shelves, parts, chains, bands
    for (const L of (CUR && CUR.labels) || []) {
      const col = { shelf: "rgba(236,230,214,0.75)", shelfkind: "rgba(236,230,214,0.5)", part: "rgba(239,179,196,0.85)", title: "rgba(240,207,138,0.85)", chain: "rgba(184,230,255,0.8)", note: "rgba(236,230,214,0.5)" }[L.kind];
      const font = L.kind === "shelf" || L.kind === "title" ? `600 ${fs + 1}px ${api.fontName}` : undefined;
      label(L.p, L.text, col, L.align || (L.kind === "shelf" || L.kind === "shelfkind" ? "left" : "center"), font);
    }
  }
  ctx.restore();
}
function spiral(tt) {
  const R0 = 430, y = (1 - 2 * tt) * 0.86 * R0, rr = Math.sqrt(Math.max(R0 * R0 - y * y, 0)), a = tt * 4.5 * Math.PI * 2;
  return [rr * Math.cos(a), y, rr * Math.sin(a)];
}
function absentSet() { // people recorded as absent from the event in focus (or at the tour's stop)
  const e = S.focus >= 0 && KIND[S.focus] === "event" ? S.focus : -1;
  if (e < 0) return null;
  const out = new Set();
  for (const c of claimsOf(e)) if (pk(c) === "absent_from" && CL.o[c] === e) out.add(CL.s[c]);
  return out.size ? out : null;
}
function drawOverlayMarks(ctx, v) {
  const ring = (i, color, w, extra) => {
    if (i < 0 || i === LIGHT || v.hidden(i)) return;
    const x = v.sx[i], y = v.sy[i];
    if (x < -100) return;
    const r = v.size(v.sw[i], i) / 2 + (extra || 7);
    ctx.strokeStyle = color; ctx.lineWidth = w; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
  };
  ctx.save();
  // the whole route of a tour: a gold dashed line through its stops, in order
  if (S.guide && S.guide.T.stops.length > 1) {
    const st = S.guide.T.stops, many = st.length > 40;
    ctx.strokeStyle = "rgba(226,180,92,0.45)"; ctx.lineWidth = 1.2; ctx.setLineDash([5, 5]);
    ctx.beginPath(); let started = false;
    for (const i of st) { if (v.hidden(i) || v.sw[i] <= 1) { started = false; continue; } if (!started) { ctx.moveTo(v.sx[i], v.sy[i]); started = true; } else ctx.lineTo(v.sx[i], v.sy[i]); }
    ctx.stroke(); ctx.setLineDash([]);
    ctx.font = `600 10px ${api.fontName}`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    st.forEach((i, k) => {
      if (v.hidden(i) || v.sw[i] <= 1 || (many && k % 10 !== 9 && Math.abs(k - S.guide.k) > 1)) return;
      if (S.markers.some((m) => m.i === i)) return;
      const x = v.sx[i] + 9, y = v.sy[i] - 9;
      ctx.fillStyle = "rgba(226,180,92,0.75)"; ctx.beginPath(); ctx.arc(x, y, 7, 0, 7); ctx.fill();
      ctx.fillStyle = "#1b1407"; ctx.fillText(fmt(k + 1), x, y + 0.5);
    });
  }
  for (const m of S.markers) {
    if (v.hidden(m.i)) continue;
    const x = v.sx[m.i], y = v.sy[m.i];
    if (x < -100) continue;
    ring(m.i, m.now ? "#e2b45c" : "rgba(226,180,92,0.6)", m.now ? 2 : 1.2, m.now ? 10 : 7);
    if (m.label) {
      ctx.font = `600 11px ${api.fontName}`;
      const r = v.size(v.sw[m.i], m.i) / 2 + (m.now ? 10 : 7);
      ctx.beginPath(); ctx.arc(x + r * 0.75, y - r * 0.75, 9, 0, Math.PI * 2); ctx.fillStyle = "#e2b45c"; ctx.fill();
      ctx.fillStyle = "#1b1407"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(m.label, x + r * 0.75, y - r * 0.75 + 0.5);
    }
  }
  // recorded as absent from the event in focus: a broken coral ring with a stroke through it
  const abs = absentSet();
  if (abs) for (const i of abs) {
    if (v.hidden(i) || v.sw[i] <= 1) continue;
    const x = v.sx[i], y = v.sy[i], r = v.size(v.sw[i], i) / 2 + 6;
    ctx.strokeStyle = "rgba(224,122,95,0.95)"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(x, y, r, 0.3, 2.6); ctx.stroke();
    ctx.beginPath(); ctx.arc(x, y, r, 3.4, 5.9); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x - r * 0.75, y + r * 0.75); ctx.lineTo(x + r * 0.75, y - r * 0.75); ctx.stroke();
  }
  // marks lighting up as history plays: a brief ring
  if (S.flash) {
    const k = (performance.now() - S.flash.t0) / 900;
    if (k < 1) for (const i of S.flash.items) {
      if (v.hidden(i) || v.sw[i] <= 1) continue;
      ctx.strokeStyle = `rgba(255,230,170,${0.9 * (1 - k)})`; ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.arc(v.sx[i], v.sy[i], 5 + 16 * k, 0, 7); ctx.stroke();
    }
  }
  const tp = S.trace.path;
  if (tp) {
    ctx.strokeStyle = "rgba(255,225,160,0.9)"; ctx.lineWidth = 2; ctx.setLineDash([6, 4]);
    ctx.beginPath();
    tp.forEach(([i], k) => { const x = v.sx[i], y = v.sy[i]; if (k) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
    ctx.stroke(); ctx.setLineDash([]);
  }
  if (S.compare >= 0) ring(S.compare, "#c9bdf5", 1.6, 9);
  if (S.focus >= 0) ring(S.focus, "#fff1cc", 1.6, 9);
  if (S.hover >= 0 && S.hover !== S.focus) ring(S.hover, "rgba(255,241,204,0.6)", 1, 6);
  ctx.restore();
}

// ------------------------------------------------------------------ history: play, and the period
let playTimerH = 0;
function playHistory(on) {
  clearInterval(playTimerH); playTimerH = 0;
  if (!on) {
    S.play = null;
    $("play").setAttribute("aria-pressed", "false"); $("play").textContent = t("play.start"); $("play-year").textContent = "";
    if (S.view === "globe") R.setExtra(globeLines());
    restyle(); here(); refreshText();
    return;
  }
  S.play = { y: YEARS[0] - 1 };
  $("play").setAttribute("aria-pressed", "true"); $("play").textContent = t("play.pause");
  announce(t("play.announce", { y: fmt(YEARS[0]) }));
  const step = () => {
    S.play.y++;
    const items = [];
    for (let i = 0; i < n; i++) { const sp = yearSpan(i); if (sp && Math.floor(sp[0]) === S.play.y && visibleNow(i)) items.push(i); }
    S.flash = { t0: performance.now(), items: reduced ? [] : items.slice(0, 400) };
    $("play-year").textContent = t("play.year", { y: fmt(S.play.y) });
    if (S.view === "globe") R.setExtra(globeLines());
    restyle(); here();
    if (S.play.y >= YEARS[1]) {
      clearInterval(playTimerH); playTimerH = 0;
      $("play").setAttribute("aria-pressed", "false"); $("play").textContent = t("play.again");
      announce(t("play.end"));
    }
  };
  step();
  playTimerH = setInterval(step, reduced ? 1400 : 800);
}
function setPeriod(p) { S.period = p; restyle(); here(); refreshText(); }
