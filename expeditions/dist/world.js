/* al-Marṣad Expeditions: the world. Present-day ground, the computed sky, gazetteer points, and nothing else.
   No person is ever drawn. Plain WebGL 1, no library; a flat relief or map where WebGL is missing.
   Every drawn element belongs to one provenance class, and the lens tints the ground and sky as computed. */
"use strict";
(function (root) {
  const rad = Math.PI / 180;
  const dirOf = (alt, az) => [Math.sin(az * rad) * Math.cos(alt * rad), Math.sin(alt * rad), -Math.cos(az * rad) * Math.cos(alt * rad)];
  const localTime = (ut, off) => { const [h, m] = ut.split(":").map(Number); const t = ((h * 60 + m + off) % 1440 + 1440) % 1440; return String(Math.floor(t / 60)).padStart(2, "0") + ":" + String(t % 60).padStart(2, "0"); };

  function heights(T) {
    const N = T.n, bin = atob(T.h), H = new Float32Array(N * N);
    for (let i = 0; i < N * N; i++) H[i] = (bin.charCodeAt(2 * i) | (bin.charCodeAt(2 * i + 1) << 8)) + T.base_m;
    return H;
  }

  /* -------- a flat map: land, points, a scale; also the route map -------- */
  function drawMap(cv, map, opts = {}) {
    const dpr = Math.min(2, window.devicePixelRatio || 1), w = cv.clientWidth, h = cv.clientHeight;
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    const x = cv.getContext("2d"); x.setTransform(dpr, 0, 0, dpr, 0, 0);
    let [W, S, E, N] = map.bbox;
    const k = Math.cos(((S + N) / 2) * rad);
    // keep the aspect true: widen the box to fit the canvas
    const bw = (E - W) * k, bh = N - S;
    if (bw / bh < w / h) { const add = (bh * w / h / k - (E - W)) / 2; W -= add; E += add; } else { const add = ((E - W) * k * h / w - bh) / 2; S -= add; N += add; }
    const P = (lon, lat) => [(lon - W) / (E - W) * w, (N - lat) / (N - S) * h];
    x.fillStyle = "#0c1730"; x.fillRect(0, 0, w, h);
    x.fillStyle = opts.lens ? "#24456e" : "#2a2a28"; x.strokeStyle = opts.lens ? "#6cb6ff" : "#4a4a44"; x.lineWidth = 1;
    for (const ring of map.land) {
      x.beginPath(); ring.forEach(([lo, la], i) => { const [px, py] = P(lo, la); i ? x.lineTo(px, py) : x.moveTo(px, py); }); x.closePath(); x.fill(); x.stroke();
    }
    // a 50 or 100 km scale bar
    const kmPerPx = (E - W) * 111.32 * k / w, len = kmPerPx * 120 > 150 ? 100 : 50;
    x.strokeStyle = "#a6b2c6"; x.fillStyle = "#a6b2c6"; x.lineWidth = 2; x.font = "12px system-ui, sans-serif";
    x.beginPath(); x.moveTo(14, h - 16); x.lineTo(14 + len / kmPerPx, h - 16); x.stroke(); x.fillText(len + " km (computed)", 14, h - 22);
    if (opts.route) {
      const pts = opts.route.filter(s => s.lat != null).map(s => P(s.lon, s.lat));
      x.setLineDash([5, 6]); x.strokeStyle = "#9aa3b5"; x.lineWidth = 1.5; x.beginPath();
      pts.forEach(([px, py], i) => i ? x.lineTo(px, py) : x.moveTo(px, py)); x.stroke(); x.setLineDash([]);
    }
    const placed = [];
    for (const p of map.points) {
      const [px, py0] = P(p.lon, p.lat);
      let py = py0;
      x.fillStyle = "#2cb98f"; x.beginPath(); x.arc(px, py0, p.big ? 6 : 4.5, 0, 7); x.fill();
      x.strokeStyle = "#0a0f1d"; x.lineWidth = 1.5; x.stroke();
      x.fillStyle = "#e8edf5"; x.font = (p.big ? "600 " : "") + "13px system-ui, sans-serif";
      const tw = x.measureText(p.name).width, right = px + 8 + tw < w - 6, lx = right ? px + 8 : px - 8 - tw;
      // nudge a label down until it clears the labels already drawn
      while (placed.some(q => lx < q[0] + q[2] && lx + tw > q[0] && Math.abs(py - q[1]) < 15)) py += 15;
      placed.push([lx, py, tw]);
      x.fillText(p.name, lx, py + 4);
    }
  }

  /* -------- the 3D world -------- */
  function World(host, X, stars, ui) {
    const T = X.world.terrain, N = T.n, S = T.size_km, EX = 2.5, H = heights(T);
    const hAt = (i, j) => H[Math.min(N - 1, Math.max(0, j)) * N + Math.min(N - 1, Math.max(0, i))];
    const yOf = h => (h - T.base_m) / 1000 * EX;
    const yC = yOf(hAt(N >> 1, N >> 1));
    const sky = X.sky && X.sky.candidates ? X.sky : null;
    const st = { c: sky ? Math.max(0, sky.candidates.findIndex(c => c.key === "tabular")) : 0, f: 0, yaw: -Math.PI / 2, pitch: 0.2, dist: 11, lens: false, view: "3d" };
    const ac = new AbortController(), on = (el, ev, fn, o) => el.addEventListener(ev, fn, Object.assign({ signal: ac.signal }, o || {}));

    host.innerHTML = "";
    const stage = document.createElement("div"); stage.className = "stage"; stage.dataset.prov = "computed"; stage.classList.add("no-badge");
    const cv = document.createElement("canvas"); cv.tabIndex = 0;
    cv.setAttribute("aria-label", `${X.world.anchor.name} on present-day terrain${sky ? ", under the computed sky" : ""}. Arrow keys look around, plus and minus zoom.`);
    const map = document.createElement("canvas"); map.className = "mapcv"; map.hidden = true; map.setAttribute("aria-label", "A flat map of the region with the gazetteer points");
    stage.append(cv, map);
    const tags = X.world.labels.map(l => { const t = document.createElement("div"); t.className = "tag"; t.dataset.prov = l.class; t.classList.add("no-badge"); stage.appendChild(t); return t; });
    const moonTag = document.createElement("div"); moonTag.className = "tag"; moonTag.dataset.prov = "computed"; moonTag.classList.add("no-badge"); stage.appendChild(moonTag);
    const tog = document.createElement("div"); tog.className = "viewtoggle seg"; tog.innerHTML = `<button aria-pressed="true" data-v="3d">3D</button><button aria-pressed="false" data-v="map">Map</button>`; stage.appendChild(tog);
    const hud = document.createElement("div"); hud.className = "hud";
    if (sky) {
      hud.innerHTML = `<span class="clock num" aria-live="off"></span><label class="sr-only" for="t-${X.slug}">Time</label><input id="t-${X.slug}" type="range" min="0" value="0">
        <span class="seg" role="group" aria-label="Which lunation">${sky.candidates.map((c, i) => `<button data-c="${i}" aria-pressed="${i === st.c}">${{ before: "Earlier", tabular: "Tabular", after: "Later" }[c.key]}</button>`).join("")}</span>`;
    } else {
      hud.innerHTML = `<span class="muted">No date in the text, so no sky. The ground only.</span>`;
    }
    stage.appendChild(hud); host.appendChild(stage);
    const note = document.createElement("p"); note.className = "muted"; note.hidden = true; note.textContent = "This device cannot draw the 3D view, so the map shows the same place."; host.appendChild(note);

    const gl = cv.getContext("webgl", { antialias: true });
    function setView(v) {
      st.view = v; tog.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", b.dataset.v === v));
      cv.hidden = v !== "3d"; map.hidden = v !== "map"; tags.concat(moonTag).forEach(t => t.hidden = v !== "3d");
      draw();
    }
    tog.querySelectorAll("button").forEach(b => on(b, "click", () => setView(b.dataset.v)));
    if (!gl) { note.hidden = false; tog.hidden = true; setTimeout(() => setView("map")); }

    let draw3d = () => {};
    if (gl) {
      const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
      const prog = (vs, fs) => { const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p); return p; };
      const terrainP = prog(`attribute vec3 p; attribute vec3 n; uniform mat4 m; varying vec3 vn; varying float vh; varying vec3 vp;
        void main(){ vn=n; vh=p.y; vp=p; gl_Position=m*vec4(p,1.0); }`,
        `precision mediump float; varying vec3 vn; varying float vh; varying vec3 vp;
        uniform vec3 moon; uniform float moonI; uniform vec3 sun; uniform float sunI; uniform float lens; uniform vec3 eye; uniform vec3 fog;
        void main(){ vec3 n=normalize(vn);
          vec3 base=mix(vec3(0.6,0.49,0.34),vec3(0.43,0.36,0.29),clamp(vh/2.0,0.0,1.0));
          float ml=max(dot(n,moon),0.0)*moonI, sl=max(dot(n,sun),0.0)*sunI;
          vec3 c=base*(0.06+ml*1.15*vec3(0.74,0.82,1.0)+sl*1.05*vec3(1.0,0.9,0.75)+sunI*0.35);
          if(lens>0.5){ float k=abs(fract(vh*6.0)-0.5); c=mix(c,vec3(0.42,0.71,1.0)*(0.35+ml+sl),0.55); if(k<0.04) c+=vec3(0.25,0.4,0.6); }
          float d=length(vp-eye); c=mix(c,fog,clamp((d-8.0)/40.0,0.0,0.7)); gl_FragColor=vec4(c,1.0); }`);
      const pointP = prog(`attribute vec3 p; attribute vec2 a; uniform mat4 m; uniform float dpr; varying float va; varying float vk;
        void main(){ gl_Position=m*vec4(p,1.0); gl_PointSize=a.x*dpr; va=a.y; vk=a.x; }`,
        `precision mediump float; varying float va; varying float vk; uniform vec3 tint;
        void main(){ vec2 q=gl_PointCoord-0.5; float r=length(q); if(r>0.5) discard;
          float f = vk>12.0 ? smoothstep(0.5,0.44,r) : smoothstep(0.5,0.0,r); gl_FragColor=vec4(tint*f*va,1.0); }`);
      const pos = new Float32Array(N * N * 3), nor = new Float32Array(N * N * 3), cell = S / (N - 1);
      for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
        const k = (j * N + i) * 3;
        pos[k] = (i / (N - 1) - 0.5) * S; pos[k + 1] = yOf(hAt(i, j)); pos[k + 2] = (j / (N - 1) - 0.5) * S;
        const dx = (yOf(hAt(i + 1, j)) - yOf(hAt(i - 1, j))) / (2 * cell), dz = (yOf(hAt(i, j + 1)) - yOf(hAt(i, j - 1))) / (2 * cell), l = Math.hypot(dx, 1, dz);
        nor[k] = -dx / l; nor[k + 1] = 1 / l; nor[k + 2] = -dz / l;
      }
      const idx = new Uint16Array((N - 1) * (N - 1) * 6); let q = 0;
      for (let j = 0; j < N - 1; j++) for (let i = 0; i < N - 1; i++) { const a = j * N + i; idx.set([a, a + N, a + 1, a + 1, a + N, a + N + 1], q); q += 6; }
      const buf = (d, t = gl.ARRAY_BUFFER) => { const b = gl.createBuffer(); gl.bindBuffer(t, b); gl.bufferData(t, d, gl.STATIC_DRAW); return b; };
      const bPos = buf(pos), bNor = buf(nor), bIdx = buf(idx, gl.ELEMENT_ARRAY_BUFFER);
      const sb = gl.createBuffer(), sa = gl.createBuffer(), mb = gl.createBuffer(), ma = gl.createBuffer();
      const persp = (fov, asp, n, f) => { const t = 1 / Math.tan(fov / 2); return [t / asp, 0, 0, 0, 0, t, 0, 0, 0, 0, (f + n) / (n - f), -1, 0, 0, 2 * f * n / (n - f), 0]; };
      const mul = (a, b) => { const o = new Array(16).fill(0); for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) for (let k = 0; k < 4; k++) o[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k]; return o; };
      const look = (e, t) => {
        let z = [e[0] - t[0], e[1] - t[1], e[2] - t[2]]; const zl = Math.hypot(...z); z = z.map(v => v / zl);
        let x = [z[2], 0, -z[0]]; const xl = Math.hypot(...x) || 1; x = x.map(v => v / xl);
        const y = [z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]];
        return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -(x[0] * e[0] + x[1] * e[1] + x[2] * e[2]), -(y[0] * e[0] + y[1] * e[1] + y[2] * e[2]), -(z[0] * e[0] + z[1] * e[1] + z[2] * e[2]), 1];
      };
      const proj = (m, v) => { const x = m[0] * v[0] + m[4] * v[1] + m[8] * v[2] + m[12], y = m[1] * v[0] + m[5] * v[1] + m[9] * v[2] + m[13], w = m[3] * v[0] + m[7] * v[1] + m[11] * v[2] + m[15]; return w <= 0 ? null : [x / w, y / w]; };
      const lat = X.world.anchor.lat * rad;
      draw3d = () => {
        const dpr = Math.min(2, window.devicePixelRatio || 1), r = cv.getBoundingClientRect();
        cv.width = Math.max(1, Math.round(r.width * dpr)); cv.height = Math.max(1, Math.round(r.height * dpr));
        gl.viewport(0, 0, cv.width, cv.height);
        const fr = sky ? sky.candidates[st.c].frames[st.f] : { moon: [-30, 0], sun: [45, 160], lst: 0 };
        const sunAlt = fr.sun[0], tw = Math.min(1, Math.max(0, (sunAlt + 12) / 18)), dark = Math.min(1, Math.max(0, (-sunAlt - 4) / 12));
        const fog = [0.015 + 0.3 * tw, 0.02 + 0.38 * tw, 0.045 + 0.55 * tw];
        gl.clearColor(...fog, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
        const target = [0, yC, 0], eye = [st.dist * Math.cos(st.pitch) * Math.sin(st.yaw), yC + st.dist * Math.sin(st.pitch), st.dist * Math.cos(st.pitch) * Math.cos(st.yaw)];
        const P4 = persp(55 * rad, cv.width / cv.height, 0.05, 200), V = look(eye, target), VR = V.slice(); VR[12] = VR[13] = VR[14] = 0;
        const MVP = mul(P4, V), SKY = mul(P4, VR);
        const md = dirOf(fr.moon[0], fr.moon[1]), sd = dirOf(fr.sun[0], fr.sun[1]);
        const ill = sky ? sky.candidates[st.c].moon_illuminated_pct / 100 : 0;
        gl.useProgram(pointP);
        const pl = gl.getAttribLocation(pointP, "p"), al = gl.getAttribLocation(pointP, "a");
        gl.uniformMatrix4fv(gl.getUniformLocation(pointP, "m"), false, SKY); gl.uniform1f(gl.getUniformLocation(pointP, "dpr"), dpr);
        gl.disable(gl.DEPTH_TEST); gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE);
        if (sky && dark > 0) {
          const p = [], a = [], moonGlow = fr.moon[0] > 0 ? 0.55 : 1;
          for (const [ra, dec, mag] of stars) {
            const ha = (fr.lst - ra) * rad, d = dec * rad;
            const alt = Math.asin(Math.sin(lat) * Math.sin(d) + Math.cos(lat) * Math.cos(d) * Math.cos(ha));
            if (alt < -0.02) continue;
            const az = Math.atan2(-Math.sin(ha) * Math.cos(d), Math.cos(lat) * Math.sin(d) - Math.sin(lat) * Math.cos(d) * Math.cos(ha));
            const v = dirOf(alt / rad, az / rad); p.push(v[0] * 90, v[1] * 90, v[2] * 90);
            a.push(Math.max(1.8, (5.8 - mag) * 1.5), Math.min(1, Math.pow(2.512, -(mag - 1.6)) * 1.6 + 0.2) * dark * Math.min(1, alt / (8 * rad) + 0.25) * moonGlow);
          }
          gl.uniform3fv(gl.getUniformLocation(pointP, "tint"), st.lens ? [0.55, 0.78, 1] : [1, 0.97, 0.9]);
          gl.enableVertexAttribArray(pl); gl.enableVertexAttribArray(al);
          gl.bindBuffer(gl.ARRAY_BUFFER, sb); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(p), gl.DYNAMIC_DRAW); gl.vertexAttribPointer(pl, 3, gl.FLOAT, false, 0, 0);
          gl.bindBuffer(gl.ARRAY_BUFFER, sa); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(a), gl.DYNAMIC_DRAW); gl.vertexAttribPointer(al, 2, gl.FLOAT, false, 0, 0);
          gl.drawArrays(gl.POINTS, 0, p.length / 3);
          gl.disableVertexAttribArray(al);
        }
        const bodies = [];
        if (sky && fr.moon[0] > -1) bodies.push([md, 26, Math.max(0.35, 1 - tw * 0.6), st.lens ? [0.55, 0.78, 1] : [1, 0.98, 0.9]]);
        if (fr.sun[0] > -1) bodies.push([sd, 34, 1, st.lens ? [0.6, 0.8, 1] : [1, 0.93, 0.7]]);
        for (const [dv, size, alpha, tint] of bodies) {
          gl.uniform3fv(gl.getUniformLocation(pointP, "tint"), tint);
          gl.enableVertexAttribArray(pl); gl.enableVertexAttribArray(al);
          gl.bindBuffer(gl.ARRAY_BUFFER, mb); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(dv.map(v => v * 90)), gl.DYNAMIC_DRAW); gl.vertexAttribPointer(pl, 3, gl.FLOAT, false, 0, 0);
          gl.bindBuffer(gl.ARRAY_BUFFER, ma); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([size, alpha]), gl.DYNAMIC_DRAW); gl.vertexAttribPointer(al, 2, gl.FLOAT, false, 0, 0);
          gl.drawArrays(gl.POINTS, 0, 1); gl.disableVertexAttribArray(al);
        }
        gl.disable(gl.BLEND); gl.enable(gl.DEPTH_TEST);
        gl.useProgram(terrainP);
        const tp = gl.getAttribLocation(terrainP, "p"), tn = gl.getAttribLocation(terrainP, "n");
        gl.uniformMatrix4fv(gl.getUniformLocation(terrainP, "m"), false, MVP);
        gl.uniform3fv(gl.getUniformLocation(terrainP, "moon"), md);
        gl.uniform1f(gl.getUniformLocation(terrainP, "moonI"), sky && fr.moon[0] > 0 ? ill * Math.min(1, fr.moon[0] / 6) * (1 - tw) : 0);
        gl.uniform3fv(gl.getUniformLocation(terrainP, "sun"), sd);
        gl.uniform1f(gl.getUniformLocation(terrainP, "sunI"), Math.max(0, Math.min(1, (sunAlt + 2) / 10)));
        gl.uniform1f(gl.getUniformLocation(terrainP, "lens"), st.lens ? 1 : 0);
        gl.uniform3fv(gl.getUniformLocation(terrainP, "eye"), eye); gl.uniform3fv(gl.getUniformLocation(terrainP, "fog"), fog);
        gl.bindBuffer(gl.ARRAY_BUFFER, bPos); gl.enableVertexAttribArray(tp); gl.vertexAttribPointer(tp, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ARRAY_BUFFER, bNor); gl.enableVertexAttribArray(tn); gl.vertexAttribPointer(tn, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, bIdx); gl.drawElements(gl.TRIANGLES, idx.length, gl.UNSIGNED_SHORT, 0);
        gl.disableVertexAttribArray(tn);
        const w = cv.clientWidth, h = cv.clientHeight;
        const place = (el, ndc) => { if (!ndc || Math.abs(ndc[0]) > 1.02 || Math.abs(ndc[1]) > 1.02) { el.style.visibility = "hidden"; return; } el.style.visibility = ""; el.style.left = ((ndc[0] + 1) / 2 * w) + "px"; el.style.top = ((1 - ndc[1]) / 2 * h - 6) + "px"; };
        X.world.labels.forEach((l, i) => {
          let x = l.x, z = l.z;
          if (!l.inside) { const r = S * 0.47; x = Math.sin(l.deg * rad) * r; z = -Math.cos(l.deg * rad) * r; }
          const gi = Math.round((x / S + 0.5) * (N - 1)), gj = Math.round((z / S + 0.5) * (N - 1));
          tags[i].textContent = l.inside ? l.name : `towards ${l.name}, ${Math.round(l.km)} km`;
          place(tags[i], proj(MVP, [x, yOf(hAt(gi, gj)) + 0.18, z]));
        });
        if (sky && fr.moon[0] > -1) { moonTag.textContent = `Moon ${Math.round(fr.moon[0])}° up`; place(moonTag, proj(SKY, md.map(v => v * 90))); } else moonTag.style.visibility = "hidden";
        if (sky) hud.querySelector(".clock").textContent = `${localTime(fr.ut, sky.candidates[st.c].local_offset_minutes)} local solar time`;
      };
      // looking: drag, pinch, wheel, keys
      let drag = null; const pts = new Map();
      on(cv, "pointerdown", e => { cv.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]); drag = [e.clientX, e.clientY]; });
      on(cv, "pointermove", e => {
        if (!pts.has(e.pointerId)) return;
        if (pts.size === 2) { const [a, b] = [...pts.values()], d0 = Math.hypot(a[0] - b[0], a[1] - b[1]); pts.set(e.pointerId, [e.clientX, e.clientY]); const [c, d] = [...pts.values()], d1 = Math.hypot(c[0] - d[0], c[1] - d[1]); st.dist = Math.min(30, Math.max(1.5, st.dist * d0 / (d1 || d0))); draw(); return; }
        pts.set(e.pointerId, [e.clientX, e.clientY]);
        st.yaw -= (e.clientX - drag[0]) * 0.006; st.pitch = Math.min(1.45, Math.max(0.02, st.pitch + (e.clientY - drag[1]) * 0.004)); drag = [e.clientX, e.clientY]; draw();
      });
      const up = e => pts.delete(e.pointerId); on(cv, "pointerup", up); on(cv, "pointercancel", up);
      on(cv, "wheel", e => { e.preventDefault(); st.dist = Math.min(30, Math.max(1.5, st.dist * Math.exp(e.deltaY * 0.001))); draw(); }, { passive: false });
      on(cv, "keydown", e => {
        const k = { ArrowLeft: () => st.yaw += 0.1, ArrowRight: () => st.yaw -= 0.1, ArrowUp: () => st.pitch = Math.min(1.45, st.pitch + 0.06), ArrowDown: () => st.pitch = Math.max(0.02, st.pitch - 0.06), "+": () => st.dist = Math.max(1.5, st.dist * 0.9), "-": () => st.dist = Math.min(30, st.dist * 1.1) }[e.key];
        if (k) { e.preventDefault(); k(); draw(); }
      });
    }
    const mapData = { bbox: X.world.map.bbox, land: X.world.map.land, points: X.world.map.points.map((p, i) => Object.assign({ big: i === 0 }, p)) };
    let pending = false;
    function draw() { if (pending) return; pending = true; requestAnimationFrame(() => { pending = false; if (st.view === "3d") draw3d(); else drawMap(map, mapData, { lens: st.lens }); }); }
    on(window, "resize", draw);

    // time and lunation
    function setCandidate(i) {
      st.c = i; const n = sky.candidates[i].frames.length, t = hud.querySelector("input");
      t.max = n - 1; if (st.f > n - 1) st.f = n - 1; t.value = st.f;
      hud.querySelectorAll("[data-c]").forEach(b => b.setAttribute("aria-pressed", +b.dataset.c === i));
      ui.onCandidate && ui.onCandidate(i); draw();
    }
    if (sky) {
      hud.querySelectorAll("[data-c]").forEach(b => on(b, "click", () => setCandidate(+b.dataset.c)));
      on(hud.querySelector("input"), "input", e => { st.f = +e.target.value; draw(); });
      // start where the scene's story starts
      const fs = sky.candidates[st.c].frames;
      let f0 = 0;
      if (sky.scene === "eve-to-noon") f0 = Math.max(0, fs.findIndex(f => f.moon[0] > 22));
      if (sky.scene === "night-after") f0 = Math.max(0, Math.round(fs.length / 3));
      if (sky.scene === "forenoon") { f0 = fs.length - 9; st.yaw = Math.PI * 0.75; st.pitch = 0.3; }
      st.f = f0; setCandidate(st.c);
    } else draw();

    return {
      get candidate() { return st.c; },
      setCandidate: i => sky && setCandidate(i),
      jumpTo(ut) {
        if (!sky) return;
        const m = s => { const [h, mi] = s.split(":").map(Number); return h * 60 + mi; }, target = m(ut);
        const fs = sky.candidates[st.c].frames; let best = 0, bd = 1e9;
        fs.forEach((f, i) => { const d = Math.abs(((m(f.ut) - target) % 1440 + 2160) % 1440 - 720); if (d < bd) { bd = d; best = i; } });
        st.f = best; hud.querySelector("input").value = best; draw();
      },
      lens(v) { st.lens = v; draw(); },
      destroy() { ac.abort(); },
    };
  }

  root.World = World;
  root.drawMap = drawMap;
})(window);
