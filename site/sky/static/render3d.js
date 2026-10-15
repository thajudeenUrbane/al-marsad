/* al-Marṣad Sky: the three-dimensional renderer. Inlined before observatory.js, which
 * calls window.MarsadRenderer(api) once and uses the object it returns, exactly as it
 * does with the flat renderer (site/observatory/static/render2d.js).
 *
 * The Sky frame is a 3D layout worked out in advance (site/sky/skylayout.py); the four
 * flat frames lie in the plane z = 0 inside it, so the morph blends real 3D positions.
 * The Prophet ﷺ is drawn as the light at the centre, never as a mark (docs/01 §5 rule 1).
 * A person's brightness and warmth show their recorded generation and nothing else
 * (rule 2), and can be switched off. Every star is the same size: nothing is sized by a
 * measure (docs/04 §3). Every edge is sharp: no blur. Nothing moves unless the visitor
 * turns, zooms, flicks, changes the view or presses Play or Orbit. */
window.MarsadRenderer = function (api) {
  "use strict";
  const { S, N, L, C, FR, FRAMES, CLASSES, DASH, META, n, byId, canvas, reduceMotion, nodeA, nodeHollow, nodeLvl, linkLvl,
    visible, selectedPath, focusNode, runTrace, interrogateLinks, back, clearFocus, computeEmphasis, update,
    syncFrameControls, syncScrub, updateHere, writeHash, announce, t } = api;
  const LIGHT = META.light === undefined || META.light === null ? -1 : META.light;
  const SKY = FR.network;
  const R_RING = SKY.ring || 560;

  // ------------------------------------------------------------------ colours (defined once, in CSS)
  const css = getComputedStyle(document.documentElement);
  const cv = (name) => css.getPropertyValue(name).trim();
  const hex = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
  const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${Math.max(0, Math.min(1, a)).toFixed(3)})`;
  const COL = {
    bg: cv("--bg"), ink: cv("--ink"), muted: cv("--muted"), deco: cv("--deco"),
    person: cv("--c-person"), group: cv("--c-group"), place: cv("--c-place"), event: cv("--c-event"), story: cv("--c-story"),
  };
  const RGB = {
    ring: hex(cv("--ring")), deco: hex(cv("--deco")), light: hex(cv("--light")), limb: hex(cv("--light-limb")),
    event: hex(COL.event), story: hex(COL.story), place: hex(COL.place), group: hex(COL.group),
    gen0: hex(cv("--gen-sahabi")), gen1: hex(cv("--gen-tabii")), gen2: hex(cv("--gen-tabi-al-tabiin")),
    genNone: hex(cv("--gen-none")), genOff: hex(cv("--c-person")),
  };
  const LINECOL = {};
  for (const cls of CLASSES) LINECOL[cls] = hex(cv("--l-" + cls));
  const FONT_STACK = cv("--font-ui") || "system-ui, sans-serif";
  const FONT_AR = cv("--font-arabic") || "serif";
  const FONT = (px, wt) => `${wt || 400} ${px}px ${FONT_STACK}`;

  // a star's light by recorded generation: [colour, core alpha, halo alpha]
  const GEN = { sahabi: ["gen0", 1, 0.5], tabii: ["gen1", 0.86, 0.34], tabi_al_tabiin: ["gen2", 0.72, 0.24] };
  const opt = { generation: true, names: true, scenery: true, orbit: false };

  // ------------------------------------------------------------------ positions (3D), blended by weight
  const FP = FRAMES.map((f) => {
    const out = new Float32Array(n * 3);
    if (f === "network") out.set(SKY.pos3);
    else { const p = FR[f].pos; for (let i = 0; i < n; i++) { out[3 * i] = p[2 * i]; out[3 * i + 1] = p[2 * i + 1]; } }
    return out;
  });
  const P = new Float32Array(n * 3);
  function blend() {
    const w = S.weights;
    for (let i = 0; i < 3 * n; i++) {
      let v = 0;
      for (let f = 0; f < FRAMES.length; f++) if (w[f] > 0) v += w[f] * FP[f][i];
      P[i] = v;
    }
  }
  const firstYear = N.map((nd) => (nd.mk && nd.mk.length ? nd.mk[0][0] : null));

  // ------------------------------------------------------------------ canvas
  const ctx = canvas.getContext("2d");
  let W = 300, H = 300, DPR = 1, F = 300, inset = 0;
  let backdrop = null;

  // the far sky: a sphere of distant pinpoints with a denser band, seeded so it is the same
  // on every visit. It turns with the view but never comes closer: scenery, not records.
  function rng(seed) {
    return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let x = Math.imul(seed ^ (seed >>> 15), 1 | seed); x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x; return ((x ^ (x >>> 14)) >>> 0) / 4294967296; };
  }
  const FAR = (() => {
    const r = rng(42), out = [];
    const g = () => (r() + r() + r() + r() - 2) / 2;
    const tints = [hex(cv("--far-1")), hex(cv("--far-2")), hex(cv("--far-3"))];
    for (let k = 0; k < 2400; k++) {
      let x, y, z;
      if (k < 1400) { const a = r() * Math.PI * 2, lat = g() * 0.22; x = Math.cos(a) * Math.cos(lat); y = Math.sin(lat); z = Math.sin(a) * Math.cos(lat); }
      else { const u = r() * 2 - 1, a = r() * Math.PI * 2, s = Math.sqrt(1 - u * u); x = s * Math.cos(a); y = u; z = s * Math.sin(a); }
      const tl = 0.9, y2 = y * Math.cos(tl) - z * Math.sin(tl), z2 = y * Math.sin(tl) + z * Math.cos(tl);
      const m = r();
      out.push([x, y2, z2, 0.08 + m * m * m * 0.5, m > 0.985 ? 2 : 1, tints[Math.floor(r() * 3)]]);
    }
    return out;
  })();

  function stageInset() {
    const pn = byId("obs-panel");
    if (!pn || pn.dataset.open !== "true" || getComputedStyle(pn).position !== "fixed") return 0;
    const vis = window.innerHeight - pn.getBoundingClientRect().height;
    const offset = canvas.getBoundingClientRect().top - byId("obs-stage-wrap").getBoundingClientRect().top;
    return Math.max(0, Math.min(H * 0.6, offset + H - vis));
  }
  function resize() {
    const r = canvas.getBoundingClientRect();
    W = Math.max(200, r.width); H = Math.max(200, r.height);
    DPR = Math.min(2.5, window.devicePixelRatio || 1);
    canvas.width = Math.round(W * DPR); canvas.height = Math.round(H * DPR);
    F = 0.9 * Math.min(W, H);
    backdrop = document.createElement("canvas");
    backdrop.width = canvas.width; backdrop.height = canvas.height;
    const b = backdrop.getContext("2d"), w = backdrop.width, h = backdrop.height;
    const gr = b.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, Math.hypot(w, h) * 0.6);
    gr.addColorStop(0, cv("--sky-1")); gr.addColorStop(0.55, cv("--sky-2")); gr.addColorStop(1, cv("--sky-3"));
    b.fillStyle = gr; b.fillRect(0, 0, w, h);
    inset = stageInset();
    S.baseDist = fitAll().dist;
    if (S.camMode !== "free") Object.assign(cam, S.camMode === "focus" ? fitEgo() : fitAll());
    requestDraw();
  }

  // ------------------------------------------------------------------ camera: orbits a target point
  const VIEWS = { face: [0, 0], angle: [0.6, -0.45], edge: [0, -1.5], below: [0.4, 1.0] };
  const cam = { x: 0, y: 0, z: 0, yaw: VIEWS.angle[0], pitch: VIEWS.angle[1], dist: 1800 };
  let cy_ = 1, sy_ = 0, cp_ = 1, sp_ = 0;
  function trig(c) { cy_ = Math.cos(c.yaw); sy_ = Math.sin(c.yaw); cp_ = Math.cos(c.pitch); sp_ = Math.sin(c.pitch); }
  function unrotate(x, y, z) {
    const y1 = cp_ * y + sp_ * z, z1 = -sp_ * y + cp_ * z;
    return [cy_ * x - sy_ * z1, y1, sy_ * x + cy_ * z1];
  }
  const clampPitch = (p) => Math.max(-1.52, Math.min(1.52, p));
  const clampDist = (d) => Math.max(40, Math.min(30000, d));

  // the camera that frames these points from the given direction, with room for the panel
  function fitPoints(pts, ori, pad) {
    if (!pts.length) pts = [[0, 0, 0]];
    let x0 = Infinity, y0 = Infinity, z0 = Infinity, x1 = -Infinity, y1 = -Infinity, z1 = -Infinity;
    for (const [x, y, z] of pts) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); z0 = Math.min(z0, z); z1 = Math.max(z1, z); }
    const c = { x: (x0 + x1) / 2, y: (y0 + y1) / 2, z: (z0 + z1) / 2, yaw: ori.yaw, pitch: ori.pitch };
    trig(c);
    const p = pad === undefined ? 34 : pad, hw = Math.max(40, W / 2 - p), hh = Math.max(40, (H - inset) / 2 - p);
    let need = 60;
    for (const [x, y, z] of pts) {
      const vx = x - c.x, vy = y - c.y, vz = z - c.z;
      const xr = cy_ * vx + sy_ * vz, zr = -sy_ * vx + cy_ * vz, yr = cp_ * vy - sp_ * zr, zz = sp_ * vy + cp_ * zr;
      need = Math.max(need, (Math.abs(xr) * F) / hw - zz, (Math.abs(yr) * F) / hh - zz, -zz + 60);
    }
    c.dist = clampDist(need);
    trig(cam);
    return c;
  }
  function framePoints(indices, withDeco) {
    const pts = [];
    for (const i of indices) if (visible(i)) pts.push([P[3 * i], P[3 * i + 1], P[3 * i + 2]]);
    if (withDeco) {
      FRAMES.forEach((f, fi) => {
        if (S.weights[fi] < 0.25) return;
        if (f === "network") { for (let k = 0; k < 8; k++) { const a = (k / 8) * Math.PI * 2; pts.push([Math.cos(a) * R_RING, Math.sin(a) * R_RING, 0]); } return; }
        for (const d of FR[f].deco) {
          if (d.t === "text") pts.push([d.x, d.y, 0]);
          else if (d.t === "line") { pts.push([d.x1, d.y1, 0], [d.x2, d.y2, 0]); }
          else if (d.t === "circle") { pts.push([d.x - d.r, d.y - d.r, 0], [d.x + d.r, d.y + d.r, 0]); }
        }
      });
    }
    return pts;
  }
  const allIdx = Array.from({ length: n }, (_, i) => i);
  const fitAll = (ori) => fitPoints(framePoints(allIdx, true), ori || cam);
  function fitEgo(ori) {
    const e = api.emph();
    if (e && e.size) {
      const f = fitPoints(framePoints(e), ori || cam, 70);
      f.dist = Math.max(f.dist, (S.baseDist || f.dist) / 7);
      return f;
    }
    return fitAll(ori);
  }

  // ------------------------------------------------------------------ projection
  const SX = new Float32Array(n), SY = new Float32Array(n), SD = new Float32Array(n), SS = new Float32Array(n);
  function project() {
    trig(cam);
    const cx = W / 2, cyy = (H - inset) / 2;
    for (let i = 0; i < n; i++) {
      const vx = P[3 * i] - cam.x, vy = P[3 * i + 1] - cam.y, vz = P[3 * i + 2] - cam.z;
      const x1 = cy_ * vx + sy_ * vz, z1 = -sy_ * vx + cy_ * vz, y2 = cp_ * vy - sp_ * z1, z2 = sp_ * vy + cp_ * z1;
      const d = z2 + cam.dist;
      SD[i] = d;
      if (d < 20) { SS[i] = 0; continue; }
      const s = F / d;
      SS[i] = s; SX[i] = cx + x1 * s; SY[i] = cyy + y2 * s;
    }
  }
  function proj(x, y, z) {
    const vx = x - cam.x, vy = y - cam.y, vz = z - cam.z;
    const x1 = cy_ * vx + sy_ * vz, z1 = -sy_ * vx + cy_ * vz, y2 = cp_ * vy - sp_ * z1, z2 = sp_ * vy + cp_ * z1, d = z2 + cam.dist;
    if (d < 20) return null;
    const s = F / d;
    return [W / 2 + x1 * s, (H - inset) / 2 + y2 * s, d, s];
  }
  // 1 at the fitted distance, larger nearer; marks grow gently as you come closer
  const mag = (i) => (SS[i] * (S.baseDist || cam.dist)) / F;
  const depthA = (d) => Math.max(0.4, Math.min(1, 1.15 - (0.5 * (d - cam.dist)) / R_RING));
  const radius = (i) => Math.max(1.6, Math.min(14, 2.7 * Math.sqrt(mag(i))));
  const lightCore = () => Math.max(6, Math.min(60, 10.5 * Math.pow(Math.max(0.05, mag(LIGHT)), 0.55)));

  // ------------------------------------------------------------------ animation
  let anim = null, flight = null, drawQueued = false, last = 0;
  const spin = { yaw: 0, pitch: 0 };
  const ripples = [];
  let dragging = false, playing = false, playYear = 0;
  function requestDraw() { if (!drawQueued) { drawQueued = true; requestAnimationFrame(frame); } }
  const ease = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
  const wrapAngle = (a) => { a %= Math.PI * 2; if (a > Math.PI) a -= Math.PI * 2; if (a < -Math.PI) a += Math.PI * 2; return a; };
  function lerpCam(a, b, e) {
    return { x: a.x + (b.x - a.x) * e, y: a.y + (b.y - a.y) * e, z: a.z + (b.z - a.z) * e,
      yaw: a.yaw + wrapAngle(b.yaw - a.yaw) * e, pitch: a.pitch + (b.pitch - a.pitch) * e,
      dist: Math.exp(Math.log(a.dist) + (Math.log(b.dist) - Math.log(a.dist)) * e) };
  }
  // flat frames are read face on; the Sky is first seen at an angle
  function orientationFor(w) {
    const d = w.indexOf(Math.max(...w));
    if (FRAMES[d] !== "network" && w[d] > 0.985) return { yaw: 0, pitch: 0 };
    if (FRAMES[d] === "network" && Math.abs(wrapAngle(cam.yaw)) < 0.05 && Math.abs(cam.pitch) < 0.05) return { yaw: VIEWS.angle[0], pitch: VIEWS.angle[1] };
    return { yaw: cam.yaw, pitch: cam.pitch };
  }
  function animateTo(weights, camMode) {
    if (camMode) S.camMode = camMode;
    const wFrom = S.weights.slice(), wTo = weights ? weights.slice() : S.weights.slice();
    const ori = orientationFor(wTo);
    flight = null; spin.yaw = spin.pitch = 0;
    if (reduceMotion) {
      S.weights = wTo; blend(); cam.yaw = ori.yaw; cam.pitch = ori.pitch; S.baseDist = fitAll().dist;
      if (S.camMode === "fit") Object.assign(cam, fitAll()); else if (S.camMode === "focus") Object.assign(cam, fitEgo());
      syncFrameControls(); requestDraw(); return;
    }
    anim = { t0: performance.now(), dur: 750, wFrom, wTo, camFrom: Object.assign({}, cam), ori };
    requestDraw();
  }
  function flyTo(to, dur) {
    if (reduceMotion) { Object.assign(cam, to); requestDraw(); return; }
    anim = null; spin.yaw = spin.pitch = 0;
    flight = { t0: performance.now(), dur: dur || 800, from: Object.assign({}, cam), to: Object.assign({}, cam, to) };
    requestDraw();
  }
  const moving = () => !!(anim || flight || dragging || playing || ripples.length || Math.abs(spin.yaw) > 1e-4 || Math.abs(spin.pitch) > 1e-4 || opt.orbit);
  function frame(now) {
    drawQueued = false;
    const dt = last ? Math.min(50, now - last) / 16.67 : 1;
    last = now;
    if (anim) {
      const p = Math.min(1, (now - anim.t0) / anim.dur), e = ease(p);
      S.weights = anim.wFrom.map((w, f) => w + (anim.wTo[f] - w) * e);
      blend();
      const ori = { yaw: anim.camFrom.yaw + wrapAngle(anim.ori.yaw - anim.camFrom.yaw) * e, pitch: anim.camFrom.pitch + (anim.ori.pitch - anim.camFrom.pitch) * e };
      const target = S.camMode === "fit" ? fitAll(ori) : S.camMode === "focus" ? fitEgo(ori) : Object.assign({}, cam, ori);
      Object.assign(cam, lerpCam(anim.camFrom, target, e), ori);
      if (p >= 1) { anim = null; S.weights = S.weights.map((w) => Math.round(w * 1000) / 1000); S.baseDist = fitAll().dist; syncFrameControls(); updateHere(); }
    } else if (flight) {
      const p = Math.min(1, (now - flight.t0) / flight.dur);
      Object.assign(cam, lerpCam(flight.from, flight.to, ease(p)));
      if (p >= 1) { flight = null; updateHere(); writeHash(); }
    } else if (!dragging) {
      cam.yaw += spin.yaw * dt; cam.pitch = clampPitch(cam.pitch + spin.pitch * dt);
      spin.yaw *= Math.pow(0.94, dt); spin.pitch *= Math.pow(0.94, dt);
      if (opt.orbit && Math.abs(spin.yaw) < 0.002) cam.yaw += 0.0018 * dt;
    }
    if (playing) stepPlay(dt);
    draw(now);
    if (moving()) requestDraw();
  }

  // ------------------------------------------------------------------ drawing
  function drawBackdrop() {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(backdrop, 0, 0);
    if (!opt.scenery) return;
    const f = Math.min(canvas.width, canvas.height) * 0.9, cx = canvas.width / 2, cy = canvas.height / 2;
    for (const [x, y, z, a, s, c] of FAR) {
      const x1 = cy_ * x + sy_ * z, z1 = -sy_ * x + cy_ * z, y2 = cp_ * y - sp_ * z1, z2 = sp_ * y + cp_ * z1;
      if (z2 < 0.05) continue;
      const px = Math.round(cx + (x1 / z2) * f), py = Math.round(cy + (y2 / z2) * f);
      if (px < 0 || py < 0 || px >= canvas.width || py >= canvas.height) continue;
      ctx.fillStyle = rgba(c, a); ctx.fillRect(px, py, s, s);
    }
  }
  function drawRing() {
    const w = S.weights[0];
    if (w < 0.02) return;
    ctx.lineWidth = 1;
    let prev = null;
    for (let k = 0; k <= 128; k++) {
      const a = (k / 128) * Math.PI * 2, p = proj(Math.cos(a) * R_RING, Math.sin(a) * R_RING, 0);
      if (p && prev) {
        ctx.strokeStyle = rgba(RGB.story, 0.22 * w * depthA(p[2]));
        ctx.beginPath(); ctx.moveTo(prev[0], prev[1]); ctx.lineTo(p[0], p[1]); ctx.stroke();
      }
      prev = p;
    }
  }
  // the flat frames' axes, grids, titles and shelves, drawn in their plane
  function drawDeco() {
    FRAMES.forEach((f, fi) => {
      const w = S.weights[fi];
      if (w < 0.02 || f === "network") return;
      for (const d of FR[f].deco) {
        const a = w * (d.o === undefined ? 1 : d.o);
        if (d.t === "text") {
          const p = proj(d.x, d.y, 0); if (!p) continue;
          const k = Math.max(0.55, Math.min(1.2, (p[3] * (S.baseDist || cam.dist)) / F));
          ctx.font = FONT(Math.max(7, (d.z || 11) * k), d.w || 400);
          ctx.fillStyle = rgba(RGB.deco, a);
          ctx.textAlign = d.a === "middle" ? "center" : d.a === "end" ? "right" : "left";
          ctx.textBaseline = "alphabetic";
          ctx.fillText(d.s, p[0], p[1] + (d.dy || 0) * k);
        } else if (d.t === "line") {
          const p = proj(d.x1, d.y1, 0), q = proj(d.x2, d.y2, 0); if (!p || !q) continue;
          ctx.strokeStyle = rgba(RGB.deco, a * 0.8); ctx.lineWidth = 1; ctx.setLineDash([]);
          ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]); ctx.stroke();
        } else if (d.t === "circle") {
          ctx.strokeStyle = rgba(RGB.deco, a * 0.8); ctx.lineWidth = 1; ctx.setLineDash([]);
          ctx.beginPath();
          for (let k = 0; k <= 64; k++) {
            const an = (k / 64) * Math.PI * 2, p = proj(d.x + Math.cos(an) * d.r, d.y + Math.sin(an) * d.r, 0);
            if (!p) continue;
            if (k === 0) ctx.moveTo(p[0], p[1]); else ctx.lineTo(p[0], p[1]);
          }
          ctx.stroke();
        }
      }
    });
    ctx.textAlign = "left";
  }
  function drawTimeMarks() {
    const w = S.weights[1];
    if (w < 0.02) return;
    const marks = FR.time.marks || {}, fp = FR.time.pos;
    for (const key in marks) {
      const i = +key;
      if (!nodeA[i]) continue;
      const y = fp[2 * i + 1];
      ctx.strokeStyle = rgba(hex(COL[N[i].k] || COL.ink), w * 0.6 * nodeA[i]); ctx.lineWidth = 2.5;
      for (const m of marks[key]) {
        const p = proj(m[0], y, 0), q = proj(m[1], y, 0); if (!p || !q) continue;
        ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(Math.max(p[0] + 1.5, q[0]), q[1]); ctx.stroke();
      }
    }
  }
  const LV_A = [0, 0.05, 0.13, 0.75, 1], LV_W = [0, 0.6, 0.7, 1.4, 2.2];
  function drawLinks() {
    for (let lv = 1; lv <= 4; lv++) {
      for (let li = 0; li < L.length; li++) {
        if (linkLvl[li] !== lv) continue;
        const l = L[li];
        if (!SS[l.a] || !SS[l.b]) continue;
        const x1 = SX[l.a], y1 = SY[l.a], x2 = SX[l.b], y2 = SY[l.b];
        ctx.strokeStyle = rgba(LINECOL[l.c], LV_A[lv] * (depthA(SD[l.a]) + depthA(SD[l.b])) / 2);
        ctx.lineWidth = LV_W[lv] * (l.c === "transmission" ? 1.5 : 1);
        ctx.setLineDash(lv >= 3 ? DASH[l.c] : []);
        ctx.beginPath();
        if (l.c === "kinship" && lv >= 3) {
          const dx = x2 - x1, dy = y2 - y1, d = Math.hypot(dx, dy) || 1, ox = (-dy / d) * 1.6, oy = (dx / d) * 1.6;
          ctx.moveTo(x1 + ox, y1 + oy); ctx.lineTo(x2 + ox, y2 + oy); ctx.moveTo(x1 - ox, y1 - oy); ctx.lineTo(x2 - ox, y2 - oy);
        } else { ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); }
        ctx.stroke();
      }
    }
    ctx.setLineDash([]);
    // direction marks on transmission links (narrator to narrator)
    for (let li = 0; li < L.length; li++) {
      if (L[li].c !== "transmission" || !linkLvl[li]) continue;
      const c = C[L[li].cl[0]];
      if (!SS[c.s] || !SS[c.o]) continue;
      const x1 = SX[c.s], y1 = SY[c.s], x2 = SX[c.o], y2 = SY[c.o], d = Math.hypot(x2 - x1, y2 - y1);
      if (d < 18) continue;
      const ux = (x2 - x1) / d, uy = (y2 - y1) / d, mx = x1 + (x2 - x1) * 0.6, my = y1 + (y2 - y1) * 0.6;
      ctx.fillStyle = rgba(LINECOL.transmission, linkLvl[li] >= 3 ? 1 : 0.5);
      ctx.beginPath(); ctx.moveTo(mx + ux * 6, my + uy * 6); ctx.lineTo(mx - uy * 4, my + ux * 4); ctx.lineTo(mx + uy * 4, my - ux * 4); ctx.closePath(); ctx.fill();
    }
  }
  function spike(x, y, a, len, w, col, alpha) {
    const ca = Math.cos(a), sa = Math.sin(a), px = -sa * w, py = ca * w;
    for (const s of [1, -1]) {
      const g = ctx.createLinearGradient(x, y, x + ca * len * s, y + sa * len * s);
      g.addColorStop(0, rgba(col, alpha)); g.addColorStop(1, rgba(col, 0));
      ctx.beginPath(); ctx.moveTo(x + px, y + py); ctx.lineTo(x + ca * len * s, y + sa * len * s); ctx.lineTo(x - px, y - py);
      ctx.closePath(); ctx.fillStyle = g; ctx.fill();
    }
  }
  // the source of light: a hard-edged core, a short corona that is gone within a few
  // radii, diffraction spikes and two hairline rings. Sharp, never smeared.
  function drawLight(x, y, core, a) {
    ctx.globalAlpha = a;
    const g = ctx.createRadialGradient(x, y, core * 0.9, x, y, core * 3.6);
    g.addColorStop(0, rgba(RGB.light, 0.55)); g.addColorStop(0.35, rgba(RGB.limb, 0.16)); g.addColorStop(1, rgba(RGB.limb, 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, core * 3.6, 0, Math.PI * 2); ctx.fill();
    for (let k = 0; k < 4; k++) spike(x, y, (k * Math.PI) / 2, core * 9.5, core * 0.13, RGB.light, 0.9);
    for (let k = 0; k < 4; k++) spike(x, y, (k * Math.PI) / 2 + Math.PI / 4, core * 4.6, core * 0.07, RGB.light, 0.6);
    ctx.lineWidth = 1;
    ctx.strokeStyle = rgba(RGB.limb, 0.28); ctx.beginPath(); ctx.arc(x, y, core * 2.25, 0, Math.PI * 2); ctx.stroke();
    ctx.strokeStyle = rgba(RGB.gen0, 0.14); ctx.beginPath(); ctx.arc(x, y, core * 3.1, 0, Math.PI * 2); ctx.stroke();
    const c = ctx.createRadialGradient(x - core * 0.15, y - core * 0.15, 0, x, y, core);
    c.addColorStop(0, "#ffffff"); c.addColorStop(0.7, rgba(RGB.light, 1)); c.addColorStop(1, rgba(RGB.limb, 1));
    ctx.fillStyle = c; ctx.beginPath(); ctx.arc(x, y, core, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = rgba(RGB.limb, 0.95); ctx.stroke();
    ctx.globalAlpha = 1;
  }
  function starLight(i) {
    if (!opt.generation) return [RGB.genOff, 1, 0.38];
    const g = GEN[N[i].tbk];
    return g ? [RGB[g[0]], g[1], g[2]] : [RGB.genNone, 0.8, 0];
  }
  function drawMark(i, x, y, r, a, hollow) {
    const k = N[i].k;
    ctx.globalAlpha = a;
    if (k === "person") {
      const [col, core, halo] = starLight(i);
      if (hollow) { ctx.strokeStyle = rgba(col, core); ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke(); ctx.globalAlpha = 1; return; }
      if (halo > 0) {
        const h = ctx.createRadialGradient(x, y, r * 0.8, x, y, r * 2.7);
        h.addColorStop(0, rgba(col, halo)); h.addColorStop(1, rgba(col, 0));
        ctx.fillStyle = h; ctx.beginPath(); ctx.arc(x, y, r * 2.7, 0, Math.PI * 2); ctx.fill();
      }
      const c = ctx.createRadialGradient(x, y, 0, x, y, r);
      c.addColorStop(0, rgba([255, 255, 255], core)); c.addColorStop(0.5, rgba([255, 255, 255], core)); c.addColorStop(1, rgba(col, core));
      ctx.fillStyle = c; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
    } else if (k === "event") { // a small planet, lit on the side that faces the light
      if (hollow) { ctx.strokeStyle = rgba(RGB.event, 1); ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(x, y, r * 1.1, 0, Math.PI * 2); ctx.stroke(); ctx.globalAlpha = 1; return; }
      const lx0 = LIGHT >= 0 && SS[LIGHT] ? SX[LIGHT] : W / 2, ly0 = LIGHT >= 0 && SS[LIGHT] ? SY[LIGHT] : H / 2;
      const d = Math.hypot(x - lx0, y - ly0) || 1, lx = (lx0 - x) / d, ly = (ly0 - y) / d, rr = r * 1.15;
      const g = ctx.createRadialGradient(x + lx * rr * 0.5, y + ly * rr * 0.5, 0, x, y, rr);
      g.addColorStop(0, cv("--event-lit")); g.addColorStop(0.6, COL.event); g.addColorStop(1, cv("--event-dark"));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, rr, 0, Math.PI * 2); ctx.fill();
      ctx.lineWidth = 0.8; ctx.strokeStyle = rgba(RGB.event, 0.9); ctx.stroke();
    } else if (k === "story") {
      ctx.beginPath(); ctx.moveTo(x, y - r * 1.5); ctx.lineTo(x + r * 1.05, y); ctx.lineTo(x, y + r * 1.5); ctx.lineTo(x - r * 1.05, y); ctx.closePath();
      if (hollow) { ctx.strokeStyle = COL.story; ctx.lineWidth = 1.2; ctx.stroke(); }
      else { ctx.fillStyle = COL.story; ctx.fill(); ctx.fillStyle = "rgba(255,255,255,0.75)"; ctx.beginPath(); ctx.arc(x, y - r * 0.2, r * 0.32, 0, Math.PI * 2); ctx.fill(); }
    } else if (k === "place") {
      ctx.strokeStyle = COL.place; ctx.lineWidth = 1.3; const s = r * 1.3;
      ctx.beginPath(); ctx.moveTo(x - s, y); ctx.lineTo(x + s, y); ctx.moveTo(x, y - s); ctx.lineTo(x, y + s); ctx.stroke();
      ctx.beginPath(); ctx.arc(x, y, s * 0.55, 0, Math.PI * 2); ctx.stroke();
    } else { // a group: a tight cluster of three
      const s = r * 0.95;
      for (const [dx, dy] of [[0, -s], [s * 0.9, s * 0.55], [-s * 0.9, s * 0.55]]) {
        ctx.beginPath(); ctx.arc(x + dx, y + dy, Math.max(0.9, r * 0.42), 0, Math.PI * 2);
        if (hollow) { ctx.strokeStyle = COL.group; ctx.lineWidth = 1; ctx.stroke(); } else { ctx.fillStyle = COL.group; ctx.fill(); }
      }
    }
    ctx.globalAlpha = 1;
  }
  function ring(x, y, r, col, a, width, dash) {
    ctx.setLineDash(dash || []); ctx.strokeStyle = rgba(col, a); ctx.lineWidth = width || 1.5;
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
  }
  let order = [];
  function drawMarks(now) {
    order = [];
    for (let i = 0; i < n; i++) if (nodeA[i] && SS[i]) order.push(i);
    order.sort((a, b) => SD[b] - SD[a]); // far first: near stars pass in front
    for (const i of order) {
      const x = SX[i], y = SY[i];
      if (x < -80 || y < -80 || x > W + 80 || y > H + 80) continue;
      const a = nodeA[i] * depthA(SD[i]);
      if (i === LIGHT) {
        const core = lightCore();
        drawLight(x, y, core, Math.max(0.35, a));
        if (i === S.focus) ring(x, y, core * 2.6, RGB.ring, 1, 2);
        else if (i === S.hover) ring(x, y, core * 2.6, RGB.ring, 0.8, 1);
        continue;
      }
      const r = radius(i);
      drawMark(i, x, y, r, a, nodeHollow[i]);
      if (nodeLvl[i] === 2 && i !== S.focus) ring(x, y, r + 5, RGB.ring, 0.9, 1.6, [3, 2]);
      if (i === S.focus) {
        ring(x, y, r + 5, RGB.ring, 1, 2);
        if (N[i].k === "person") { const [col] = starLight(i); spike(x, y, 0, r * 6, Math.max(0.6, r * 0.16), col, 0.85); spike(x, y, Math.PI / 2, r * 6, Math.max(0.6, r * 0.16), col, 0.85); }
      }
      if (S.trace.a === i && S.picking) ring(x, y, r + 8, RGB.ring, 0.9, 1.4, [2, 3]);
      if (i === S.hover) ring(x, y, r + 3, RGB.ring, 0.8, 1);
      if (playing && firstYear[i] !== null) { // lit just now, as the year passes its first dated record
        const age = S.scrub.y1 + 1 - firstYear[i];
        if (age >= 0 && age < 2.5) ring(x, y, r + 3 + age * 7, RGB.light, 1 - age / 2.5, 1.2);
      }
    }
    for (let k = ripples.length - 1; k >= 0; k--) { // the answer to a touch
      const rp = ripples[k], p = (now - rp.t0) / 650;
      if (p >= 1 || !SS[rp.i]) { ripples.splice(k, 1); continue; }
      const r0 = rp.i === LIGHT ? lightCore() : radius(rp.i);
      ring(SX[rp.i], SY[rp.i], r0 + 4 + p * 34, RGB.ring, 1 - p, 1.5);
    }
  }

  // ------------------------------------------------------------------ names
  function labelCandidates() {
    const out = [];
    const wd = S.weights;
    const zoomRel = (S.baseDist || cam.dist) / cam.dist;
    const disc = S.lens === "discover";
    const path = selectedPath();
    const e = api.emph();
    const push = (i, pri) => { if (i >= 0 && nodeA[i] > 0.5 && SS[i]) out.push([pri, i, 1]); };
    const pushStructural = (i, pri) => { if (i >= 0 && nodeA[i] > 0 && SS[i]) out.push([pri, i, nodeA[i] > 0.5 ? 1 : 0.6]); };
    if (S.hover >= 0) push(S.hover, 9);
    push(S.focus, 8);
    if (path) { push(S.trace.a, 7); push(S.trace.b, 7); for (const hop of path.hops) push(hop.to, 6); }
    if (e) {
      let k = 0;
      for (const i of e) { if (disc && N[i].k !== "story" && k++ > 10) continue; push(i, disc && N[i].k === "story" ? 5 : 4); }
    }
    if (!opt.names) return out;
    for (const i of order.slice().reverse()) {
      if (!nodeA[i] || i === LIGHT) continue;
      const kind = N[i].k;
      if (wd[2] > 0.5 && kind === "place" && FR.geo.region[i] === "map") pushStructural(i, 6.5);
      if (wd[4] > 0.5 && FR.isnad.region[i] === "chain") pushStructural(i, 6.5);
      if (nodeA[i] < 0.5) continue;
      if (wd[3] > 0.5 && kind === "story") push(i, disc ? 3 : 2);
      if (wd[1] > 0.5 && kind === "event" && FR.time.region[i] === "axis") push(i, 2);
      if (zoomRel > 1.9 && (!disc || kind === "story" || kind === "place" || kind === "event")) push(i, 1);
    }
    out.sort((p, q) => q[0] - p[0] || SD[p[1]] - SD[q[1]]);
    return out;
  }
  function drawLabels() {
    const placed = [];
    // the light is named in both scripts; nothing else is written over it
    if (LIGHT >= 0 && nodeA[LIGHT] && SS[LIGHT] && S.weights[0] > 0.3) {
      const core = lightCore(), x = SX[LIGHT], y = SY[LIGHT];
      ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
      ctx.font = `400 ${Math.round(16 + core * 0.3)}px ${FONT_AR}`;
      ctx.lineWidth = 4; ctx.strokeStyle = COL.bg; ctx.lineJoin = "round";
      const ar = t("sky.light_arabic"), en = N[LIGHT].n;
      ctx.strokeText(ar, x, y - core * 2.4 - 6); ctx.fillStyle = rgba(RGB.light, 1); ctx.fillText(ar, x, y - core * 2.4 - 6);
      ctx.font = FONT(13, 600);
      ctx.strokeText(en, x, y + core * 2.4 + 16); ctx.fillText(en, x, y + core * 2.4 + 16);
      const wa = ctx.measureText(en).width;
      placed.push([x - 60, y - core * 2.4 - 34, x + 60, y - core * 2.4 - 2], [x - wa / 2 - 4, y + core * 2.4 + 2, x + wa / 2 + 4, y + core * 2.4 + 22]);
      ctx.textAlign = "left";
    }
    const max = Math.min(moving() ? 24 : S.lens === "discover" ? 40 : 140, Math.max(10, Math.round((W * H) / 6000)));
    const seen = new Set();
    let count = 0;
    ctx.textBaseline = "middle";
    for (const [pri, i, alpha] of labelCandidates()) {
      if (seen.has(i) || i === LIGHT) continue;
      seen.add(i);
      if (count >= max && pri < 6) break;
      const font = FONT(pri >= 8 ? 13 : 12, pri >= 7 ? 600 : 400);
      ctx.font = font;
      const text = N[i].n, w = ctx.measureText(text).width, r = radius(i);
      const nx = SX[i], y = SY[i];
      const flip = nx + r + 6 + w > W - 4 && nx - r - 6 - w > 4;
      const x = flip ? nx - r - 6 - w : nx + r + 6;
      if (x > W || y < 0 || y > H || x + w < 0) continue;
      const box = [x - 2, y - 8, x + w + 2, y + 8];
      if (pri < 7 && placed.some((b) => b[0] < box[2] && b[2] > box[0] && b[1] < box[3] && b[3] > box[1])) continue;
      placed.push(box);
      ctx.globalAlpha = alpha * Math.max(0.55, depthA(SD[i]));
      ctx.lineWidth = 3.5; ctx.strokeStyle = COL.bg; ctx.lineJoin = "round"; ctx.strokeText(text, x, y);
      ctx.fillStyle = pri >= 4 ? COL.ink : COL.muted; ctx.fillText(text, x, y);
      count++;
    }
    ctx.globalAlpha = 1;
  }

  function draw(now) {
    project();
    drawBackdrop();
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.globalAlpha = 1;
    drawRing();
    drawDeco();
    drawTimeMarks();
    drawLinks();
    drawMarks(now || performance.now());
    drawLabels();
  }

  // ------------------------------------------------------------------ hit testing (fingers get a larger target)
  function nodeAt(x, y, touch) {
    let best = -1, bd = Infinity;
    const lim = touch ? 22 : 12;
    for (let i = 0; i < n; i++) {
      if (!nodeA[i] || !SS[i]) continue;
      const d = Math.hypot(SX[i] - x, SY[i] - y) - (i === LIGHT ? lightCore() : radius(i));
      if (d > lim) continue;
      const score = d - nodeA[i] * 4 + SD[i] * 0.0005; // brighter and nearer win a tie
      if (score < bd) { bd = score; best = i; }
    }
    return best;
  }
  function linkAt(x, y) {
    let best = -1, bd = 36;
    for (let li = 0; li < L.length; li++) {
      if (linkLvl[li] < 2) continue;
      const l = L[li];
      if (!SS[l.a] || !SS[l.b]) continue;
      const x1 = SX[l.a], y1 = SY[l.a], x2 = SX[l.b], y2 = SY[l.b];
      const dx = x2 - x1, dy = y2 - y1, len2 = dx * dx + dy * dy || 1;
      const u = Math.max(0, Math.min(1, ((x - x1) * dx + (y - y1) * dy) / len2));
      const ex = x1 + u * dx - x, ey = y1 + u * dy - y, d = ex * ex + ey * ey;
      if (d < bd) { bd = d; best = li; }
    }
    return best;
  }
  function nearestToCentre() {
    let best = -1, bd = Infinity;
    for (let i = 0; i < n; i++) {
      if (!nodeA[i] || nodeA[i] < 0.5 || !SS[i]) continue;
      const d = Math.hypot(SX[i] - W / 2, SY[i] - (H - inset) / 2);
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  }

  // ------------------------------------------------------------------ input: drag turns the sky; right-drag,
  // Shift-drag or two fingers move it; the wheel and a pinch zoom; a tap touches a mark
  const pointers = new Map();
  let gesture = null, lastMove = 0;
  function pan(dx, dy) {
    trig(cam);
    const s = F / cam.dist, r = unrotate(1, 0, 0), u = unrotate(0, 1, 0);
    cam.x -= (r[0] * dx + u[0] * dy) / s; cam.y -= (r[1] * dx + u[1] * dy) / s; cam.z -= (r[2] * dx + u[2] * dy) / s;
  }
  const freeCam = () => { anim = null; flight = null; S.camMode = "free"; };
  canvas.addEventListener("contextmenu", (e) => e.preventDefault());
  // a finger tap opens the panel under the finger; cancelling the touch end stops the
  // browser's follow-up click from landing on a button in it
  canvas.addEventListener("touchend", (e) => { if (e.cancelable) e.preventDefault(); }, { passive: false });
  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.offsetX, y: e.offsetY });
    spin.yaw = spin.pitch = 0;
    if (pointers.size === 1) gesture = { type: e.button === 2 || e.shiftKey ? "pan" : "turn", x0: e.offsetX, y0: e.offsetY, moved: false, touch: e.pointerType !== "mouse" };
    else if (pointers.size === 2) {
      const [p, q] = [...pointers.values()];
      gesture = { type: "pinch", d0: Math.hypot(p.x - q.x, p.y - q.y) || 1, dist0: cam.dist, m: { x: (p.x + q.x) / 2, y: (p.y + q.y) / 2 }, moved: true };
    }
  });
  canvas.addEventListener("pointermove", (e) => {
    const prev = pointers.get(e.pointerId);
    if (prev) pointers.set(e.pointerId, { x: e.offsetX, y: e.offsetY });
    if (gesture && (gesture.type === "turn" || gesture.type === "pan") && pointers.size === 1 && prev) {
      const dx = e.offsetX - prev.x, dy = e.offsetY - prev.y;
      if (!gesture.moved && Math.hypot(e.offsetX - gesture.x0, e.offsetY - gesture.y0) > 5) { gesture.moved = true; dragging = true; canvas.classList.add("dragging"); }
      if (!gesture.moved) return;
      if (gesture.type === "pan") { freeCam(); pan(dx, dy); }
      else {
        anim = null; flight = null;
        cam.yaw += dx * 0.0065; cam.pitch = clampPitch(cam.pitch + dy * 0.0065);
        spin.yaw = dx * 0.0065; spin.pitch = dy * 0.0065; lastMove = performance.now();
      }
      requestDraw();
    } else if (gesture && gesture.type === "pinch" && pointers.size === 2) {
      const [p, q] = [...pointers.values()];
      const d = Math.hypot(p.x - q.x, p.y - q.y) || 1, m = { x: (p.x + q.x) / 2, y: (p.y + q.y) / 2 };
      freeCam(); dragging = true;
      cam.dist = clampDist((gesture.dist0 * gesture.d0) / d);
      pan(m.x - gesture.m.x, m.y - gesture.m.y); gesture.m = m;
      requestDraw();
    } else if (e.pointerType === "mouse" && !gesture) {
      const i = nodeAt(e.offsetX, e.offsetY, false);
      if (i !== S.hover) { S.hover = i; canvas.style.cursor = i >= 0 ? "pointer" : "grab"; requestDraw(); }
    }
  });
  const endPointer = (e) => {
    const g = gesture;
    pointers.delete(e.pointerId);
    if (g && g.type !== "pinch" && !g.moved && e.type === "pointerup") tap(e.offsetX, e.offsetY, g.touch);
    if (pointers.size === 1) { const [p] = [...pointers.values()]; gesture = { type: "turn", x0: p.x, y0: p.y, moved: true }; }
    else if (pointers.size === 0) {
      gesture = null; dragging = false; canvas.classList.remove("dragging");
      if (performance.now() - lastMove > 90 || reduceMotion) spin.yaw = spin.pitch = 0; // a held stop stops; a flick keeps turning
      if (g && g.moved) { updateHere(); writeHash(); }
      requestDraw();
    }
  };
  canvas.addEventListener("pointerup", endPointer);
  canvas.addEventListener("pointercancel", endPointer);
  canvas.addEventListener("pointerleave", () => { if (S.hover >= 0 && !pointers.size) { S.hover = -1; requestDraw(); } });
  let wheelTimer = 0;
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    freeCam();
    cam.dist = clampDist(cam.dist * Math.exp(e.deltaY * (e.deltaMode === 1 ? 0.05 : 0.0014)));
    requestDraw();
    clearTimeout(wheelTimer); wheelTimer = setTimeout(() => { updateHere(); writeHash(); }, 200);
  }, { passive: false });
  canvas.addEventListener("dblclick", (e) => {
    const i = nodeAt(e.offsetX, e.offsetY, false);
    if (i >= 0) flyTo({ x: P[3 * i], y: P[3 * i + 1], z: P[3 * i + 2], dist: clampDist(cam.dist * 0.45) }, 700);
  });
  function tap(x, y, touch) {
    const i = nodeAt(x, y, touch);
    if (i >= 0) {
      ripples.push({ i, t0: performance.now() });
      if (touch) { try { if (navigator.vibrate) navigator.vibrate(12); } catch (err) { /* not allowed here */ } }
      if (S.picking && S.trace.a >= 0 && i !== S.trace.a) { runTrace(S.trace.a, i); return; }
      focusNode(i);
      return;
    }
    const li = linkAt(x, y);
    if (li >= 0) {
      const l = L[li], lis = [];
      L.forEach((m, k) => { if (m.a === l.a && m.b === l.b) lis.push(k); });
      interrogateLinks(lis);
    }
  }
  canvas.addEventListener("keydown", (e) => {
    let handled = true;
    const step = 0.12;
    if (e.shiftKey && e.key.startsWith("Arrow")) {
      freeCam();
      const d = 50;
      if (e.key === "ArrowLeft") pan(d, 0); else if (e.key === "ArrowRight") pan(-d, 0); else if (e.key === "ArrowUp") pan(0, d); else pan(0, -d);
    } else {
      switch (e.key) {
        case "ArrowLeft": cam.yaw -= step; break;
        case "ArrowRight": cam.yaw += step; break;
        case "ArrowUp": cam.pitch = clampPitch(cam.pitch - step); break;
        case "ArrowDown": cam.pitch = clampPitch(cam.pitch + step); break;
        case "+": case "=": freeCam(); cam.dist = clampDist(cam.dist * 0.8); break;
        case "-": case "_": freeCam(); cam.dist = clampDist(cam.dist * 1.25); break;
        case "0": S.camMode = S.focus >= 0 ? "focus" : "fit"; animateTo(null); break;
        case "Escape": if (S.links || S.nodeLadder) back(); else if (S.focus >= 0 || S.trace.a >= 0 || S.hl) clearFocus(); break;
        case "Enter": case " ": {
          const i = nodeAt(W / 2, (H - inset) / 2, false) >= 0 ? nodeAt(W / 2, (H - inset) / 2, false) : nearestToCentre();
          if (i >= 0) focusNode(i);
          break;
        }
        default: handled = false;
      }
    }
    if (handled) { e.preventDefault(); requestDraw(); }
  });
  window.addEventListener("resize", resize);

  // ------------------------------------------------------------------ the Sky's own controls
  const press = (id, on) => { const b = byId(id); if (b) b.setAttribute("aria-pressed", on ? "true" : "false"); };
  function toggle(id, key, msg) {
    const b = byId(id);
    if (!b) return;
    press(id, opt[key]);
    b.addEventListener("click", () => {
      opt[key] = !opt[key]; press(id, opt[key]);
      if (key === "orbit" && opt.orbit && reduceMotion) { opt.orbit = false; press(id, false); announce(t("sky.orbit_reduced")); return; }
      announce(t(msg + (opt[key] ? ".on" : ".off")));
      requestDraw();
    });
  }
  toggle("sky-generation", "generation", "sky.announce.generation");
  toggle("sky-names", "names", "sky.announce.names");
  toggle("sky-scenery", "scenery", "sky.announce.scenery");
  toggle("sky-orbit", "orbit", "sky.announce.orbit");
  document.querySelectorAll("[data-sky-view]").forEach((b) => {
    b.addEventListener("click", () => {
      const [yaw, pitch] = VIEWS[b.dataset.skyView];
      const target = S.camMode === "focus" ? fitEgo({ yaw, pitch }) : fitAll({ yaw, pitch });
      if (S.camMode === "free") S.camMode = "fit";
      flyTo(Object.assign(target, { yaw, pitch }), 900);
      announce(t("sky.announce.view", { view: b.textContent.trim() }));
    });
  });

  // Play history: the period grows year by year from the first recorded year, so each
  // mark lights when the year reaches its first dated record. Undated marks stay drawn
  // hollow (never hidden), exactly as the period scrub draws them.
  const playBtn = byId("sky-play");
  const AX = FR.time.axis;
  function syncPlay() { if (playBtn) { playBtn.textContent = t(playing ? "sky.pause" : "sky.play"); playBtn.setAttribute("aria-pressed", playing ? "true" : "false"); } }
  let lastHere = 0;
  function stepPlay(dt) {
    playYear += 0.2 * dt;
    const y = Math.min(AX.y1, Math.floor(playYear));
    if (y !== S.scrub.y1) {
      S.scrub.y1 = y; computeEmphasis(); syncScrub();
      const now = performance.now();
      if (now - lastHere > 400) { lastHere = now; updateHere(); }
    }
    if (playYear >= AX.y1 + 1) { playing = false; syncPlay(); update(false); announce(t("sky.announce.play_end")); }
  }
  if (playBtn) {
    syncPlay();
    playBtn.addEventListener("click", () => {
      if (playing) { playing = false; syncPlay(); update(false); return; }
      if (!S.scrub.on || S.scrub.y1 >= AX.y1) { S.scrub = { on: true, y0: AX.y0, y1: AX.y0 }; playYear = AX.y0; }
      else { S.scrub.on = true; playYear = S.scrub.y1; }
      if (reduceMotion) { S.scrub.y1 = AX.y1; syncScrub(); update(false); announce(t("sky.announce.play_end")); return; }
      playing = true; syncPlay(); syncScrub(); computeEmphasis(); requestDraw();
      announce(t("sky.announce.play", { y: AX.y0 }));
    });
  }

  return {
    start() {
      resize();
      if (S.camMode !== "free") Object.assign(cam, S.camMode === "focus" ? fitEgo() : fitAll());
    },
    requestDraw,
    animateTo,
    isAnimating: () => !!anim,
    stopAnim() { anim = null; },
    blend,
    refit() {
      inset = stageInset();
      if (anim || S.camMode === "free") { requestDraw(); return; }
      flyTo(S.camMode === "focus" ? fitEgo() : fitAll(), 500);
    },
    rebase() { S.baseDist = fitAll().dist; },
    cameraState: () => ({ target: [Math.round(cam.x), Math.round(cam.y), Math.round(cam.z)], yaw: Math.round(cam.yaw * 1000) / 1000,
      pitch: Math.round(cam.pitch * 1000) / 1000, distance: Math.round(cam.dist) }),
    applyCamera(c) {
      if (typeof c.distance !== "number") return false;
      const tg = Array.isArray(c.target) ? c.target : [0, 0, 0];
      Object.assign(cam, { x: +tg[0] || 0, y: +tg[1] || 0, z: +tg[2] || 0, yaw: +c.yaw || 0, pitch: clampPitch(+c.pitch || 0), dist: clampDist(c.distance) });
      return true;
    },
    clearCaches() {},
  };
};
