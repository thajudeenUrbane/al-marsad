/* Sky Atlas renderer. WebGL draws the marks and lines; a 2D canvas on top draws the
   light, the names and the markers. The renderer knows nothing about the records: the
   page hands it positions, colours and shapes, and asks it what was tapped. */
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
  const FS_PTS = `
precision mediump float;
varying vec4 v_col; varying float v_shape; varying float v_glow; varying float v_size;
void main() {
  float g = v_glow > 0.0 ? 2.4 : 1.15;
  vec2 q = (gl_PointCoord * 2.0 - 1.0) * g;
  float ax = abs(q.x), ay = abs(q.y);
  float d;
  vec3 col = v_col.rgb;
  float rim = 0.0;
  if (v_shape < 0.5) d = length(q) - 0.62;
  else if (v_shape < 1.5) d = pow(ax, 0.55) + pow(ay, 0.55) - 0.95;
  else if (v_shape < 2.5) d = ax + ay - 0.82;
  else if (v_shape < 3.5) { float h = max(ax * 0.866 + ay * 0.5, ay); d = abs(h - 0.62) - 0.16; }
  else if (v_shape < 4.5) { vec2 t = vec2(ax, -q.y); d = max(t.x * 0.866 + t.y * 0.5, -t.y) - 0.42; }
  else { d = length(q) - 0.7; rim = smoothstep(0.28, 0.0, abs(length(q) - 0.62)); }
  float px = v_size * 0.5;
  float core = clamp(0.5 - d * px, 0.0, 1.0);
  float r = length(gl_PointCoord * 2.0 - 1.0);
  float halo = v_glow * 0.6 * pow(max(0.0, 1.0 - r), 2.2);
  if (v_shape > 4.5) col = mix(col, vec3(0.86, 0.38, 0.26), rim);
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
    const { glCanvas, ovCanvas, n, api } = opts;
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const gl = glCanvas.getContext("webgl", { antialias: true, premultipliedAlpha: true, alpha: false });
    if (!gl) throw new Error("webgl");
    const ctx = ovCanvas.getContext("2d");
    const P = compile(gl, VS_PTS, FS_PTS), L = compile(gl, VS_LN, FS_LN);
    const loc = (p, a) => gl.getAttribLocation(p, a), uni = (p, u) => gl.getUniformLocation(p, u);
    const A = { pos: loc(P, "a_pos"), col: loc(P, "a_col"), shape: loc(P, "a_shape"), glow: loc(P, "a_glow") };
    const U = { mvp: uni(P, "u_mvp"), scale: uni(P, "u_scale"), px: uni(P, "u_px") };
    const AL = { pos: loc(L, "a_pos"), col: loc(L, "a_col") }, UL = { mvp: uni(L, "u_mvp") };
    const buf = () => gl.createBuffer();
    const B = { pos: buf(), col: buf(), shape: buf(), glow: buf(), idx: buf(), lpos: buf(), lcol: buf(), xpos: buf(), xcol: buf() };

    const cur = new Float32Array(n * 3), from = new Float32Array(n * 3), to = new Float32Array(n * 3);
    let morph = null;                      // {t0, dur}
    let cols = new Float32Array(n * 4), shapes = new Float32Array(n), glows = new Float32Array(n);
    const order = new Uint16Array(n); for (let i = 0; i < n; i++) order[i] = i;
    const depth = new Float32Array(n);
    const SX = new Float32Array(n), SY = new Float32Array(n), SW = new Float32Array(n);
    let pairs = new Int32Array(0), lineCols = new Float32Array(0), lineBuf = new Float32Array(0), lineColBuf = new Float32Array(0);
    let extra = null;                      // {pos: Float32Array, col: Float32Array, alpha}
    let W = 1, H = 1, DPR = 1, mvp = null, dirty = true, sortDirty = true;

    const cam = { target: [0, 0, 0], dist: 2400, yaw: 0.6, pitch: 0.32 };
    // the part of the canvas the page's plates leave free: its centre is the view's centre
    const inset = { l: 0, r: 0, t: 0, b: 0 };
    let fly = null;

    // -------------------------------------------------------------- data in
    function upload(b, data, usage) { gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, data, usage || gl.DYNAMIC_DRAW); }
    function setPositions(p) { cur.set(p); morph = null; upload(B.pos, cur); rebuildLines(); sortDirty = true; requestDraw(); }
    function morphTo(p, dur) {
      if (reduced || !dur) { setPositions(p); return; }
      from.set(cur); to.set(p); morph = { t0: performance.now(), dur }; requestDraw();
    }
    function setStyle(c, s, g) {
      cols = c; shapes = s; glows = g;
      upload(B.col, cols); upload(B.shape, shapes); upload(B.glow, glows); requestDraw();
    }
    function setLines(pr, lc) {
      pairs = pr; lineCols = lc;
      lineBuf = new Float32Array(pairs.length * 3);
      lineColBuf = new Float32Array(pairs.length * 4);
      for (let k = 0; k < pairs.length / 2; k++) for (let e = 0; e < 2; e++) lineColBuf.set(lineCols.subarray(k * 4, k * 4 + 4), (2 * k + e) * 4);
      upload(B.lcol, lineColBuf); rebuildLines(); requestDraw();
    }
    function rebuildLines() {
      for (let v = 0; v < pairs.length; v++) {
        const i = pairs[v] * 3;
        lineBuf[v * 3] = cur[i]; lineBuf[v * 3 + 1] = cur[i + 1]; lineBuf[v * 3 + 2] = cur[i + 2];
      }
      upload(B.lpos, lineBuf);
    }
    function setExtra(x) {
      extra = x;
      if (x) { upload(B.xpos, x.pos, gl.STATIC_DRAW); upload(B.xcol, x.col, gl.STATIC_DRAW); }
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
      let rx = fz * 0 - fy * 0, ry = 0, rz = 0;
      rx = -fz; rz = fx; const rl = Math.hypot(rx, rz) || 1; rx /= rl; rz /= rl;
      const ux = ry * fz - rz * fy, uy = rz * fx - rx * fz, uz = rx * fy - ry * fx;
      return { r: [rx, ry, rz], u: [ux, uy, uz] };
    }
    const clampPitch = (p) => Math.max(-1.5, Math.min(1.5, p));
    const clampDist = (d) => Math.max(60, Math.min(9000, d));
    function flyTo(goal, dur) {
      const g = { target: goal.target || cam.target.slice(), dist: clampDist(goal.dist || cam.dist),
        yaw: goal.yaw === undefined ? cam.yaw : goal.yaw, pitch: goal.pitch === undefined ? cam.pitch : clampPitch(goal.pitch) };
      // turn the short way round
      while (g.yaw - cam.yaw > Math.PI) g.yaw -= 2 * Math.PI;
      while (g.yaw - cam.yaw < -Math.PI) g.yaw += 2 * Math.PI;
      if (reduced || dur === 0) { Object.assign(cam, g); fly = null; dirty = sortDirty = true; requestDraw(); return; }
      fly = { a: { target: cam.target.slice(), dist: cam.dist, yaw: cam.yaw, pitch: cam.pitch }, b: g, t0: performance.now(), dur: dur || 1100 };
      requestDraw();
    }

    // -------------------------------------------------------------- frame
    let raf = 0;
    function requestDraw() { dirty = true; if (!raf) raf = requestAnimationFrame(frame); }
    function resize() {
      DPR = Math.min(window.devicePixelRatio || 1, 2);
      const r = glCanvas.getBoundingClientRect();
      W = Math.max(1, r.width); H = Math.max(1, r.height);
      for (const c of [glCanvas, ovCanvas]) { c.width = Math.round(W * DPR); c.height = Math.round(H * DPR); }
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
      if (morph) {
        const t = Math.min(1, (now - morph.t0) / morph.dur), k = ease(t);
        for (let i = 0; i < cur.length; i++) cur[i] = from[i] + (to[i] - from[i]) * k;
        upload(B.pos, cur); rebuildLines(); sortDirty = true;
        if (t >= 1) morph = null; else again = true;
      }
      if (api.tick && api.tick(now)) again = true;
      draw();
      if (again) raf = requestAnimationFrame(frame);
    }
    function computeMVP() {
      const fw = Math.max(1, W - inset.l - inset.r), fh = Math.max(1, H - inset.t - inset.b);
      const proj = perspective(0.8, fw / fh, Math.max(1, cam.dist * 0.02), cam.dist * 6 + 4000);
      // scale the free area's projection to the canvas, then move its centre into place
      const sx = fw / W, sy = fh / H;
      const cx = (inset.l + fw / 2) / W * 2 - 1, cy = 1 - (inset.t + fh / 2) / H * 2;
      const T = [sx, 0, 0, 0, 0, sy, 0, 0, 0, 0, 1, 0, cx, cy, 0, 1];
      mvp = mul(T, mul(proj, lookAt(eye(), cam.target, [0, 1, 0])));
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
    function projectPoint(p) {
      const m = mvp, w = m[3] * p[0] + m[7] * p[1] + m[11] * p[2] + m[15];
      if (w <= 1) return null;
      return [((m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12]) / w * 0.5 + 0.5) * W,
        (1 - ((m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13]) / w * 0.5 + 0.5)) * H, w];
    }
    const pointSize = (w, i) => Math.max(3.2, Math.min(i !== undefined && cols[4 * i + 3] < 0.5 ? 7 : 24, scale() / Math.max(w, 1)));
    const scale = () => 7600 * Math.max(0.7, Math.min(1.4, H / 820));

    function draw() {
      computeMVP();
      project();
      if (sortDirty) {
        const o = Array.from(order);
        o.sort((a, b) => depth[b] - depth[a]);
        order.set(o);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, B.idx);
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, order, gl.DYNAMIC_DRAW);
        sortDirty = false;
      }
      gl.viewport(0, 0, glCanvas.width, glCanvas.height);
      const bg = api.background || [0.027, 0.039, 0.078];
      gl.clearColor(bg[0], bg[1], bg[2], 1);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      const M = new Float32Array(mvp);
      // lines
      gl.useProgram(L);
      gl.uniformMatrix4fv(UL.mvp, false, M);
      const drawLines = (pb, cb, count) => {
        gl.bindBuffer(gl.ARRAY_BUFFER, pb); gl.enableVertexAttribArray(AL.pos); gl.vertexAttribPointer(AL.pos, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ARRAY_BUFFER, cb); gl.enableVertexAttribArray(AL.col); gl.vertexAttribPointer(AL.col, 4, gl.FLOAT, false, 0, 0);
        gl.drawArrays(gl.LINES, 0, count);
      };
      if (extra && extra.pos.length) drawLines(B.xpos, B.xcol, extra.pos.length / 3);
      if (pairs.length) drawLines(B.lpos, B.lcol, pairs.length);
      gl.disableVertexAttribArray(AL.pos); gl.disableVertexAttribArray(AL.col);
      // marks
      gl.useProgram(P);
      gl.uniformMatrix4fv(U.mvp, false, M);
      gl.uniform1f(U.scale, scale());
      gl.uniform1f(U.px, DPR);
      const bind = (b, a, size) => { gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.enableVertexAttribArray(a); gl.vertexAttribPointer(a, size, gl.FLOAT, false, 0, 0); };
      bind(B.pos, A.pos, 3); bind(B.col, A.col, 4); bind(B.shape, A.shape, 1); bind(B.glow, A.glow, 1);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, B.idx);
      gl.drawElements(gl.POINTS, n, gl.UNSIGNED_SHORT, 0);
      for (const a of Object.values(A)) gl.disableVertexAttribArray(a);
      drawOverlay();
      dirty = false;
    }

    // -------------------------------------------------------------- overlay: light, names, markers
    const widths = new Map();
    function textWidth(s, font) {
      const k = font + "|" + s;
      let w = widths.get(k);
      if (w === undefined) { ctx.font = font; w = ctx.measureText(s).width; if (widths.size > 6000) widths.clear(); widths.set(k, w); }
      return w;
    }
    function drawLight() {
      const lp = api.lightPos ? api.lightPos(cur) : null;
      if (!lp) return;
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
    let placed = [], lightScreen = null;
    const overlaps = (r) => placed.some((q) => r[0] < q[0] + q[2] && r[0] + r[2] > q[0] && r[1] < q[1] + q[3] && r[1] + r[3] > q[1]);
    function drawOverlay() {
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
      ctx.clearRect(0, 0, W, H);
      placed = []; lightScreen = null;
      const view = { W, H, project: projectPoint, sx: SX, sy: SY, sw: SW, size: pointSize, cur, cam, ctx };
      if (api.underlay) api.underlay(ctx, view);
      drawLight();
      if (api.overlay) api.overlay(ctx, view);
      const labels = api.labels ? api.labels(view) : [];
      labels.sort((a, b) => b.pri - a.pri);
      let count = 0;
      for (const L of labels) {
        const i = L.i, x = SX[i], y = SY[i];
        if (x < -50 || y < -20 || x > W + 50 || y > H + 20) continue;
        const font = L.font || `${L.bold ? 600 : 500} ${L.size || 12.5}px ${api.fontName}`;
        const w = textWidth(L.text, font), off = pointSize(SW[i], i) / 2 + 4;
        const r = [x + off, y - 8, w, 16];
        if (L.rtl) r[0] = x - off - w;
        if (!L.force && overlaps(r)) continue;
        placed.push(r);
        ctx.font = font; ctx.textAlign = "left"; ctx.textBaseline = "middle";
        ctx.lineWidth = 3.5; ctx.strokeStyle = "rgba(7,10,20,0.88)"; ctx.lineJoin = "round";
        ctx.strokeText(L.text, r[0], y); ctx.fillStyle = L.color || "#ece6d6"; ctx.fillText(L.text, r[0], y);
        if (++count > (L.max || 70)) break;
      }
    }

    // -------------------------------------------------------------- picking
    function pick(x, y, touch) {
      const lim = touch ? 24 : 12;
      let best = -1, bd = lim;
      if (lightScreen && Math.hypot(x - lightScreen[0], y - lightScreen[1]) < Math.max(lightScreen[2], 14)) return api.lightIndex;
      for (let i = 0; i < n; i++) {
        if (cols[4 * i + 3] < 0.2 || SW[i] <= 1) continue;
        const d = Math.hypot(SX[i] - x, SY[i] - y) - pointSize(SW[i], i) / 2;
        if (d < bd) { bd = d; best = i; }
      }
      return best;
    }

    // -------------------------------------------------------------- input
    const pointers = new Map();
    let drag = null;
    ovCanvas.addEventListener("pointerdown", (e) => {
      ovCanvas.setPointerCapture(e.pointerId);
      pointers.set(e.pointerId, [e.offsetX, e.offsetY]);
      fly = null;
      drag = { x: e.offsetX, y: e.offsetY, t: performance.now(), moved: 0, pan: e.button === 2 || e.shiftKey, touch: e.pointerType !== "mouse" };
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
      else { cam.yaw -= dx * 0.0055; cam.pitch = clampPitch(cam.pitch + dy * 0.0055); }
      sortDirty = true; requestDraw();
      if (api.onCamera) api.onCamera();
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
          const i = pick(e.offsetX, e.offsetY, drag.touch);
          if (api.onTap) api.onTap(i, e.offsetX, e.offsetY);
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
      fly = null;
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

    window.addEventListener("resize", resize);
    if (window.ResizeObserver) new ResizeObserver(resize).observe(glCanvas);
    resize();

    return {
      setPositions, morphTo, setStyle, setLines, setExtra, flyTo, flyToNode, requestDraw, pick, nodePos, targetPos,
      camera: () => ({ target: cam.target.slice(), dist: cam.dist, yaw: cam.yaw, pitch: cam.pitch }),
      screen: (i) => [SX[i], SY[i], SW[i]], size: () => [W, H], isMoving: () => !!(fly || morph),
      zoom: (k) => flyTo({ dist: cam.dist * k }, 300),
      setInset: (x) => { Object.assign(inset, x); sortDirty = true; requestDraw(); },
      nudge: (dyaw) => { if (!drag && !fly) { cam.yaw += dyaw; sortDirty = true; } },
    };
  };
})();
