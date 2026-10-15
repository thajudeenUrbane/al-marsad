/* Timeline (slice 10). Draws every placed item of data.json as a bar from the earliest to the
 * latest date its record allows. Positions come only from the recorded bounds (Julian Day
 * Numbers worked out by the builder) and never move while the year cursor or the focus change;
 * only the window of years shown rescales them. Undated items are never drawn: the page lists
 * them under "Not placed". UI text comes from data.strings. */
(function () {
  "use strict";
  var IX = window.IX;
  var app = document.getElementById("ix-app");
  if (!app || !IX) return;
  IX.load(app, function (data) { draw(app, data); });

  var supports = function (prop) { return !!(window.CSS && CSS.supports && CSS.supports(prop, "0")); };
  var RTL = (document.documentElement.getAttribute("dir") || "ltr") === "rtl";
  var START = supports("inset-inline-start") ? "inset-inline-start" : (RTL ? "right" : "left");
  var SIZE = supports("inline-size") ? "inline-size" : "width";
  var STEPS = [1, 2, 5, 10, 20, 25, 50, 100, 200];

  function draw(app, data) {
    var S = data.strings, ax = data.axis, items = data.items;
    var byId = IX.byId(items);
    var focusById = IX.byId(data.focus);
    var yearStart = {};
    ax.ce.forEach(function (t) { yearStart[t.y] = t.x; });
    var clamp = function (v, dflt) {
      v = parseInt(v, 10);
      return isFinite(v) ? Math.max(ax.first_year, Math.min(ax.last_year, v)) : dflt;
    };
    var st0 = IX.readState();
    var state = {
      from: clamp(st0.from, ax.first_year), to: clamp(st0.to, ax.last_year),
      year: clamp(st0.year, null), focus: focusById[st0.focus] ? st0.focus : "",
      sel: byId[st0.sel] ? st0.sel : ""
    };
    if (state.from > state.to) { var sw = state.from; state.from = state.to; state.to = sw; }
    var narrowed = state.from !== ax.first_year || state.to !== ax.last_year;
    var yearText = function (y) { return IX.fmt(S["ix.ctl.year_value"], { year: y }); };

    /* ---------------------------------------------------------------- controls */
    var controls = IX.el("div", { class: "ix-controls" });
    var fromIn = IX.el("input", { id: "ix-from", type: "range", min: ax.first_year, max: ax.last_year, step: 1, value: state.from });
    var toIn = IX.el("input", { id: "ix-to", type: "range", min: ax.first_year, max: ax.last_year, step: 1, value: state.to });
    var fromOut = IX.el("output", { for: "ix-from" });
    var toOut = IX.el("output", { for: "ix-to" });
    var reset = IX.el("button", { type: "button", text: S["ix.ctl.reset"] });
    var winSummary = IX.el("summary", {});
    var win = IX.el("details", { class: "ix-window", open: narrowed }, [winSummary, IX.el("div", { class: "ix-window-body" },
      [IX.control(S["ix.ctl.from"], fromIn, fromOut), IX.control(S["ix.ctl.to"], toIn, toOut), reset])]);
    var year = IX.yearControl(S, ax.first_year, ax.last_year, state.year, function (v) { state.year = v; update(); });
    var focus = IX.focusSelect(S, data.focus, state.focus, function (v) { state.focus = v; update(); });
    var toMap = IX.el("a", { href: "../map/", text: S["ix.ctl.to_map"] });
    [year.box, focus.box, win].forEach(function (n) { controls.appendChild(n); });
    var summary = IX.summary();
    var cross = IX.el("p", { class: "ix-cross" }, [toMap]);

    fromIn.addEventListener("input", function () {
      state.from = parseInt(fromIn.value, 10);
      if (state.from > state.to) { state.to = state.from; toIn.value = state.to; }
      update();
    });
    toIn.addEventListener("input", function () {
      state.to = parseInt(toIn.value, 10);
      if (state.to < state.from) { state.from = state.to; fromIn.value = state.from; }
      update();
    });
    reset.addEventListener("click", function () {
      state.from = ax.first_year; state.to = ax.last_year; state.focus = "";
      fromIn.value = state.from; toIn.value = state.to; focus.input.value = "";
      year.set(null, true); state.year = null;
      update();
    });

    /* ---------------------------------------------------------------- chart */
    var chart = IX.el("div", { class: "tl-chart", role: "group", "aria-label": S["ix.tl.chart_label"] });
    var axisTrack = IX.el("div", { class: "tl-axis-track" });
    chart.appendChild(IX.el("div", { class: "tl-axis", "aria-hidden": "true" },
      [IX.el("div", { class: "tl-axis-label", text: S["ix.tl.axis_label"] }), axisTrack]));
    var rows = [];
    [["event", "ix.tl.band.events"], ["death", "ix.tl.band.deaths"]].forEach(function (band) {
      var list = items.filter(function (it) { return it.role === band[0]; });
      if (!list.length) return;
      var hid = "tl-band-" + band[0];
      chart.appendChild(IX.el("h3", { class: "tl-band", id: hid, text: IX.fmt(S[band[1]], { n: list.length }) }));
      var ol = IX.el("ol", { class: "tl-rows", "aria-labelledby": hid });
      list.forEach(function (it) { var r = row(it, rows.length); rows.push(r); ol.appendChild(r.li); });
      chart.appendChild(ol);
    });

    function row(it, i) {
      var li = IX.el("li", { class: "tl-row kind-" + it.kind, "data-id": it.id });
      var detId = "tl-d-" + i;
      var more = IX.el("button", { type: "button", class: "tl-more", "aria-expanded": "false", "aria-controls": detId,
        "aria-label": IX.fmt(S["ix.ctl.details_for"], { name: it.name }), title: S["ix.ctl.details"] });
      var label = IX.el("div", { class: "tl-label" }, [more, IX.el("div", { class: "tl-text" }, [
        IX.el("a", { class: "tl-name", href: it.href, html: it.name_html }),
        IX.el("span", { class: "tl-meta", html: [it.date_html, it.basis_text, it.status_html].filter(Boolean).join(" · ") })])]);
      var track = IX.el("div", { class: "tl-track", "aria-hidden": "true" });
      var whisker = it.conv ? IX.el("span", { class: "tl-whisker" }) : null;
      var bar = IX.el("a", { class: "tl-bar basis-" + it.basis + (it.disputed ? " is-disputed" : ""),
        href: it.href, tabindex: "-1", title: it.title });
      if (whisker) track.appendChild(whisker);
      track.appendChild(bar);
      var det = IX.el("div", { class: "tl-details", id: detId, hidden: true, html: it.info_html });
      li.appendChild(label); li.appendChild(track); li.appendChild(det);
      var r = { it: it, li: li, bar: bar, whisker: whisker, det: det, more: more };
      more.addEventListener("click", function () { toggle(r, more.getAttribute("aria-expanded") !== "true"); });
      return r;
    }

    function toggle(r, open) {
      r.more.setAttribute("aria-expanded", String(open));
      r.det.hidden = !open;
      if (open) state.sel = r.it.id;
      else if (state.sel === r.it.id) state.sel = "";
      rows.forEach(function (x) { x.li.classList.toggle("is-sel", x.it.id === state.sel); });
      save();
    }

    app.appendChild(controls);
    app.appendChild(summary);
    app.appendChild(cross);
    app.appendChild(chart);

    /* ---------------------------------------------------------------- scrub by pointer: tap or drag
       across any track or the axis to set the year cursor (vertical swipes still scroll) */
    var dragging = null;
    var yearAt = function (el, clientX) {
      var rect = el.getBoundingClientRect();
      if (!rect.width) return null;
      var frac = RTL ? (rect.right - clientX) / rect.width : (clientX - rect.left) / rect.width;
      var a = yearStart[state.from], b = yearStart[state.to + 1];
      var x = a + Math.max(0, Math.min(0.999999, frac)) * (b - a);
      for (var y = state.from; y <= state.to; y++) { if (x < yearStart[y + 1]) return y; }
      return state.to;
    };
    chart.addEventListener("pointerdown", function (ev) {
      if (ev.button > 0 || ev.target.closest(".tl-bar")) return;
      var tr = ev.target.closest(".tl-track, .tl-axis-track");
      if (!tr) return;
      dragging = tr;
      if (tr.setPointerCapture) { try { tr.setPointerCapture(ev.pointerId); } catch (e) { /* ignore */ } }
      var y = yearAt(tr, ev.clientX);
      if (y !== null) year.set(y);
    });
    chart.addEventListener("pointermove", function (ev) {
      if (!dragging) return;
      var y = yearAt(dragging, ev.clientX);
      if (y !== null && y !== state.year) year.set(y);
    });
    ["pointerup", "pointercancel", "lostpointercapture"].forEach(function (t) {
      chart.addEventListener(t, function () { dragging = null; });
    });

    /* ---------------------------------------------------------------- drawing */
    function pct(x, a, b) { return (x - a) / (b - a) * 100; }

    function place() {
      var a = yearStart[state.from], b = yearStart[state.to + 1];
      rows.forEach(function (r) {
        var it = r.it;
        var out = it.end <= a || it.start >= b;
        r.li.classList.toggle("is-out", out);
        if (out) return;
        var s = pct(it.start, a, b), e = pct(it.end, a, b);
        r.bar.style.setProperty(START, s + "%");
        r.bar.style.setProperty(SIZE, Math.max(e - s, 0) + "%");
        r.li.classList.toggle("tl-clip-start", s < 0);
        r.li.classList.toggle("tl-clip-end", e > 100);
        if (r.whisker) {
          var ws = pct(it.start - it.conv, a, b), we = pct(it.end + it.conv, a, b);
          r.whisker.style.setProperty(START, ws + "%");
          r.whisker.style.setProperty(SIZE, (we - ws) + "%");
        }
      });
      ticks(a, b);
      cursor(a, b);
    }

    function step(span, px) {
      for (var i = 0; i < STEPS.length; i++) { if (px / (span / STEPS[i]) >= 46) return STEPS[i]; }
      return STEPS[STEPS.length - 1];
    }

    function ticks(a, b) {
      axisTrack.textContent = "";
      var px = axisTrack.clientWidth || 320;
      var years = (b - a) / 365.25;
      /* the first label of each row carries its calendar: "610 CE", "1 AH" */
      var row = function (list, cls, every, name) {
        var first = true;
        list.forEach(function (t) {
          if (t.x < a || t.x >= b || (t.y % every && !(cls === "ah" && t.y === 1))) return;
          var n = IX.el("span", { class: "tl-tick " + cls, text: first ? t.y + " " + name : String(t.y) });
          n.style.setProperty(START, pct(t.x, a, b) + "%");
          axisTrack.appendChild(n);
          first = false;
        });
      };
      row(ax.ce, "ce", step(years, px), ax.ce_label);
      if (ax.ah && ax.ah.length) row(ax.ah, "ah", step(years * 1.0307, px), ax.ah_label);
    }

    function cursor(a, b) {
      if (state.year === null) { chart.classList.remove("has-cursor"); return; }
      var ys = yearStart[state.year], ye = yearStart[state.year + 1];
      chart.style.setProperty("--cur-start", pct(ys, a, b) + "%");
      chart.style.setProperty("--cur-size", (pct(ye, a, b) - pct(ys, a, b)) + "%");
      chart.classList.add("has-cursor");
    }

    function emphasis() {
      var f = state.focus ? focusById[state.focus] : null;
      var fset = {};
      if (f) f.items.forEach(function (id) { fset[id] = true; });
      var ys = state.year === null ? null : yearStart[state.year];
      var ye = state.year === null ? null : yearStart[state.year + 1];
      var shown = 0, hidden = 0, inYear = 0;
      rows.forEach(function (r) {
        var it = r.it;
        var okF = !f || !!fset[it.id];
        var okY = ys === null || (it.start < ye && it.end > ys);
        r.li.classList.toggle("is-dim", !(okF && okY));
        r.li.classList.toggle("is-focus", !!f && !!fset[it.id]);
        if (r.li.classList.contains("is-out")) hidden++; else shown++;
        if (ys !== null && okY) inYear++;
      });
      var parts = [IX.fmt(S["ix.summary.window"], { from: yearText(state.from), to: yearText(state.to), n: shown, total: rows.length })];
      if (hidden) parts.push(IX.fmt(S["ix.summary.hidden." + (hidden === 1 ? "one" : "other")], { n: hidden }));
      if (ys !== null) parts.push(IX.fmt(S["ix.summary.year." + (inYear === 1 ? "one" : "other")], { year: yearText(state.year), n: inYear }));
      if (f) parts.push(IX.fmt(S["ix.summary.focus_tl"], { name: f.name, n: f.items.length, m: f.unplaced }));
      summary.textContent = parts.join(" ");
    }

    function save() {
      var st = {
        from: state.from !== ax.first_year ? state.from : null,
        to: state.to !== ax.last_year ? state.to : null,
        year: state.year, focus: state.focus, sel: state.sel
      };
      IX.writeState(st);
      var link = IX.stateString({ focus: state.focus, year: state.year });
      toMap.setAttribute("href", "../map/" + (link ? "#" + link : ""));
    }

    function update() {
      fromOut.textContent = yearText(state.from);
      toOut.textContent = yearText(state.to);
      winSummary.textContent = IX.fmt(S["ix.ctl.window_summary"], { from: yearText(state.from), to: yearText(state.to) });
      place();
      emphasis();
      save();
    }

    update();
    if (state.sel) {
      var r = rows.filter(function (x) { return x.it.id === state.sel; })[0];
      if (r) {
        toggle(r, true);
        r.li.scrollIntoView({ block: "center", behavior: IX.reduceMotion() ? "auto" : "smooth" });
      }
    }
    var redraw = function () { ticks(yearStart[state.from], yearStart[state.to + 1]); };
    if (window.ResizeObserver) new ResizeObserver(redraw).observe(axisTrack);
    else window.addEventListener("resize", redraw);
  }
}());
