/* Map (slice 10). Draws only what data.json gives: places at the coordinates their records
 * give, route segments along their recorded geometry, on land outlines from Natural Earth.
 * No tiles, no requests beyond data.json, no geocoding. Equirectangular projection, x scaled by
 * the cosine of the middle latitude of the plotted places; north is up. Marks keep their size
 * at every zoom; zooming redraws, the viewport scrolls natively (thumb, wheel, arrow keys).
 * The first activation of a mark shows its record in the panel; a second one opens its page. */
(function () {
  "use strict";
  var IX = window.IX;
  var app = document.getElementById("ix-app");
  if (!app || !IX) return;
  IX.load(app, function (data) { draw(app, data); });

  var KM_PER_DEGREE = 111.195;   /* one degree of latitude on a sphere of radius 6371 km */
  var SCALES = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000];
  var LEVELS = 8;                 /* zoom level k shows the region at 2^k times its fitted size */

  function draw(app, data) {
    var S = data.strings, places = data.places, bm = data.basemap;
    var segs = [];
    data.routes.forEach(function (r) { r.segments.forEach(function (s) { if (s.drawn) segs.push(s); }); });
    var focusById = IX.byId(data.focus);
    var W = bm.bbox[0], SO = bm.bbox[1], E = bm.bbox[2], N = bm.bbox[3];
    var lats = places.map(function (p) { return p.lat; });
    var lons = places.map(function (p) { return p.lon; });
    var lat0 = lats.length ? (Math.min.apply(null, lats) + Math.max.apply(null, lats)) / 2 : (SO + N) / 2;
    var kx = Math.cos(lat0 * Math.PI / 180);
    var worldW = (E - W) * kx, worldH = N - SO;

    var st0 = IX.readState();
    var allIds = {};
    places.forEach(function (p) { allIds[p.id] = p; });
    segs.forEach(function (s) { allIds[s.id] = s; });
    var years = data.years || {};
    var yv = parseInt(st0.year, 10);
    var state = {
      z: null, focus: focusById[st0.focus] ? st0.focus : "",
      year: isFinite(yv) && years.first !== null && yv >= years.first && yv <= years.last ? yv : null,
      sel: allIds[st0.sel] ? st0.sel : ""
    };
    var zoom = 1, base = 1, level = 0;

    /* ---------------------------------------------------------------- controls */
    var controls = IX.el("div", { class: "ix-controls" });
    var focus = IX.focusSelect(S, data.focus, state.focus, function (v) { state.focus = v; emphasis(); save(); });
    var year = years.first !== null && years.first !== undefined
      ? IX.yearControl(S, years.first, years.last, state.year, function (v) { state.year = v; emphasis(); save(); })
      : null;
    [focus.box, year ? year.box : null].forEach(function (n) { if (n) controls.appendChild(n); });
    var summary = IX.summary();

    /* ---------------------------------------------------------------- viewport, zoom buttons, layers */
    var zin = IX.el("button", { type: "button", text: "+", "aria-label": S["ix.ctl.zoom_in"], title: S["ix.ctl.zoom_in"] });
    var zout = IX.el("button", { type: "button", text: "−", "aria-label": S["ix.ctl.zoom_out"], title: S["ix.ctl.zoom_out"] });
    var zfit = IX.el("button", { type: "button", class: "wide", text: S["ix.ctl.zoom_fit"], title: S["ix.ctl.zoom_fit_long"] });
    var zall = IX.el("button", { type: "button", class: "wide", text: S["ix.ctl.zoom_region"], title: S["ix.ctl.zoom_region_long"] });
    var zoomBox = IX.el("div", { class: "map-zoom", role: "group", "aria-label": S["ix.ctl.zoom"] }, [zin, zout, zfit, zall]);
    var viewport = IX.el("div", { class: "map-viewport", tabindex: "0", role: "group", "aria-label": S["ix.map.chart_label"] });
    var svg = IX.svg("svg", { xmlns: "http://www.w3.org/2000/svg", focusable: "false" });
    var gLand = IX.svg("g", { "aria-hidden": "true" });
    var gSegs = IX.svg("g");
    var gMarks = IX.svg("g");
    svg.appendChild(gLand); svg.appendChild(gSegs); svg.appendChild(gMarks);
    viewport.appendChild(svg);
    var frame = IX.el("div", { class: "map-wrap" }, [viewport, zoomBox]);
    var zval = IX.el("output", { class: "map-zoom-value" });
    var scale = IX.el("span", { class: "map-scale", "aria-hidden": "true" });
    var toTl = IX.el("a", { href: "../timeline/", text: S["ix.ctl.to_timeline"] });
    var foot = IX.el("div", { class: "map-foot" }, [zval, scale, IX.el("span", { class: "map-attrib",
      text: IX.fmt(S["ix.map.attrib"], { source: bm.source.name, licence: bm.source.licence }) }), toTl]);
    var panel = IX.el("div", { class: "map-panel", role: "region", "aria-label": S["ix.map.panel_label"] },
      [IX.el("p", { class: "ix-nojs", text: S["ix.map.panel_empty"] })]);
    [controls, summary, frame, foot, panel].forEach(function (n) { app.appendChild(n); });

    var px = function (lon) { return (lon - W) * kx * zoom; };
    var py = function (lat) { return (N - lat) * zoom; };

    var markEls = {}, segEls = {};

    function drawAll() {
      var w = Math.round(worldW * zoom), h = Math.round(worldH * zoom);
      IX.set(svg, { width: w, height: h, viewBox: "0 0 " + w + " " + h });
      gLand.textContent = gSegs.textContent = gMarks.textContent = "";
      var d = bm.rings.map(function (ring) {
        return "M" + ring.map(function (p) { return px(p[0]).toFixed(1) + "," + py(p[1]).toFixed(1); }).join("L") + "Z";
      }).join("");
      gLand.appendChild(IX.svg("path", { class: "map-land", d: d }));
      segs.forEach(function (s) {
        var dd = "M" + s.line.map(function (p) { return px(p[0]).toFixed(1) + "," + py(p[1]).toFixed(1); }).join("L");
        var a = IX.svg("a", { class: "map-seg seg-" + s.confidence, href: s.href, "data-id": s.id }, [
          IX.svg("title", { text: s.title }), IX.svg("path", { class: "hit", d: dd }), IX.svg("path", { d: dd })]);
        wire(a, s.id);
        segEls[s.id] = a;
        gSegs.appendChild(a);
      });
      places.forEach(function (p) {
        var x = px(p.lon), y = py(p.lat);
        var label = IX.svg("text", { class: "mk-label", x: 11, y: 4, text: p.name });
        var a = IX.svg("a", { class: "mk", href: p.href, "data-id": p.id, transform: "translate(" + x.toFixed(1) + "," + y.toFixed(1) + ")" }, [
          IX.svg("title", { text: p.title }),
          IX.svg("circle", { class: "mk-hit", r: 13 }),
          IX.svg("use", { class: "mk-shape conf-" + p.confidence, href: "#ix-sym-" + p.basis, x: -8, y: -8, width: 16, height: 16 }),
          IX.svg("circle", { class: "mk-ring", r: 11 }),
          label]);
        wire(a, p.id);
        markEls[p.id] = { a: a, label: label, x: x, y: y };
        gMarks.appendChild(a);
      });
      labels();
      scaleBar();
      emphasis();
      highlight();
      zval.textContent = IX.fmt(S["ix.map.zoom_value"], { n: level + 1, max: LEVELS });
      zin.disabled = level >= LEVELS - 1;
      zout.disabled = level <= 0;
    }

    /* labels: east, west, north, south of the mark, the first that collides with nothing;
       a label that fits nowhere is hidden (the mark keeps its name in its title) */
    function labels() {
      var boxes = [];
      places.forEach(function (p) { var m = markEls[p.id]; boxes.push([m.x - 9, m.y - 9, m.x + 9, m.y + 9]); });
      var hit = function (b) {
        return boxes.some(function (o) { return b[0] < o[2] && b[2] > o[0] && b[1] < o[3] && b[3] > o[1]; });
      };
      places.forEach(function (p) {
        var m = markEls[p.id];
        var bb = m.label.getBBox ? m.label.getBBox() : { width: p.name.length * 7, height: 14 };
        var w = bb.width, h = bb.height || 14;
        var tries = [[11, 4, "start"], [-11, 4, "end"], [0, -13, "middle"], [0, 21, "middle"]];
        for (var i = 0; i < tries.length; i++) {
          var t = tries[i];
          var x0 = t[2] === "start" ? m.x + t[0] : t[2] === "end" ? m.x + t[0] - w : m.x - w / 2;
          var box = [x0 - 2, m.y + t[1] - h + 2, x0 + w + 2, m.y + t[1] + 4];
          if (!hit(box)) {
            IX.set(m.label, { x: t[0], y: t[1], "text-anchor": t[2] });
            m.label.classList.remove("is-hidden");
            boxes.push(box);
            return;
          }
        }
        m.label.classList.add("is-hidden");
      });
    }

    function scaleBar() {
      var kmPerPx = KM_PER_DEGREE / zoom;
      var km = SCALES[0];
      SCALES.forEach(function (s) { if (s / kmPerPx <= 120) km = s; });
      scale.textContent = "";
      var bar = IX.el("span", { class: "bar" });
      bar.style.setProperty(window.CSS && CSS.supports && CSS.supports("inline-size", "0") ? "inline-size" : "width",
        Math.round(km / kmPerPx) + "px");
      scale.appendChild(bar);
      scale.appendChild(IX.el("span", { class: "km", text: IX.fmt(S["ix.map.scale"], { km: km }) }));
    }

    /* ---------------------------------------------------------------- zoom */
    function center() {
      return [(viewport.scrollLeft + viewport.clientWidth / 2) / zoom / kx + W,
              N - (viewport.scrollTop + viewport.clientHeight / 2) / zoom];
    }
    function setLevel(k, c) {
      level = Math.max(0, Math.min(LEVELS - 1, k));
      zoom = base * Math.pow(2, level);
      drawAll();
      if (c) {
        viewport.scrollLeft = px(c[0]) - viewport.clientWidth / 2;
        viewport.scrollTop = py(c[1]) - viewport.clientHeight / 2;
      }
      save();
    }
    function fitLevel() {
      if (!places.length) return 0;
      var w = Math.max((Math.max.apply(null, lons) - Math.min.apply(null, lons)) * kx, 0.5) * 1.5;
      var h = Math.max(Math.max.apply(null, lats) - Math.min.apply(null, lats), 0.5) * 1.5;
      var vw = viewport.clientWidth || 320, vh = viewport.clientHeight || 320;
      var k = 0;
      while (k < LEVELS - 1 && w * base * Math.pow(2, k + 1) <= vw && h * base * Math.pow(2, k + 1) <= vh) k++;
      return k;
    }
    var placesCenter = places.length
      ? [(Math.min.apply(null, lons) + Math.max.apply(null, lons)) / 2, (Math.min.apply(null, lats) + Math.max.apply(null, lats)) / 2]
      : [(W + E) / 2, (SO + N) / 2];
    zin.addEventListener("click", function () { setLevel(level + 1, center()); });
    zout.addEventListener("click", function () { setLevel(level - 1, center()); });
    zfit.addEventListener("click", function () { setLevel(fitLevel(), placesCenter); });
    zall.addEventListener("click", function () { setLevel(0, [(W + E) / 2, (SO + N) / 2]); });
    viewport.addEventListener("keydown", function (ev) {
      if (ev.target !== viewport) return;
      if (ev.key === "+" || ev.key === "=") { setLevel(level + 1, center()); ev.preventDefault(); }
      if (ev.key === "-" || ev.key === "_") { setLevel(level - 1, center()); ev.preventDefault(); }
    });
    var scrollTimer = null;
    viewport.addEventListener("scroll", function () {
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(save, 200);
    });

    /* ---------------------------------------------------------------- selection */
    /* keyboard focus selects; a pointer selects on its first click or tap and opens the page on
       the second (a click also focuses the link, so focus from a pointer is ignored) */
    var pointer = false;
    function wire(a, id) {
      a.addEventListener("pointerdown", function () { pointer = true; });
      a.addEventListener("focus", function () { if (!pointer) select(id); });
      a.addEventListener("click", function (ev) {
        pointer = false;
        if (state.sel !== id) { ev.preventDefault(); select(id); }
      });
    }
    function select(id) {
      state.sel = id;
      highlight();
      var p = allIds[id];
      panel.textContent = "";
      if (!p) { panel.appendChild(IX.el("p", { class: "ix-nojs", text: S["ix.map.panel_empty"] })); save(); return; }
      if (p.lat !== undefined) {
        panel.appendChild(IX.el("h3", { html: p.name_html + (p.arabic_html ? " " + p.arabic_html : "") }));
      } else {
        panel.appendChild(IX.el("h3", { html: p.head_html }));
      }
      panel.appendChild(IX.el("div", { html: p.info_html }));
      var links = IX.el("p", {});
      if (p.lat !== undefined) {
        links.appendChild(IX.el("a", { class: "ix-btn", href: p.href, text: S["ix.map.open"] }));
        links.appendChild(document.createTextNode(" "));
        links.appendChild(IX.el("a", { href: "../timeline/#" + IX.stateString({ focus: p.entity }), text: S["ix.map.on_timeline"] }));
      } else {
        links.appendChild(IX.el("a", { href: p.href, text: S["ix.map.open_segment"] }));
      }
      panel.appendChild(links);
      save();
    }
    function highlight() {
      Object.keys(markEls).forEach(function (id) { markEls[id].a.classList.toggle("is-sel", id === state.sel); });
      Object.keys(segEls).forEach(function (id) { segEls[id].classList.toggle("is-sel", id === state.sel); });
      Array.prototype.forEach.call(document.querySelectorAll(".ix-alt > li[data-id]"), function (li) {
        li.classList.toggle("is-sel", li.getAttribute("data-id") === state.sel);
      });
    }

    /* ---------------------------------------------------------------- focus and year */
    function emphasis() {
      var f = state.focus ? focusById[state.focus] : null;
      var fset = {};
      if (f) f.items.forEach(function (id) { fset[id] = true; });
      var ys = state.year === null ? null : years.starts[state.year];
      var ye = state.year === null ? null : years.starts[state.year + 1];
      var nYear = 0, nFocus = 0;
      places.forEach(function (p) {
        var okF = !f || !!fset[p.id];
        var okY = ys === null || p.spans.some(function (s) { return s.start < ye && s.end > ys; });
        if (ys !== null && okY) nYear++;
        if (f && okF) nFocus++;
        var m = markEls[p.id];
        if (!m) return;
        m.a.classList.toggle("is-dim", !(okF && okY));
        m.a.classList.toggle("is-focus", !!f && okF);
      });
      segs.forEach(function (s) { if (segEls[s.id]) segEls[s.id].classList.toggle("is-dim", !!f || ys !== null); });
      var parts = [];
      if (f) parts.push(IX.fmt(S["ix.summary.focus_map"], { name: f.name, n: nFocus, total: places.length }));
      if (ys !== null) parts.push(IX.fmt(S["ix.summary.year_map"], { year: IX.fmt(S["ix.ctl.year_value"], { year: state.year }), n: nYear, total: places.length }));
      summary.textContent = parts.join(" ");
    }

    function save() {
      var c = center();
      IX.writeState({ z: level, c: c[0].toFixed(3) + "," + c[1].toFixed(3), focus: state.focus, year: state.year, sel: state.sel });
      var link = IX.stateString({ focus: state.focus, year: state.year });
      toTl.setAttribute("href", "../timeline/" + (link ? "#" + link : ""));
    }

    /* ---------------------------------------------------------------- start */
    base = (viewport.clientWidth || 320) / worldW;
    var z0 = parseInt(st0.z, 10);
    var c0 = (st0.c || "").split(",").map(parseFloat);
    var startCenter = c0.length === 2 && isFinite(c0[0]) && isFinite(c0[1]) ? c0 : placesCenter;
    setLevel(isFinite(z0) ? z0 : fitLevel(), startCenter);
    if (state.sel) select(state.sel);
    var lastW = viewport.clientWidth;
    var onResize = function () {
      if (!viewport.clientWidth || viewport.clientWidth === lastW) return;
      var c = center();
      lastW = viewport.clientWidth;
      base = lastW / worldW;
      setLevel(level, c);
    };
    if (window.ResizeObserver) new ResizeObserver(onResize).observe(viewport);
    else window.addEventListener("resize", onResize);
  }
}());
