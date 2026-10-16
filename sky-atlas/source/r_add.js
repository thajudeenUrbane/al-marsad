
  // ------------------------------------------------------------------ Sky Atlas additions: chain light, journey trail,
  // absence marks, groups of stars, a test load drawn by the graphics card, and the globe
  const CHAIN_D = api.chainDist, CHAIN_MAX = Math.max(1, api.chainMax || 1);
  RGB.absent = hex(cv("--absent")); RGB.trail = hex(cv("--trail")); RGB.cluster = hex(cv("--cluster")); RGB.test = hex(cv("--test-star"));
  RGB.sea1 = hex(cv("--globe-sea-1")); RGB.sea2 = hex(cv("--globe-sea-2")); RGB.land = hex(cv("--globe-land")); RGB.coast = hex(cv("--globe-coast"));
  const mix = (a, b, f) => [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f].map(Math.round);

  // the journey trail: dashed gold segments through the stops passed so far, each stop numbered
  function drawTrail() {
    const tr = api.trail();
    if (!tr || globeOn) return;
    ctx.lineWidth = 1.6; ctx.setLineDash([5, 4]);
    if (tr.line) {
      for (let k = 1; k <= tr.k; k++) {
        const a = tr.stops[k - 1], b = tr.stops[k];
        if (!SS[a] || !SS[b]) continue;
        ctx.strokeStyle = rgba(RGB.trail, 0.85);
        ctx.beginPath(); ctx.moveTo(SX[a], SY[a]); ctx.lineTo(SX[b], SY[b]); ctx.stroke();
      }
    }
    ctx.setLineDash([]);
    ctx.font = FONT(10, 700); ctx.textAlign = "center"; ctx.textBaseline = "middle";
    tr.stops.forEach((i, k) => {
      if (!SS[i] || clustered[i]) return;
      const r = i === LIGHT ? lightCore() : radius(i), x = SX[i] - r - 9, y = SY[i] - r - 9;
      ctx.fillStyle = rgba(RGB.trail, k <= tr.k ? 0.95 : 0.35); ctx.beginPath(); ctx.arc(x, y, 7.5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = COL.bg; ctx.fillText(String(k + 1), x, y + 0.5);
    });
    ctx.textAlign = "left";
  }
  function drawAbsent(i, x, y, r) {
    ring(x, y, r + 6, RGB.absent, 0.95, 1.6, [3, 2]);
    ctx.strokeStyle = rgba(RGB.absent, 0.95); ctx.lineWidth = 1.6;
    ctx.beginPath(); ctx.moveTo(x - (r + 6) * 0.7, y + (r + 6) * 0.7); ctx.lineTo(x + (r + 6) * 0.7, y - (r + 6) * 0.7); ctx.stroke();
  }

  // ---- test load: synthetic points in the generation shells, never records
  let T = 0, TP = new Float32Array(0), TB = new Float32Array(0), TSX = new Float32Array(0), TSY = new Float32Array(0), TA = new Float32Array(0), TK = new Float64Array(0);
  function setTestLoad(count) {
    T = count;
    TP = new Float32Array(3 * T); TB = new Float32Array(T); TSX = new Float32Array(T); TSY = new Float32Array(T); TA = new Float32Array(T); TK = new Float64Array(T);
    const r = rng(7), g = () => (r() + r() + r() - 1.5) / 1.5, sh = META.shells || { sahabi: 190, tabii: 330, tabi_al_tabiin: 430 };
    for (let j = 0; j < T; j++) {
      const u = r(), rad = u < 0.62 ? sh.sahabi : u < 0.9 ? sh.tabii : sh.tabi_al_tabiin, a = r() * Math.PI * 2, rr = rad + g() * 34;
      TP[3 * j] = Math.cos(a) * rr; TP[3 * j + 1] = Math.sin(a) * rr; TP[3 * j + 2] = g() * 46;
      TB[j] = u < 0.62 ? 0.7 : u < 0.9 ? 0.5 : 0.38;
    }
    if (T) opt.cluster = true;
    press("sky-cluster", opt.cluster);
    requestDraw();
  }
  function projectTests() {
    const w0 = S.weights[0];
    if (!T || w0 < 0.02 || globeOn) { for (let j = 0; j < T; j++) TA[j] = 0; return; }
    const cx = W / 2, cyy = (H - inset) / 2;
    for (let j = 0; j < T; j++) {
      const vx = TP[3 * j] - cam.x, vy = TP[3 * j + 1] - cam.y, vz = TP[3 * j + 2] - cam.z;
      const x1 = cy_ * vx + sy_ * vz, z1 = -sy_ * vx + cy_ * vz, y2 = cp_ * vy - sp_ * z1, d = sp_ * vy + cp_ * z1 + cam.dist;
      if (d < 20) { TA[j] = 0; continue; }
      const s = F / d, x = cx + x1 * s, y = cyy + y2 * s;
      if (x < -4 || y < -4 || x > W + 4 || y > H + 4) { TA[j] = 0; continue; }
      TSX[j] = x; TSY[j] = y; TA[j] = TB[j] * w0 * depthA(d) * (S.focus >= 0 || S.hl ? 0.35 : 1);
    }
  }

  // ---- groups: stars that share a screen cell merge until you zoom in; the emphasised never merge
  const clustered = new Uint8Array(n);
  let clusters = [], buckets = null;
  const CELL = 30;
  function buildClusters() {
    clustered.fill(0); clusters = []; buckets = null;
    if (!opt.cluster || globeOn) return;
    buckets = new Map();
    const get = (x, y) => {
      const key = Math.floor(x / CELL) * 65536 + Math.floor(y / CELL);
      let b = buckets.get(key);
      if (!b) { b = { r: [], t: 0, sx: 0, sy: 0, X: 0, Y: 0, Z: 0, c: 0, a: 0 }; buckets.set(key, b); }
      return [key, b];
    };
    for (const i of order) {
      if (i === LIGHT || nodeLvl[i] || i === S.hover || !SS[i]) continue;
      const x = SX[i], y = SY[i];
      if (x < 0 || y < 0 || x > W || y > H) continue;
      const [, b] = get(x, y);
      b.r.push(i); b.sx += x; b.sy += y; b.X += P[3 * i]; b.Y += P[3 * i + 1]; b.Z += P[3 * i + 2]; b.c++; b.a = Math.max(b.a, nodeA[i]);
    }
    for (let j = 0; j < T; j++) {
      if (!TA[j]) { TK[j] = -1; continue; }
      const [key, b] = get(TSX[j], TSY[j]);
      TK[j] = key; b.t++; b.sx += TSX[j]; b.sy += TSY[j]; b.X += TP[3 * j]; b.Y += TP[3 * j + 1]; b.Z += TP[3 * j + 2]; b.c++; b.a = Math.max(b.a, Math.min(1, TA[j] * 1.6));
    }
    for (const b of buckets.values()) {
      if (b.c < 2) continue;
      for (const i of b.r) clustered[i] = 1;
      clusters.push({ x: b.sx / b.c, y: b.sy / b.c, X: b.X / b.c, Y: b.Y / b.c, Z: b.Z / b.c, n: b.c, rec: b.r.length, a: b.a });
    }
  }
  const inCluster = (j) => { if (!buckets || TK[j] < 0) return false; const b = buckets.get(TK[j]); return !!b && b.c >= 2; };
  function drawClusters() {
    ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.font = FONT(10, 700);
    for (const c of clusters) {
      const col = c.rec ? RGB.cluster : RGB.test, a = Math.max(0.45, c.a);
      ctx.fillStyle = rgba(col, 0.16 * a); ctx.beginPath(); ctx.arc(c.x, c.y, 10, 0, Math.PI * 2); ctx.fill();
      ring(c.x, c.y, 10, col, 0.9 * a, 1.3);
      const label = c.n > 999 ? Math.round(c.n / 100) / 10 + "k" : String(c.n);
      ctx.lineWidth = 3; ctx.strokeStyle = COL.bg; ctx.strokeText(label, c.x, c.y + 0.5);
      ctx.fillStyle = rgba(col, a); ctx.fillText(label, c.x, c.y + 0.5);
    }
    ctx.textAlign = "left";
  }
  function clusterAt(x, y, touch) {
    let best = null, bd = touch ? 20 : 13;
    for (const c of clusters) { const d = Math.hypot(c.x - x, c.y - y); if (d < bd) { bd = d; best = c; } }
    return best;
  }

  // ---- drawing the test load on the ordinary canvas (the slow path)
  function drawTests2D() {
    if (!T) return;
    for (let j = 0; j < T; j++) {
      if (!TA[j] || inCluster(j)) continue;
      ctx.fillStyle = rgba(RGB.test, TA[j]); ctx.fillRect(TSX[j] - 0.75, TSY[j] - 0.75, 1.5, 1.5);
    }
  }

  // ---- faster drawing: a WebGL layer under the canvas draws the distant scenery and the test load as point sprites
  const glc = byId("sky-gl");
  let gl = null, glProg = null, glBuf = null, glData = new Float32Array(0), glLoc = null;
  function initGL() {
    if (gl) return true;
    if (!glc) return false;
    try { gl = glc.getContext("webgl", { premultipliedAlpha: false, antialias: false, alpha: true }); } catch (e) { gl = null; }
    if (!gl) return false;
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; };
    glProg = gl.createProgram();
    gl.attachShader(glProg, sh(gl.VERTEX_SHADER, "attribute vec2 p;attribute float s;attribute vec4 c;uniform vec2 res;varying vec4 vc;void main(){vec2 q=p/res*2.0-1.0;gl_Position=vec4(q.x,-q.y,0.0,1.0);gl_PointSize=s;vc=c;}"));
    gl.attachShader(glProg, sh(gl.FRAGMENT_SHADER, "precision mediump float;varying vec4 vc;void main(){vec2 d=gl_PointCoord-0.5;if(dot(d,d)>0.25)discard;gl_FragColor=vc;}"));
    gl.linkProgram(glProg);
    if (!gl.getProgramParameter(glProg, gl.LINK_STATUS)) { gl = null; return false; }
    glBuf = gl.createBuffer();
    glLoc = { p: gl.getAttribLocation(glProg, "p"), s: gl.getAttribLocation(glProg, "s"), c: gl.getAttribLocation(glProg, "c"), res: gl.getUniformLocation(glProg, "res") };
    return true;
  }
  function drawGL() {
    if (!gl) return;
    if (glc.width !== canvas.width || glc.height !== canvas.height) { glc.width = canvas.width; glc.height = canvas.height; }
    gl.viewport(0, 0, glc.width, glc.height);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    const need = 7 * (FAR.length + T);
    if (glData.length < need) glData = new Float32Array(need);
    let k = 0;
    const put = (x, y, s, c, a) => { glData[k++] = x; glData[k++] = y; glData[k++] = s; glData[k++] = c[0] / 255; glData[k++] = c[1] / 255; glData[k++] = c[2] / 255; glData[k++] = a; };
    if (opt.scenery) {
      const f = Math.min(canvas.width, canvas.height) * 0.9, cx = canvas.width / 2, cy = canvas.height / 2;
      for (const [x, y, z, a, s, c] of FAR) {
        const x1 = cy_ * x + sy_ * z, z1 = -sy_ * x + cy_ * z, y2 = cp_ * y - sp_ * z1, z2 = sp_ * y + cp_ * z1;
        if (z2 < 0.05) continue;
        put(cx + (x1 / z2) * f, cy + (y2 / z2) * f, s + 0.5, c, a);
      }
    }
    for (let j = 0; j < T; j++) if (TA[j] && !inCluster(j)) put(TSX[j] * DPR, TSY[j] * DPR, 1.6 * DPR, RGB.test, TA[j]);
    const count = k / 7;
    gl.useProgram(glProg);
    gl.bindBuffer(gl.ARRAY_BUFFER, glBuf);
    gl.bufferData(gl.ARRAY_BUFFER, glData.subarray(0, k), gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(glLoc.p); gl.vertexAttribPointer(glLoc.p, 2, gl.FLOAT, false, 28, 0);
    gl.enableVertexAttribArray(glLoc.s); gl.vertexAttribPointer(glLoc.s, 1, gl.FLOAT, false, 28, 8);
    gl.enableVertexAttribArray(glLoc.c); gl.vertexAttribPointer(glLoc.c, 4, gl.FLOAT, false, 28, 12);
    gl.uniform2f(glLoc.res, glc.width, glc.height);
    gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    if (count) gl.drawArrays(gl.POINTS, 0, count);
  }
  function setGPU(on) {
    if (on && !initGL()) { opt.gpu = false; press("sky-gpu", false); announce(t("x.sky.announce.gpu.none")); return false; }
    opt.gpu = on; press("sky-gpu", on);
    const stage = canvas.parentElement;
    stage.classList.toggle("gpu", on);
    if (glc) glc.hidden = !on;
    if (!on && gl) { gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT); }
    requestDraw();
    return true;
  }

  // ---- how fast the drawing is, shown while there is a test load or the GPU is on
  const perfOut = byId("sky-perf");
  let perfMs = 0, perfFps = 0, perfLast = 0, perfShown = 0;
  function notePerf(ms, now) {
    perfMs = perfMs ? perfMs * 0.9 + ms * 0.1 : ms;
    if (perfLast && now - perfLast < 200) perfFps = perfFps ? perfFps * 0.9 + (1000 / (now - perfLast)) * 0.1 : 1000 / (now - perfLast);
    perfLast = now;
    if (!perfOut) return;
    const show = T > 0 || opt.gpu;
    perfOut.hidden = !show;
    if (show && now - perfShown > 400) {
      perfShown = now;
      perfOut.textContent = t("x.perf", { ms: perfMs.toFixed(1), fps: perfFps ? Math.round(Math.min(144, perfFps)) : "—",
        n: (n + T).toLocaleString(S.lang === "ar" ? "ar" : "en"), mode: t(opt.gpu ? "x.perf.gpu" : "x.perf.cpu") });
    }
  }

  // ---- the globe: an orthographic globe for the Geography view. The camera's turn is the globe's turn.
  const LAND = api.land || [];
  let globeOn = false, globeSaved = null, globeHits = [];
  const DEG = Math.PI / 180;
  function globeParams() {
    const lon0 = 41 - cam.yaw / DEG, lat0 = Math.max(-80, Math.min(80, 23 + cam.pitch / DEG));
    const R = 6 * Math.min(W, H - inset) * (1800 / cam.dist); // opens on the Hijaz; zoom out for the whole globe
    return { lon0, lat0, R, cx: W / 2, cy: (H - inset) / 2, s0: Math.sin(lat0 * DEG), c0: Math.cos(lat0 * DEG) };
  }
  function ortho(lon, lat, g, lift) {
    const l = (lon - g.lon0) * DEG, p = lat * DEG, cp = Math.cos(p), sp = Math.sin(p), cl = Math.cos(l);
    const k = g.R * (1 + (lift || 0));
    return [g.cx + k * cp * Math.sin(l), g.cy - k * (g.c0 * sp - g.s0 * cp * cl), g.s0 * sp + g.c0 * cp * cl];
  }
  function setGlobe(on) {
    if (on === globeOn) return;
    if (on) {
      globeSaved = { cam: Object.assign({}, cam), camMode: S.camMode };
      anim = null; flight = null; spin.yaw = spin.pitch = 0; playing = false; syncPlay();
      S.weights = [0, 0, 1, 0, 0]; blend();
      Object.assign(cam, { yaw: 0, pitch: 0, dist: 1800 });
      S.camMode = "free"; globeOn = true;
      announce(t("x.sky.announce.globe.on"));
    } else {
      globeOn = false;
      if (globeSaved) { Object.assign(cam, globeSaved.cam); S.camMode = globeSaved.camMode === "free" ? "fit" : globeSaved.camMode; }
      S.baseDist = fitAll().dist;
      announce(t("x.sky.announce.globe.off"));
    }
    press("frame-globe", globeOn);
    syncFrameControls(); updateHere(); api.updateTextAlt(); requestDraw();
  }
  function arcPoints(a, b, g) {
    const v = (lon, lat) => [Math.cos(lat * DEG) * Math.cos(lon * DEG), Math.cos(lat * DEG) * Math.sin(lon * DEG), Math.sin(lat * DEG)];
    const A = v(a[0], a[1]), B = v(b[0], b[1]);
    const om = Math.acos(Math.max(-1, Math.min(1, A[0] * B[0] + A[1] * B[1] + A[2] * B[2]))) || 1e-6;
    const out = [];
    for (let k = 0; k <= 24; k++) {
      const tt = k / 24, s1 = Math.sin((1 - tt) * om) / Math.sin(om), s2 = Math.sin(tt * om) / Math.sin(om);
      const x = s1 * A[0] + s2 * B[0], y = s1 * A[1] + s2 * B[1], z = s1 * A[2] + s2 * B[2];
      out.push(ortho(Math.atan2(y, x) / DEG, Math.asin(Math.max(-1, Math.min(1, z))) / DEG, g, Math.sin(Math.PI * tt) * Math.min(0.25, 0.4 * om + 0.012)));
    }
    return out;
  }
  function drawGlobe() {
    const g = globeParams();
    globeHits = [];
    // the sea: a sharp-edged disc
    const sea = ctx.createRadialGradient(g.cx - g.R * 0.3, g.cy - g.R * 0.3, 0, g.cx, g.cy, g.R);
    sea.addColorStop(0, rgba(RGB.sea1, 1)); sea.addColorStop(1, rgba(RGB.sea2, 1));
    ctx.fillStyle = sea; ctx.beginPath(); ctx.arc(g.cx, g.cy, g.R, 0, Math.PI * 2); ctx.fill();
    // graticule every ten degrees
    ctx.lineWidth = 0.8; ctx.strokeStyle = rgba(RGB.deco, 0.16);
    const line = (pts) => { ctx.beginPath(); let on = false; for (const p of pts) { if (p[2] < 0) { on = false; continue; } if (!on) { ctx.moveTo(p[0], p[1]); on = true; } else ctx.lineTo(p[0], p[1]); } ctx.stroke(); };
    for (let lon = -180; lon < 180; lon += 10) { const pts = []; for (let lat = -80; lat <= 80; lat += 4) pts.push(ortho(lon, lat, g)); line(pts); }
    for (let lat = -80; lat <= 80; lat += 10) { const pts = []; for (let lon = -180; lon <= 180; lon += 4) pts.push(ortho(lon, lat, g)); line(pts); }
    // land: points on the far side are pushed to the limb, so the fill stays whole
    ctx.fillStyle = rgba(RGB.land, 1); ctx.strokeStyle = rgba(RGB.coast, 0.9); ctx.lineWidth = 0.9;
    for (const ring of LAND) {
      ctx.beginPath(); let any = false;
      for (let k = 0; k < ring.length; k += 2) {
        let [x, y, z] = ortho(ring[k], ring[k + 1], g);
        if (z >= 0) any = true;
        else { const dx = x - g.cx, dy = y - g.cy, d = Math.hypot(dx, dy) || 1; x = g.cx + (dx / d) * g.R; y = g.cy + (dy / d) * g.R; }
        if (k === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      if (!any) continue;
      ctx.closePath(); ctx.fill(); ctx.stroke();
    }
    ctx.strokeStyle = rgba(RGB.ring, 0.45); ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(g.cx, g.cy, g.R, 0, Math.PI * 2); ctx.stroke();
    // the record moving between places: arcs in the order of the dated events
    const geoOf = (i) => N[i].geo;
    const moves = api.globeMoves();
    const y1 = S.scrub.on ? S.scrub.y1 + 1 : Infinity;
    ctx.lineWidth = 1.6;
    // one arc per direction between two places, bowed to its own side so the way back does not cover the way there
    const pairs = new Map();
    for (const m of moves) {
      if (m.y > y1) continue;
      const key = m.a + ">" + m.b;
      if (!pairs.has(key)) pairs.set(key, { a: m.a, b: m.b, ys: [] });
      const yy = Math.floor(m.y), ys = pairs.get(key).ys;
      if (!ys.includes(yy)) ys.push(yy);
    }
    for (const pr of pairs.values()) {
      const pts = arcPoints(geoOf(pr.a), geoOf(pr.b), g);
      const p0 = pts[0], p1 = pts[pts.length - 1], L0 = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) || 1;
      const ox = -(p1[1] - p0[1]) / L0, oy = (p1[0] - p0[0]) / L0, bow = Math.min(40, L0 * 0.18);
      pts.forEach((p, k) => { const s = Math.sin((Math.PI * k) / (pts.length - 1)) * bow; p[0] += ox * s; p[1] += oy * s; });
      ctx.strokeStyle = rgba(RGB.trail, 0.8); line(pts);
      const mid = pts[12], nx = pts[13];
      if (mid[2] > 0 && nx[2] > 0) {
        const dx = nx[0] - mid[0], dy = nx[1] - mid[1], d = Math.hypot(dx, dy) || 1, ux = dx / d, uy = dy / d;
        ctx.fillStyle = rgba(RGB.trail, 0.95); ctx.beginPath(); ctx.moveTo(mid[0] + ux * 6, mid[1] + uy * 6); ctx.lineTo(mid[0] - uy * 4, mid[1] + ux * 4); ctx.lineTo(mid[0] + uy * 4, mid[1] - ux * 4); ctx.closePath(); ctx.fill();
        const label = pr.ys.length > 3 ? pr.ys.slice(0, 3).join(", ") + "…" : pr.ys.join(", ");
        ctx.font = FONT(10, 600); ctx.textAlign = ox >= 0 ? "left" : "right";
        ctx.lineWidth = 3; ctx.strokeStyle = COL.bg; ctx.strokeText(label, mid[0] + ox * 9, mid[1] + oy * 9);
        ctx.fillStyle = rgba(RGB.trail, 0.95); ctx.fillText(label, mid[0] + ox * 9, mid[1] + oy * 9);
        ctx.textAlign = "left"; ctx.lineWidth = 1.6;
      }
    }
    // places, then the events and people the record ties to each place, ringed around it
    const around = new Map();
    for (let i = 0; i < n; i++) {
      if (i === LIGHT || !nodeA[i]) continue;
      const k = N[i].k;
      if ((k === "event" || k === "person" || k === "group") && N[i].pl !== undefined && geoOf(N[i].pl)) {
        if (!around.has(N[i].pl)) around.set(N[i].pl, []);
        around.get(N[i].pl).push(i);
      }
    }
    ctx.textBaseline = "middle";
    const labels = [], pts = [];
    for (let i = 0; i < n; i++) {
      if (N[i].k !== "place" || !geoOf(i) || !visible(i)) continue;
      const q = ortho(geoOf(i)[0], geoOf(i)[1], g);
      if (q[2] >= 0) pts.push([i, q[0], q[1]]);
    }
    // a place's events ring it only when no other place is close on screen, or when it is in focus
    const lonely = (i, x, y) => i === S.focus || i === S.hover || pts.every(([j, px, py]) => j === i || Math.hypot(px - x, py - y) > 64);
    pts.sort((a, b) => (a[0] === S.focus) - (b[0] === S.focus));
    for (const [i, x, y] of pts) {
      const a = Math.max(0.25, nodeA[i]);
      drawMark(i, x, y, 4.5, a, false);
      if (i === S.focus) ring(x, y, 11, RGB.ring, 1, 2); else if (i === S.hover) ring(x, y, 9, RGB.ring, 0.8, 1);
      globeHits.push([x, y, i, 7]);
      labels.push([i, x, y, a]);
      const all = around.get(i) || [];
      if (!lonely(i, x, y)) {
        if (all.length) { // a count beside the place instead of a ring; tap the place to open it
          const s = String(all.length);
          ctx.font = FONT(10, 700); const w = ctx.measureText(s).width + 8;
          ctx.fillStyle = rgba(RGB.event, 0.9); ctx.beginPath(); ctx.arc(x - 9, y + 9, Math.max(7, w / 2), 0, Math.PI * 2); ctx.fill();
          ctx.fillStyle = COL.bg; ctx.textAlign = "center"; ctx.fillText(s, x - 9, y + 9.5); ctx.textAlign = "left";
        }
        continue;
      }
      const list = all.sort((p, q) => (N[p].k === "event" ? 0 : 1) - (N[q].k === "event" ? 0 : 1) || p - q);
      list.forEach((j, m) => {
        const ringNo = m < 10 ? 0 : m < 26 ? 1 : 2, per = [10, 16, 24][ringNo], idx = m - [0, 10, 26][ringNo];
        const ang = (idx / per) * Math.PI * 2 - Math.PI / 2, rr = 16 + ringNo * 9;
        const px = x + Math.cos(ang) * rr, py = y + Math.sin(ang) * rr;
        drawMark(j, px, py, 3, nodeA[j], nodeHollow[j]);
        if (absentSet && absentSet.has(j)) drawAbsent(j, px, py, 2);
        if (j === S.focus) ring(px, py, 8, RGB.ring, 1, 2); else if (j === S.hover) ring(px, py, 6, RGB.ring, 0.8, 1); else if (nodeLvl[j]) ring(px, py, 6, RGB.ring, 0.7, 1);
        globeHits.push([px, py, j, 4]);
        if (j === S.focus || j === S.hover) labels.push([j, px, py, 1]);
      });
    }
    const boxes = [];
    labels.sort((p, q) => (q[0] === S.focus) - (p[0] === S.focus));
    for (const [i, x, y, a] of labels) {
      ctx.font = FONT(12, i === S.focus ? 700 : 600);
      const w = ctx.measureText(N[i].n).width;
      const tries = [[x + 10, y - 12], [x + 10, y + 14], [x - 10 - w, y - 12], [x - 10 - w, y + 14], [x + 10, y - 28], [x - 10 - w, y + 30]];
      let at = null;
      for (const [tx, ty] of tries) { const b = [tx - 2, ty - 8, tx + w + 2, ty + 8]; if (!boxes.some((o) => o[0] < b[2] && o[2] > b[0] && o[1] < b[3] && o[3] > b[1])) { at = [tx, ty]; boxes.push(b); break; } }
      if (!at) continue;
      ctx.globalAlpha = a; ctx.lineWidth = 3.5; ctx.strokeStyle = COL.bg; ctx.lineJoin = "round";
      ctx.strokeText(N[i].n, at[0], at[1]); ctx.fillStyle = COL.ink; ctx.fillText(N[i].n, at[0], at[1]);
    }
    ctx.globalAlpha = 1;
    const c = api.placeCounts();
    ctx.font = FONT(11, 400); ctx.fillStyle = COL.muted; ctx.textBaseline = "alphabetic";
    ctx.fillText(t("x.globe.counts", { n: c.located, total: c.places }), 12, H - inset - 12);
  }
  let absentSet = null;
