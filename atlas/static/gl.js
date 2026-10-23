/* Sky Atlas renderer. WebGL draws the marks and lines (or, when WebGL is missing or
   switched off, a plain 2D canvas does); a 2D canvas on top draws the light, the names
   and the markers. The renderer knows nothing about the records: the page hands it
   positions, colours and shapes, and asks it what was tapped. */
(function () {
  "use strict";

  const VS_PTS = `
attribute vec3 a_pos; attribute vec4 a_col; attribute float a_shape; attribute float a_glow;
uniform mat4 u_mvp; uniform float u_scale; uniform float u_px;
varying vec4 v_col; varying float v_shape; varying float v_glow; varying float v_size;
void main() {
  vec4 p = u_mvp * vec4(a_pos, 1.0);
  gl_Position = p;
  float s = clamp(u_scale / max(p.w, 1.0), 3.2, a_col.a < 0.5 ? 7.0 : 24.0) * u_px; // dimmed marks stay small
  float g = a_glow > 0.0 ? 2.4 : 1.15;
  gl_PointSize = a_col.a > 0.0 ? s * g : 0.0;
  v_col = a_col; v_shape = a_shape; v_glow = a_glow; v_size = gl_PointSize / g;
}`;
  // Shapes, by type only: 0 person (disc), 1 event (four-point star), 2 place (diamond),
  // 3 story (hexagonal ring), 4 group (triangle), 5 opponent (dark stone, ember rim).
  // Shape + 10 is the same shape drawn hollow: no recorded date.
  const FS_PTS = `
precision mediump float;
varying vec4 v_col; varying float v_shape; varying float v_glow; varying float v_size;
void main() {
  float g = v_glow > 0.0 ? 2.4 : 1.15;
  vec2 q = (gl_PointCoord * 2.0 - 1.0) * g;
  float ax = abs(q.x), ay = abs(q.y);
  float sh = v_shape;
  bool hollow = sh > 9.5;
  if (hollow) sh -= 10.0;
  float d;
  vec3 col = v_col.rgb;
  float rim = 0.0;
  if (sh < 0.5) d = length(q) - 0.62;
  else if (sh < 1.5) d = pow(ax, 0.55) + pow(ay, 0.55) - 0.95;
  else if (sh < 2.5) d = ax + ay - 0.82;
  else if (sh < 3.5) { float h = max(ax * 0.866 + ay * 0.5, ay); d = abs(h - 0.62) - 0.16; }
  else if (sh < 4.5) { vec2 t = vec2(ax, -q.y); d = max(t.x * 0.866 + t.y * 0.5, -t.y) - 0.42; }
  else { d = length(q) - 0.7; rim = smoothstep(0.28, 0.0, abs(length(q) - 0.62)); }
  if (hollow) d = abs(d + 0.13) - 0.13;
  float px = v_size * 0.5;
  float core = clamp(0.5 - d * px, 0.0, 1.0);
  float r = length(gl_PointCoord * 2.0 - 1.0);
  float halo = v_glow * 0.6 * pow(max(0.0, 1.0 - r), 2.2);
  if (sh > 4.5) col = mix(col, vec3(0.86, 0.38, 0.26), rim);
  float a = max(core, halo * (1.0 - core)) * v_col.a;
  if (a < 0.01) discard;
  gl_FragColor = vec4(col * a, a);
}`;
  const VS_LN = `
attribute vec3 a_pos; attribute vec4 a_col; uniform mat4 u_mvp; varying vec4 v_col;
void main() { gl_Position = u_mvp * vec4(a_pos, 1.0); v_col = a_col; }`;
  const FS_LN = `
precision mediump float; varying vec4 v_col;
void main() { gl_FragColor = vec4(v_col.rgb * v_col.a, v_col.a); }`;
  // pinpoints: the distant scenery (direction only) and the synthetic test load
  const VS_PIN = `
attribute vec3 a_pos; uniform mat4 u_mvp; uniform float u_size;
void main() { gl_Position = u_mvp * vec4(a_pos, 1.0); gl_PointSize = u_size; }`;
  const FS_PIN = `
precision mediump float; uniform vec4 u_col;
void main() { vec2 q = gl_PointCoord * 2.0 - 1.0; float a = clamp(1.0 - dot(q, q), 0.0, 1.0) * u_col.a; gl_FragColor = vec4(u_col.rgb * a, a); }`;
  // the globe's body: an opaque sphere that hides what lies behind it
  const VS_GLOBE = `attribute vec3 a_pos; uniform mat4 u_mvp; varying vec3 v_n;
void main() { gl_Position = u_mvp * vec4(a_pos, 1.0); v_n = normalize(a_pos); }`;
  const FS_GLOBE = `precision mediump float; varying vec3 v_n; uniform vec3 u_c;
void main() { float l = 0.55 + 0.45 * max(0.0, v_n.y * 0.4 + v_n.z * 0.6); gl_FragColor = vec4(u_c * l, 1.0); }`;

  // ------------------------------------------------------------------ matrices
  function perspective(fovy, aspect, near, far) {
    const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far);
    return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0];
  }
  function lookAt(e, c, up) {
    let zx = e[0] - c[0], zy = e[1] - c[1], zz = e[2] - c[2];
    let l = Math.hypot(zx, zy, zz) || 1; zx /= l; zy /= l; zz /= l;
    let xx = up[1] * zz - up[2] * zy, xy = up[2] * zx - up[0] * zz, xz = up[0] * zy - up[1] * zx;
    l = Math.hypot(xx, xy, xz) || 1; xx /= l; xy /= l; xz /= l;
    const yx = zy * xz - zz * xy, yy = zz * xx - zx * xz, yz = zx * xy - zy * xx;
    return [xx, yx, zx, 0, xy, yy, zy, 0, xz, yz, zz, 0,
      -(xx * e[0] + xy * e[1] + xz * e[2]), -(yx * e[0] + yy * e[1] + yz * e[2]), -(zx * e[0] + zy * e[1] + zz * e[2]), 1];
  }
  function mul(a, b) {
    const o = new Array(16);
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) {
      let s = 0;
      for (let k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k];
      o[i * 4 + j] = s;
    }
    return o;
  }
  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  function rng(seed) { let x = seed >>> 0; return () => { x ^= x << 13; x >>>= 0; x ^= x >>> 17; x ^= x << 5; x >>>= 0; return x / 4294967296; }; }

  function compile(gl, vs, fs) {
    const p = gl.createProgram();
    for (const [type, src] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) {
      const s = gl.createShader(type);
      gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      gl.attachShader(p, s);
    }
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    return p;
  }

  // ------------------------------------------------------------------ the renderer
  window.AtlasSky = function (opts) {
    const { glCanvas, ovCanvas, cvCanvas, n, api } = opts;
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let gl = null;
    try { gl = glCanvas.getContext("webgl", { antialias: true, premultipliedAlpha: true, alpha: false }); } catch (e) { gl = null; }
    const hasGL = !!gl;
    let mode = hasGL ? "gl" : "2d";
    const ctx = ovCanvas.getContext("2d");
    const c2 = cvCanvas.getContext("2d");
    let P, L, PIN, GLB, A, U, AL, UL, APIN, UPIN, AG, UG, B;
    if (hasGL) {
      P = compile(gl, VS_PTS, FS_PTS); L = compile(gl, VS_LN, FS_LN); PIN = compile(gl, VS_PIN, FS_PIN); GLB = compile(gl, VS_GLOBE, FS_GLOBE);
      const loc = (p, a) => gl.getAttribLocation(p, a), uni = (p, u) => gl.getUniformLocation(p, u);
      A = { pos: loc(P, "a_pos"), col: loc(P, "a_col"), shape: loc(P, "a_shape"), glow: loc(P, "a_glow") };
      U = { mvp: uni(P, "u_mvp"), scale: uni(P, "u_scale"), px: uni(P, "u_px") };
      AL = { pos: loc(L, "a_pos"), col: loc(L, "a_col") }; UL = { mvp: uni(L, "u_mvp") };
      APIN = { pos: loc(PIN, "a_pos") }; UPIN = { mvp: uni(PIN, "u_mvp"), size: uni(PIN, "u_size"), col: uni(PIN, "u_col") };
      AG = { pos: loc(GLB, "a_pos") }; UG = { mvp: uni(GLB, "u_mvp"), c: uni(GLB, "u_c") };
      const buf = () => gl.createBuffer();
      B = { pos: buf(), col: buf(), shape: buf(), glow: buf(), idx: buf(), lpos: buf(), lcol: buf(), xpos: buf(), xcol: buf(), sky: buf(), test: buf(), globe: buf(), gidx: buf() };
    }
    glCanvas.hidden = mode !== "gl"; cvCanvas.hidden = mode !== "2d";

    const cur = new Float32Array(n * 3), from = new Float32Array(n * 3), to = new Float32Array(n * 3);
    let morph = null;                      // {t0, dur}
    let cols = new Float32Array(n * 4), shapes = new Float32Array(n), glows = new Float32Array(n);
    let drawCols = cols;                   // cols with grouped stars hidden
    const order = new Uint16Array(n); for (let i = 0; i < n; i++) order[i] = i;
    const depth = new Float32Array(n);
    const SX = new Float32Array(n), SY = new Float32Array(n), SW = new Float32Array(n);
    let pairs = new Int32Array(0), lineCols = new Float32Array(0), lineBuf = new Float32Array(0), lineColBuf = new Float32Array(0);
    let extra = null;                      // {pos, col}: coastlines, arcs, bars
    let globe = null;                      // {c: [x,y,z], r} when the globe hides its far side
    let globeCount = 0;
    let W = 1, H = 1, DPR = 1, mvp = null, sortDirty = true;
    const opt = { scenery: true, tests: 0 };
    let clusters = [], ripples = [];

    const cam = { target: [0, 0, 0], dist: 2400, yaw: 0.6, pitch: 0.32 };
    const inset = { l: 0, r: 0, t: 0, b: 0 };
    let fly = null, spin = null;

    // -------------------------------------------------------------- the scenery and the test load
    const SKY_N = 1600;
    const skyDirs = new Float32Array(SKY_N * 3);
    { const r = rng(7919); for (let k = 0; k < SKY_N; k++) { const u = r() * 2 - 1, th = r() * Math.PI * 2, s = Math.sqrt(1 - u * u); skyDirs.set([s * Math.cos(th) * 1000, u * 1000, s * Math.sin(th) * 1000], 3 * k); } }
    let testPos = new Float32Array(0);
    function setTestLoad(count) {
      opt.tests = count;
      testPos = new Float32Array(count * 3);
      const r = rng(104729);
      for (let k = 0; k < count; k++) { // synthetic points in shells round the light: not records
        const u = r() * 2 - 1, th = r() * Math.PI * 2, s = Math.sqrt(1 - u * u), rad = 260 + r() * 820;
        testPos.set([s * Math.cos(th) * rad, u * rad, s * Math.sin(th) * rad], 3 * k);
      }
      if (hasGL) upload(B.test, testPos, gl.STATIC_DRAW);
      requestDraw();
    }
    if (hasGL) { upload(B.sky, skyDirs, gl.STATIC_DRAW); }

    // -------------------------------------------------------------- data in
    function upload(b, data, usage) { gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, data, usage || gl.DYNAMIC_DRAW); }
    function setPositions(p) { cur.set(p); morph = null; if (hasGL) upload(B.pos, cur); rebuildLines(); sortDirty = true; requestDraw(); }
    function morphTo(p, dur) {
      if (reduced || !dur) { setPositions(p); return; }
      from.set(cur); to.set(p); morph = { t0: performance.now(), dur }; requestDraw();
    }
    function setStyle(c, s, g) {
      cols = c; shapes = s; glows = g; drawCols = cols;
      if (hasGL) { upload(B.col, cols); upload(B.shape, shapes); upload(B.glow, glows); }
      requestDraw();
    }
    function setLines(pr, lc) {
      pairs = pr; lineCols = lc;
      lineBuf = new Float32Array(pairs.length * 3);
      lineColBuf = new Float32Array(pairs.length * 4);
      for (let k = 0; k < pairs.length / 2; k++) for (let e = 0; e < 2; e++) lineColBuf.set(lineCols.subarray(k * 4, k * 4 + 4), (2 * k + e) * 4);
      if (hasGL) upload(B.lcol, lineColBuf);
      rebuildLines(); requestDraw();
    }
    function rebuildLines() {
      for (let v = 0; v < pairs.length; v++) {
        const i = pairs[v] * 3;
        lineBuf[v * 3] = cur[i]; lineBuf[v * 3 + 1] = cur[i + 1]; lineBuf[v * 3 + 2] = cur[i + 2];
      }
      if (hasGL) upload(B.lpos, lineBuf);
    }
    function setExtra(x) {
      extra = x && x.pos.length ? x : null;
      if (extra && hasGL) { upload(B.xpos, extra.pos, gl.STATIC_DRAW); upload(B.xcol, extra.col, gl.STATIC_DRAW); }
      requestDraw();
    }
    function setGlobe(g) {
      globe = g;
      if (g && hasGL) { // a latitude-longitude sphere, a little inside the drawn surface
        const LA = 36, LO = 72, v = [], idx = [], r = g.r * 0.992;
        for (let a = 0; a <= LA; a++) for (let b = 0; b <= LO; b++) {
          const th = a / LA * Math.PI, ph = b / LO * Math.PI * 2;
          v.push(g.c[0] + r * Math.sin(th) * Math.cos(ph), g.c[1] + r * Math.cos(th), g.c[2] + r * Math.sin(th) * Math.sin(ph));
        }
        for (let a = 0; a < LA; a++) for (let b = 0; b < LO; b++) {
          const p = a * (LO + 1) + b, q = p + LO + 1;
          idx.push(p, q, p + 1, p + 1, q, q + 1);
        }
        upload(B.globe, new Float32Array(v), gl.STATIC_DRAW);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, B.gidx); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(idx), gl.STATIC_DRAW);
        globeCount = idx.length;
      }
      requestDraw();
    }

    // -------------------------------------------------------------- camera
    function eye() {
      const c = Math.cos(cam.pitch);
      return [cam.target[0] + cam.dist * c * Math.sin(cam.yaw), cam.target[1] + cam.dist * Math.sin(cam.pitch),
        cam.target[2] + cam.dist * c * Math.cos(cam.yaw)];
    }
    function basis() {
      const e = eye();
      let fx = cam.target[0] - e[0], fy = cam.target[1] - e[1], fz = cam.target[2] - e[2];
      const l = Math.hypot(fx, fy, fz) || 1; fx /= l; fy /= l; fz /= l;
      let rx = -fz, ry = 0, rz = fx;
      const rl = Math.hypot(rx, rz) || 1; rx /= rl; rz /= rl;
      const ux = ry * fz - rz * fy, uy = rz * fx - rx * fz, uz = rx * fy - ry * fx;
      return { r: [rx, ry, rz], u: [ux, uy, uz], f: [fx, fy, fz] };
    }
    const clampPitch = (p) => Math.max(-1.5, Math.min(1.5, p));
    const clampDist = (d) => Math.max(60, Math.min(9000, d));
    function flyTo(goal, dur) {
      spin = null;
      const g = { target: goal.target || cam.target.slice(), dist: clampDist(goal.dist || cam.dist),
        yaw: goal.yaw === undefined ? cam.yaw : goal.yaw, pitch: goal.pitch === undefined ? cam.pitch : clampPitch(goal.pitch) };
      while (g.yaw - cam.yaw > Math.PI) g.yaw -= 2 * Math.PI;
      while (g.yaw - cam.yaw < -Math.PI) g.yaw += 2 * Math.PI;
      if (reduced || dur === 0) { Object.assign(cam, g); fly = null; sortDirty = true; requestDraw(); return; }
      fly = { a: { target: cam.target.slice(), dist: cam.dist, yaw: cam.yaw, pitch: cam.pitch }, b: g, t0: performance.now(), dur: dur || 1100 };
      requestDraw();
    }

    // -------------------------------------------------------------- frame
    let raf = 0, lastFrame = 0, perfMs = 0, perfFps = 0;
    function requestDraw() { if (!raf) raf = requestAnimationFrame(frame); }
    function resize() {
      DPR = Math.min(window.devicePixelRatio || 1, 2);
      const r = ovCanvas.getBoundingClientRect();
      W = Math.max(1, r.width); H = Math.max(1, r.height);
      for (const c of [glCanvas, ovCanvas, cvCanvas]) { c.width = Math.round(W * DPR); c.height = Math.round(H * DPR); }
      requestDraw();
    }
    function frame(now) {
      raf = 0;
      let again = false;
      if (fly) {
        const t = Math.min(1, (now - fly.t0) / fly.dur), k = ease(t);
        for (let j = 0; j < 3; j++) cam.target[j] = fly.a.target[j] + (fly.b.target[j] - fly.a.target[j]) * k;
        cam.dist = Math.exp(Math.log(fly.a.dist) + (Math.log(fly.b.dist) - Math.log(fly.a.dist)) * k);
        cam.yaw = fly.a.yaw + (fly.b.yaw - fly.a.yaw) * k;
        cam.pitch = fly.a.pitch + (fly.b.pitch - fly.a.pitch) * k;
        sortDirty = true;
        if (t >= 1) fly = null; else again = true;
      }
      if (spin) { // a flick keeps turning, slowing down
        cam.yaw -= spin.yaw; cam.pitch = clampPitch(cam.pitch + spin.pitch);
        spin.yaw *= 0.94; spin.pitch *= 0.94; sortDirty = true;
        if (Math.abs(spin.yaw) + Math.abs(spin.pitch) < 0.0004) spin = null; else again = true;
      }
      if (morph) {
        const t = Math.min(1, (now - morph.t0) / morph.dur), k = ease(t);
        for (let i = 0; i < cur.length; i++) cur[i] = from[i] + (to[i] - from[i]) * k;
        if (hasGL) upload(B.pos, cur);
        rebuildLines(); sortDirty = true;
        if (t >= 1) morph = null; else again = true;
      }
      if (ripples.length) again = true;
      if (api.tick && api.tick(now)) again = true;
      const t0 = performance.now();
      draw(now);
      perfMs = performance.now() - t0;
      if (again && lastFrame) perfFps = 1000 / Math.max(1, now - lastFrame);
      lastFrame = again ? now : 0;
      if (api.onPerf) api.onPerf(perfMs, again ? perfFps : 0, mode, n + opt.tests);
      if (again) raf = requestAnimationFrame(frame);
    }
    function projection() {
      const fw = Math.max(1, W - inset.l - inset.r), fh = Math.max(1, H - inset.t - inset.b);
      const sx = fw / W, sy = fh / H;
      const cx = (inset.l + fw / 2) / W * 2 - 1, cy = 1 - (inset.t + fh / 2) / H * 2;
      return { T: [sx, 0, 0, 0, 0, sy, 0, 0, 0, 0, 1, 0, cx, cy, 0, 1], aspect: fw / fh };
    }
    let mvpSky = null;
    function computeMVP() {
      const pr = projection();
      const proj = perspective(0.8, pr.aspect, Math.max(1, cam.dist * 0.02), cam.dist * 6 + 4000);
      mvp = mul(pr.T, mul(proj, lookAt(eye(), cam.target, [0, 1, 0])));
      const b = basis();
      mvpSky = mul(pr.T, mul(perspective(0.8, pr.aspect, 1, 5000), lookAt([0, 0, 0], b.f, [0, 1, 0])));
    }
    function project() {
      const m = mvp;
      for (let i = 0; i < n; i++) {
        const x = cur[3 * i], y = cur[3 * i + 1], z = cur[3 * i + 2];
        const w = m[3] * x + m[7] * y + m[11] * z + m[15];
        SW[i] = w;
        if (w <= 1) { SX[i] = -1e6; SY[i] = -1e6; continue; }
        SX[i] = ((m[0] * x + m[4] * y + m[8] * z + m[12]) / w * 0.5 + 0.5) * W;
        SY[i] = (1 - ((m[1] * x + m[5] * y + m[9] * z + m[13]) / w * 0.5 + 0.5)) * H;
        depth[i] = w;
      }
    }
    function projectWith(m, p) {
      const w = m[3] * p[0] + m[7] * p[1] + m[11] * p[2] + m[15];
      if (w <= 1e-3) return null;
      return [((m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12]) / w * 0.5 + 0.5) * W,
        (1 - ((m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13]) / w * 0.5 + 0.5)) * H, w];
    }
    const projectPoint = (p) => { const r = projectWith(mvp, p); return r && r[2] > 1 ? r : null; };
    const scale = () => 7600 * Math.max(0.7, Math.min(1.4, H / 820));
    const pointSize = (w, i) => Math.max(3.2, Math.min(i !== undefined && cols[4 * i + 3] < 0.5 ? 7 : 24, scale() / Math.max(w, 1)));
    function behindGlobe(x, y, z) { // on the globe's far side, seen from the camera
      if (!globe) return false;
      const e = eye(), c = globe.c;
      const nx = x - c[0], ny = y - c[1], nz = z - c[2];
      return nx * (e[0] - x) + ny * (e[1] - y) + nz * (e[2] - z) < 0;
    }

    // stars that share a screen cell merge into one group until the camera comes closer
    function buildClusters() {
      clusters = [];
      drawCols = cols;
      if (!api.clusterOn || !api.clusterOn()) return;
      const cell = 30, grid = new Map();
      for (let i = 0; i < n; i++) {
        if (cols[4 * i + 3] < 0.5 || SW[i] <= 1 || (api.clusterable && !api.clusterable(i))) continue;
        if (SX[i] < 0 || SY[i] < 0 || SX[i] > W || SY[i] > H) continue;
        const key = Math.floor(SX[i] / cell) * 4096 + Math.floor(SY[i] / cell);
        let g = grid.get(key);
        if (!g) grid.set(key, g = []);
        g.push(i);
      }
      let hidden = null;
      for (const g of grid.values()) {
        if (g.length < 5) continue;
        if (!hidden) { hidden = new Float32Array(cols); }
        let x = 0, y = 0, X = 0, Y = 0, Z = 0;
        for (const i of g) { x += SX[i]; y += SY[i]; X += cur[3 * i]; Y += cur[3 * i + 1]; Z += cur[3 * i + 2]; hidden[4 * i + 3] = 0; }
        const k = g.length;
        clusters.push({ x: x / k, y: y / k, X: X / k, Y: Y / k, Z: Z / k, n: k, members: g });
      }
      if (hidden) drawCols = hidden;
    }

    function draw(now) {
      computeMVP();
      project();
      buildClusters();
      if (mode === "gl") drawGL(); else draw2D();
      drawOverlay(now);
    }
    function sortOrder() {
      if (!sortDirty) return;
      const o = Array.from(order);
      o.sort((a, b) => depth[b] - depth[a]);
      order.set(o);
      if (hasGL) { gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, B.idx); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, order, gl.DYNAMIC_DRAW); }
      sortDirty = false;
    }
    function drawGL() {
      sortOrder();
      gl.viewport(0, 0, glCanvas.width, glCanvas.height);
      const bg = api.background || [0.027, 0.039, 0.078];
      gl.clearColor(bg[0], bg[1], bg[2], 1);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      gl.disable(gl.DEPTH_TEST);
      const M = new Float32Array(mvp);
      // the distant scenery, behind everything
      if (opt.scenery) {
        gl.useProgram(PIN);
        gl.uniformMatrix4fv(UPIN.mvp, false, new Float32Array(mvpSky));
        gl.uniform1f(UPIN.size, 1.8 * DPR); gl.uniform4f(UPIN.col, 0.78, 0.82, 0.95, 0.42);
        gl.bindBuffer(gl.ARRAY_BUFFER, B.sky); gl.enableVertexAttribArray(APIN.pos); gl.vertexAttribPointer(APIN.pos, 3, gl.FLOAT, false, 0, 0);
        gl.drawArrays(gl.POINTS, 0, SKY_N);
        gl.disableVertexAttribArray(APIN.pos);
      }
      // the globe's body writes depth; what is behind it then fails the depth test
      if (globe && globeCount) {
        gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.depthMask(true);
        gl.useProgram(GLB);
        gl.uniformMatrix4fv(UG.mvp, false, M); gl.uniform3f(UG.c, 0.05, 0.11, 0.15);
        gl.bindBuffer(gl.ARRAY_BUFFER, B.globe); gl.enableVertexAttribArray(AG.pos); gl.vertexAttribPointer(AG.pos, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, B.gidx);
        gl.drawElements(gl.TRIANGLES, globeCount, gl.UNSIGNED_SHORT, 0);
        gl.disableVertexAttribArray(AG.pos);
        gl.depthMask(false);
      }
      // lines
      gl.useProgram(L);
      gl.uniformMatrix4fv(UL.mvp, false, M);
      const drawLines = (pb, cb, count) => {
        gl.bindBuffer(gl.ARRAY_BUFFER, pb); gl.enableVertexAttribArray(AL.pos); gl.vertexAttribPointer(AL.pos, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ARRAY_BUFFER, cb); gl.enableVertexAttribArray(AL.col); gl.vertexAttribPointer(AL.col, 4, gl.FLOAT, false, 0, 0);
        gl.drawArrays(gl.LINES, 0, count);
      };
      if (extra) drawLines(B.xpos, B.xcol, extra.pos.length / 3);
      if (pairs.length) drawLines(B.lpos, B.lcol, pairs.length);
      gl.disableVertexAttribArray(AL.pos); gl.disableVertexAttribArray(AL.col);
      // the test load
      if (opt.tests) {
        gl.useProgram(PIN);
        gl.uniformMatrix4fv(UPIN.mvp, false, M);
        gl.uniform1f(UPIN.size, 2.2 * DPR); gl.uniform4f(UPIN.col, 0.55, 0.64, 0.8, 0.55);
        gl.bindBuffer(gl.ARRAY_BUFFER, B.test); gl.enableVertexAttribArray(APIN.pos); gl.vertexAttribPointer(APIN.pos, 3, gl.FLOAT, false, 0, 0);
        gl.drawArrays(gl.POINTS, 0, opt.tests);
        gl.disableVertexAttribArray(APIN.pos);
      }
      // marks
      gl.useProgram(P);
      gl.uniformMatrix4fv(U.mvp, false, M);
      gl.uniform1f(U.scale, scale());
      gl.uniform1f(U.px, DPR);
      if (drawCols !== cols) upload(B.col, drawCols);
      const bind = (b, a, size) => { gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.enableVertexAttribArray(a); gl.vertexAttribPointer(a, size, gl.FLOAT, false, 0, 0); };
      bind(B.pos, A.pos, 3); bind(B.col, A.col, 4); bind(B.shape, A.shape, 1); bind(B.glow, A.glow, 1);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, B.idx);
      gl.drawElements(gl.POINTS, n, gl.UNSIGNED_SHORT, 0);
      for (const a of Object.values(A)) gl.disableVertexAttribArray(a);
      if (drawCols !== cols) upload(B.col, cols);
      gl.disable(gl.DEPTH_TEST);
    }

    // the same picture on a plain canvas: no shaders, simpler shapes
    function draw2D() {
      sortOrder();
      const g = c2;
      g.setTransform(DPR, 0, 0, DPR, 0, 0);
      const bg = api.background || [0.027, 0.039, 0.078];
      g.fillStyle = `rgb(${bg.map((x) => Math.round(x * 255)).join(",")})`;
      g.fillRect(0, 0, W, H);
      if (opt.scenery) {
        g.fillStyle = "rgba(200,210,240,0.4)";
        for (let k = 0; k < SKY_N; k++) { const p = projectWith(mvpSky, skyDirs.subarray(3 * k, 3 * k + 3)); if (p) g.fillRect(p[0], p[1], 1.2, 1.2); }
      }
      if (globe) {
        const c = projectPoint(globe.c), e = projectPoint([globe.c[0] + globe.r, globe.c[1], globe.c[2]]);
        if (c && e) {
          const b = basis(), edge = projectPoint([globe.c[0] + b.r[0] * globe.r, globe.c[1] + b.r[1] * globe.r, globe.c[2] + b.r[2] * globe.r]);
          const r = edge ? Math.hypot(edge[0] - c[0], edge[1] - c[1]) : Math.hypot(e[0] - c[0], e[1] - c[1]);
          g.fillStyle = "rgb(13,28,38)"; g.beginPath(); g.arc(c[0], c[1], r, 0, Math.PI * 2); g.fill();
        }
      }
      const seg = (pos, col, count) => {
        for (let v = 0; v + 1 < count; v += 2) {
          const a = pos.subarray(v * 3, v * 3 + 3), b = pos.subarray(v * 3 + 3, v * 3 + 6);
          if (globe && (behindGlobe(a[0], a[1], a[2]) || behindGlobe(b[0], b[1], b[2]))) continue;
          const p = projectPoint(a), q = projectPoint(b);
          if (!p || !q) continue;
          const al = col[v * 4 + 3];
          if (al <= 0) continue;
          g.strokeStyle = `rgba(${Math.round(col[v * 4] * 255)},${Math.round(col[v * 4 + 1] * 255)},${Math.round(col[v * 4 + 2] * 255)},${al})`;
          g.beginPath(); g.moveTo(p[0], p[1]); g.lineTo(q[0], q[1]); g.stroke();
        }
      };
      g.lineWidth = 1;
      if (extra) seg(extra.pos, extra.col, extra.pos.length / 3);
      if (pairs.length) seg(lineBuf, lineColBuf, pairs.length);
      if (opt.tests) {
        g.fillStyle = "rgba(140,163,204,0.55)";
        const lim = Math.min(opt.tests, 50000);
        for (let k = 0; k < lim; k++) { const p = projectPoint(testPos.subarray(3 * k, 3 * k + 3)); if (p) g.fillRect(p[0] - 1, p[1] - 1, 2, 2); }
      }
      for (let o = 0; o < n; o++) {
        const i = order[o], a = drawCols[4 * i + 3];
        if (a <= 0 || SW[i] <= 1) continue;
        if (globe && behindGlobe(cur[3 * i], cur[3 * i + 1], cur[3 * i + 2])) continue;
        const x = SX[i], y = SY[i];
        if (x < -30 || y < -30 || x > W + 30 || y > H + 30) continue;
        const r = pointSize(SW[i], i) / 2, sh = shapes[i] % 10, hollow = shapes[i] > 9.5;
        const col = `rgba(${Math.round(cols[4 * i] * 255)},${Math.round(cols[4 * i + 1] * 255)},${Math.round(cols[4 * i + 2] * 255)},${a})`;
        if (glows[i] > 0) { g.fillStyle = `rgba(${Math.round(cols[4 * i] * 255)},${Math.round(cols[4 * i + 1] * 255)},${Math.round(cols[4 * i + 2] * 255)},${0.18 * glows[i]})`; g.beginPath(); g.arc(x, y, r * 2.1, 0, 7); g.fill(); }
        g.beginPath();
        if (sh === 1) { for (let k = 0; k < 8; k++) { const an = k * Math.PI / 4 - Math.PI / 2, rr = k % 2 ? r * 0.3 : r * 1.1; g.lineTo(x + Math.cos(an) * rr, y + Math.sin(an) * rr); } g.closePath(); }
        else if (sh === 2) { g.moveTo(x, y - r); g.lineTo(x + r, y); g.lineTo(x, y + r); g.lineTo(x - r, y); g.closePath(); }
        else if (sh === 4) { g.moveTo(x, y - r); g.lineTo(x + r, y + r * 0.7); g.lineTo(x - r, y + r * 0.7); g.closePath(); }
        else g.arc(x, y, r * (sh === 3 ? 0.8 : 0.62), 0, 7);
        if (sh === 5) { g.fillStyle = `rgba(26,23,22,${a})`; g.fill(); g.strokeStyle = `rgba(212,100,70,${a})`; g.lineWidth = 1.2; g.stroke(); }
        else if (hollow || sh === 3) { g.strokeStyle = col; g.lineWidth = 1.3; g.stroke(); }
        else { g.fillStyle = col; g.fill(); }
      }
    }

    // -------------------------------------------------------------- overlay: light, names, markers
    const widths = new Map();
    function textWidth(s, font) {
      const k = font + "|" + s;
      let w = widths.get(k);
      if (w === undefined) { ctx.font = font; w = ctx.measureText(s).width; if (widths.size > 6000) widths.clear(); widths.set(k, w); }
      return w;
    }
    let placed = [], lightScreen = null;
    function drawLight() {
      const lp = api.lightPos ? api.lightPos(cur) : null;
      if (!lp) return;
      if (globe && behindGlobe(lp[0], lp[1], lp[2])) return;
      const p = projectPoint(lp);
      if (!p) return;
      const r = Math.max(10, Math.min(70, 26000 / p[2]));
      lightScreen = [p[0], p[1], r];
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      const g = ctx.createRadialGradient(p[0], p[1], 0, p[0], p[1], r * 2.6);
      g.addColorStop(0, "rgba(255,251,236,1)");
      g.addColorStop(0.12, "rgba(255,236,190,0.95)");
      g.addColorStop(0.35, "rgba(233,190,104,0.35)");
      g.addColorStop(1, "rgba(233,190,104,0)");
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(p[0], p[1], r * 2.6, 0, Math.PI * 2); ctx.fill();
      // eight rays: two squares turned by 45 degrees, the geometry of an eight-pointed star
      ctx.lineCap = "round";
      for (let k = 0; k < 8; k++) {
        const a = k * Math.PI / 4 + Math.PI / 8, len = r * (k % 2 ? 2.1 : 3.0);
        const lg = ctx.createLinearGradient(p[0], p[1], p[0] + Math.cos(a) * len, p[1] + Math.sin(a) * len);
        lg.addColorStop(0, "rgba(255,244,214,0.9)"); lg.addColorStop(1, "rgba(255,244,214,0)");
        ctx.strokeStyle = lg; ctx.lineWidth = Math.max(1, r / 14);
        ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(p[0] + Math.cos(a) * len, p[1] + Math.sin(a) * len); ctx.stroke();
      }
      ctx.restore();
      if (api.lightLabel) {
        const s = api.lightLabel(), font = `600 ${Math.round(Math.max(13, Math.min(18, r / 2.2)))}px ${api.fontName}`;
        ctx.font = font; ctx.textAlign = "center"; ctx.textBaseline = "top";
        ctx.lineWidth = 4; ctx.strokeStyle = "rgba(7,10,20,0.85)"; ctx.fillStyle = "#fff4d6";
        ctx.strokeText(s, p[0], p[1] + r * 1.15); ctx.fillText(s, p[0], p[1] + r * 1.15);
        placed.push([p[0] - textWidth(s, font) / 2, p[1] + r * 1.15, textWidth(s, font), 20]);
      }
    }
    const overlaps = (r) => placed.some((q) => r[0] < q[0] + q[2] && r[0] + r[2] > q[0] && r[1] < q[1] + q[3] && r[1] + r[3] > q[1]);
    function drawOverlay(now) {
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
      ctx.clearRect(0, 0, W, H);
      placed = []; lightScreen = null;
      const hiddenNow = (i) => drawCols[4 * i + 3] <= 0 || (globe && behindGlobe(cur[3 * i], cur[3 * i + 1], cur[3 * i + 2]));
      const view = { W, H, project: projectPoint, sx: SX, sy: SY, sw: SW, size: pointSize, cur, cam, ctx, hidden: hiddenNow, behindGlobe };
      if (api.underlay) api.underlay(ctx, view);
      drawLight();
      // groups of stars: a ring with a count, every ring the same size
      if (clusters.length) {
        ctx.save();
        ctx.font = `600 11px ${api.fontName}`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
        for (const c of clusters) {
          ctx.fillStyle = "rgba(14,20,38,0.85)"; ctx.strokeStyle = "rgba(220,232,255,0.75)"; ctx.lineWidth = 1.3;
          ctx.beginPath(); ctx.arc(c.x, c.y, 12, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
          ctx.fillStyle = "#dce8ff"; ctx.fillText(c.n > 999 ? Math.round(c.n / 100) / 10 + "k" : String(c.n), c.x, c.y + 0.5);
        }
        ctx.restore();
      }
      if (api.overlay) api.overlay(ctx, view);
      const labels = api.labels ? api.labels(view) : [];
      labels.sort((a, b) => b.pri - a.pri);
      let count = 0;
      for (const Lb of labels) {
        const i = Lb.i, x = SX[i], y = SY[i];
        if (x < -50 || y < -20 || x > W + 50 || y > H + 20 || hiddenNow(i)) continue;
        const font = Lb.font || `${Lb.bold ? 600 : 500} ${Lb.size || 12.5}px ${api.fontName}`;
        const w = textWidth(Lb.text, font), off = pointSize(SW[i], i) / 2 + 4;
        const r = [x + off, y - 8, w, 16];
        if (Lb.rtl) r[0] = x - off - w;
        if (!Lb.force && overlaps(r)) continue;
        placed.push(r);
        ctx.font = font; ctx.textAlign = "left"; ctx.textBaseline = "middle";
        ctx.lineWidth = 3.5; ctx.strokeStyle = "rgba(7,10,20,0.88)"; ctx.lineJoin = "round";
        ctx.strokeText(Lb.text, r[0], y); ctx.fillStyle = Lb.color || "#ece6d6"; ctx.fillText(Lb.text, r[0], y);
        if (++count > (Lb.max || 70)) break;
      }
      // a tap answers with a ring
      ripples = ripples.filter((rp) => now - rp.t0 < 450);
      for (const rp of ripples) {
        const k = (now - rp.t0) / 450;
        ctx.strokeStyle = `rgba(255,241,204,${0.8 * (1 - k)})`; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(rp.x, rp.y, 8 + 22 * k, 0, Math.PI * 2); ctx.stroke();
      }
    }

    // -------------------------------------------------------------- picking
    function pick(x, y, touch) {
      const lim = touch ? 24 : 12;
      let best = -1, bd = lim;
      if (lightScreen && Math.hypot(x - lightScreen[0], y - lightScreen[1]) < Math.max(lightScreen[2], 14)) return api.lightIndex;
      for (let i = 0; i < n; i++) {
        if (drawCols[4 * i + 3] < 0.2 || SW[i] <= 1) continue;
        if (globe && behindGlobe(cur[3 * i], cur[3 * i + 1], cur[3 * i + 2])) continue;
        const d = Math.hypot(SX[i] - x, SY[i] - y) - pointSize(SW[i], i) / 2;
        if (d < bd) { bd = d; best = i; }
      }
      return best;
    }
    function pickCluster(x, y, touch) {
      const lim = touch ? 18 : 13;
      let best = null, bd = lim;
      for (const c of clusters) { const d = Math.hypot(c.x - x, c.y - y); if (d < bd) { bd = d; best = c; } }
      return best;
    }
    function pickLine(x, y, touch) { // the nearest drawn line: [a, b] or null
      const lim = touch ? 10 : 6;
      let best = null, bd = lim;
      for (let k = 0; k < pairs.length / 2; k++) {
        if (lineCols[4 * k + 3] < 0.1) continue;
        const a = pairs[2 * k], b = pairs[2 * k + 1];
        if (SW[a] <= 1 || SW[b] <= 1) continue;
        const ax = SX[a], ay = SY[a], bx = SX[b], by = SY[b];
        const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy || 1;
        const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / l2));
        const d = Math.hypot(ax + t * dx - x, ay + t * dy - y);
        if (d < bd) { bd = d; best = [a, b]; }
      }
      return best;
    }

    // -------------------------------------------------------------- input
    const pointers = new Map();
    let drag = null;
    ovCanvas.addEventListener("pointerdown", (e) => {
      ovCanvas.setPointerCapture(e.pointerId);
      pointers.set(e.pointerId, [e.offsetX, e.offsetY]);
      fly = null; spin = null;
      drag = { x: e.offsetX, y: e.offsetY, t: performance.now(), moved: 0, pan: e.button === 2 || e.shiftKey, touch: e.pointerType !== "mouse", vy: 0, vp: 0, lt: performance.now() };
      if (pointers.size === 2) {
        const [a, b] = [...pointers.values()];
        drag.pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), dist: cam.dist, mx: (a[0] + b[0]) / 2, my: (a[1] + b[1]) / 2 };
      }
    });
    ovCanvas.addEventListener("pointermove", (e) => {
      if (!drag) {
        if (e.pointerType === "mouse" && api.onHover) api.onHover(pick(e.offsetX, e.offsetY, false), e.offsetX, e.offsetY);
        return;
      }
      const prev = pointers.get(e.pointerId);
      if (!prev) return;
      pointers.set(e.pointerId, [e.offsetX, e.offsetY]);
      const dx = e.offsetX - prev[0], dy = e.offsetY - prev[1];
      drag.moved += Math.abs(dx) + Math.abs(dy);
      if (pointers.size >= 2 && drag.pinch) {
        const [a, b] = [...pointers.values()];
        const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
        cam.dist = clampDist(drag.pinch.dist * drag.pinch.d / Math.max(d, 1));
        const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
        panBy(mx - drag.pinch.mx, my - drag.pinch.my);
        drag.pinch.mx = mx; drag.pinch.my = my;
      } else if (drag.pan) panBy(dx, dy);
      else {
        const k = api.turnRate ? api.turnRate() : 0.0055;
        cam.yaw -= dx * k; cam.pitch = clampPitch(cam.pitch + dy * k);
        drag.vy = dx * k; drag.vp = dy * k; drag.lt = performance.now();
      }
      sortDirty = true; requestDraw();
    });
    function panBy(dx, dy) {
      const b = basis(), k = cam.dist * 0.0011;
      for (let j = 0; j < 3; j++) cam.target[j] += (-b.r[j] * dx + b.u[j] * dy) * k;
    }
    const end = (e) => {
      if (!drag) return;
      pointers.delete(e.pointerId);
      if (pointers.size === 0) {
        if (drag.moved < 7 && performance.now() - drag.t < 600 && !drag.pinch) {
          ripples.push({ x: e.offsetX, y: e.offsetY, t0: performance.now() });
          if (drag.touch && navigator.vibrate) { try { navigator.vibrate(12); } catch (err) { /* no vibration here */ } }
          const c = pickCluster(e.offsetX, e.offsetY, drag.touch);
          if (c && api.onCluster) api.onCluster(c);
          else {
            const i = pick(e.offsetX, e.offsetY, drag.touch);
            if (i < 0 && api.onLine) { const l = pickLine(e.offsetX, e.offsetY, drag.touch); if (l) { api.onLine(l); drag = null; requestDraw(); return; } }
            if (api.onTap) api.onTap(i, e.offsetX, e.offsetY);
          }
          requestDraw();
        } else if (!drag.pan && !drag.pinch && !reduced && performance.now() - drag.lt < 60 && Math.abs(drag.vy) + Math.abs(drag.vp) > 0.004) {
          spin = { yaw: drag.vy, pitch: drag.vp }; requestDraw();
        }
        drag = null;
      }
    };
    ovCanvas.addEventListener("pointerup", end);
    ovCanvas.addEventListener("pointercancel", end);
    ovCanvas.addEventListener("pointerleave", () => { if (!drag && api.onHover) api.onHover(-1); });
    ovCanvas.addEventListener("contextmenu", (e) => e.preventDefault());
    ovCanvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      fly = null; spin = null;
      cam.dist = clampDist(cam.dist * Math.exp(e.deltaY * (e.deltaMode ? 0.05 : 0.0012)));
      sortDirty = true; requestDraw();
    }, { passive: false });
    ovCanvas.addEventListener("dblclick", (e) => {
      const i = pick(e.offsetX, e.offsetY, false);
      if (i >= 0) flyToNode(i, 0.25); else flyTo({ dist: cam.dist * 0.6 }, 600);
    });
    ovCanvas.addEventListener("keydown", (e) => {
      const step = 0.12;
      let used = true;
      switch (e.key) {
        case "ArrowLeft": if (e.shiftKey) panBy(40, 0); else cam.yaw += step; break;
        case "ArrowRight": if (e.shiftKey) panBy(-40, 0); else cam.yaw -= step; break;
        case "ArrowUp": if (e.shiftKey) panBy(0, 40); else cam.pitch = clampPitch(cam.pitch + step); break;
        case "ArrowDown": if (e.shiftKey) panBy(0, -40); else cam.pitch = clampPitch(cam.pitch - step); break;
        case "+": case "=": cam.dist = clampDist(cam.dist * 0.8); break;
        case "-": case "_": cam.dist = clampDist(cam.dist * 1.25); break;
        case "0": if (api.onFit) api.onFit(); break;
        case "Enter": if (api.onTap) api.onTap(pick(W / 2, H / 2, true), W / 2, H / 2); break;
        default: used = false;
      }
      if (used) { e.preventDefault(); sortDirty = true; requestDraw(); }
    });

    function flyToNode(i, k, dur) {
      flyTo({ target: [cur[3 * i], cur[3 * i + 1], cur[3 * i + 2]], dist: k > 10 ? k : 2400 * (k || 0.3) }, dur);
    }
    function nodePos(i) { return [cur[3 * i], cur[3 * i + 1], cur[3 * i + 2]]; }
    function targetPos(i) { return morph ? [to[3 * i], to[3 * i + 1], to[3 * i + 2]] : nodePos(i); }
    function setMode(m) {
      if (m === "gl" && !hasGL) return false;
      mode = m; glCanvas.hidden = mode !== "gl"; cvCanvas.hidden = mode !== "2d";
      sortDirty = true; requestDraw();
      return true;
    }

    window.addEventListener("resize", resize);
    if (window.ResizeObserver) new ResizeObserver(resize).observe(ovCanvas);
    resize();

    return {
      setPositions, morphTo, setStyle, setLines, setExtra, setGlobe, flyTo, flyToNode, requestDraw, pick, nodePos, targetPos,
      camera: () => ({ target: cam.target.slice(), dist: cam.dist, yaw: cam.yaw, pitch: cam.pitch }),
      screen: (i) => [SX[i], SY[i], SW[i]], size: () => [W, H], isMoving: () => !!(fly || morph || spin),
      zoom: (k) => flyTo({ dist: cam.dist * k }, 300),
      setInset: (x) => { Object.assign(inset, x); sortDirty = true; requestDraw(); },
      nudge: (dyaw) => { if (!drag && !fly) { cam.yaw += dyaw; sortDirty = true; } },
      setScenery: (v) => { opt.scenery = v; requestDraw(); },
      setTestLoad, testCount: () => opt.tests,
      setMode, mode: () => mode, hasGL: () => hasGL,
    };
  };
})();
