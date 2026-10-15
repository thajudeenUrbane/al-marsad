/* Lifelines: each person's life as a line. Draws only what the build put in #ll-data:
 * every date, range and age there was worked out by site/lifelines (Python) from sourced
 * records. This script places, morphs and explains; it computes no date or age itself.
 * Hue = kind of thing (person, event). Dashes and hatching = proposed, not reviewed.
 */
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("ll-data").textContent);
  var T = JSON.parse(document.getElementById("ll-i18n").textContent);
  var NS = "http://www.w3.org/2000/svg";

  function t(k, kw) {
    var s = T[k];
    if (s === undefined) { throw new Error("missing string " + k); }
    if (kw) { s = s.replace(/\{(\w+)\}/g, function (m, n) { return kw[n] !== undefined ? kw[n] : m; }); }
    return s;
  }
  function h(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  var AR = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-ﷹﷻ-﷿ﹰ-﻿]+(?:[ ‌‍]+[؀-ۿݐ-ݿࢠ-ࣿﭐ-ﷹﷻ-﷿ﹰ-﻿]+)*/g;
  function ar(escaped) {
    return escaped.replace(AR, function (m) { return '<span lang="ar" dir="rtl">' + m + "</span>"; })
      .replace(/ﷺ/g, '<span class="pbuh" lang="ar" dir="rtl">ﷺ</span>');
  }
  function hx(s) { return ar(h(s)); }

  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var ROW = 36, GAP = 30, PAD = 28, FADE = 30, AXH = 50;

  document.body.classList.remove("nojs");
  document.body.classList.add("js");
  var controls = document.querySelector(".controls");
  var stage = document.querySelector(".stage");
  var scroller = document.getElementById("ll-scroller");
  var details = document.getElementById("ll-details");
  var countEl = document.getElementById("ll-count");
  controls.hidden = false;
  stage.hidden = false;

  var P = D.people, E = D.events;
  var hasTribes = P.some(function (p) { return p.tr && p.tr.length; });
  var hasKin = P.some(function (p) { return p.kin >= 0; });
  var hasTabaqa = P.some(function (p) { return p.tb; });

  var DEFAULTS = { align: "date", units: "lunar", order: "birth", filter: "", review: false, zoom: 1 };
  var state = Object.assign({}, DEFAULTS);
  var sel = null;        // {type: "e"|"p", i}
  var m = 0;             // morph: 0 = by date, 1 = by age
  var L = null;          // current layout

  // ------------------------------------------------------------ state <-> URL
  function readHash() {
    var q = new URLSearchParams(location.hash.replace(/^#/, ""));
    if (q.get("align") === "age") { state.align = "age"; }
    if (q.get("units") === "solar") { state.units = "solar"; }
    if (["birth", "tabaqa", "kin", "tribe"].indexOf(q.get("order")) >= 0) { state.order = q.get("order"); }
    if (q.get("f")) { state.filter = q.get("f"); }
    if (q.get("rv") === "1") { state.review = true; }
    var z = parseFloat(q.get("z"));
    if (z > 0.2 && z < 40) { state.zoom = z; }
    m = state.align === "age" ? 1 : 0;
  }
  function writeHash() {
    var q = new URLSearchParams();
    Object.keys(DEFAULTS).forEach(function (k) {
      if (state[k] !== DEFAULTS[k]) {
        var key = k === "filter" ? "f" : k === "review" ? "rv" : k === "zoom" ? "z" : k;
        q.set(key, k === "review" ? "1" : k === "zoom" ? state.zoom.toFixed(2) : state[k]);
      }
    });
    var s = q.toString();
    try { history.replaceState(null, "", s ? "#" + s : location.pathname + location.search); } catch (e) { /* file: */ }
  }

  // ------------------------------------------------------------ which life to draw
  function life(p) { return state.review ? (p.v.a || p.v.b || null) : (p.v.b || null); }
  function vkey(p) { return state.review && p.v.a ? "a" : "b"; }
  function placementOf(ps) { var p = P[ps.p]; return ps.pl[vkey(p)] || null; }
  function isReviewOnly(p) {
    var lf = life(p);
    if (!lf || !state.review) { return false; }
    var act = p.c.filter(function (c) { return c.lo !== null && c.hi !== null; });
    return act.length > 0 && act.every(function (c) { return c.rv; });
  }

  // ------------------------------------------------------------ filter (label lookup)
  var lookup = {};        // datalist value -> {type, i}
  function buildLookup() {
    var dl = document.getElementById("ll-names");
    var seen = {}, opts = [];
    function add(label, ref) {
      var v = label, n = 2;
      while (seen[v]) { v = label + " (" + n + ")"; n++; }
      seen[v] = true;
      lookup[v] = ref;
      opts.push('<option value="' + h(v) + '"></option>');
    }
    E.forEach(function (e, i) { add(t("js.filter_event", { name: e.n }), { type: "e", i: i }); });
    P.forEach(function (p, i) { add(t("js.filter_person", { name: p.n }), { type: "p", i: i }); });
    dl.innerHTML = opts.join("");
  }
  function filterRef() {
    if (!state.filter) { return null; }
    var parts = state.filter.split(":");
    var list = parts[0] === "e" ? E : P;
    for (var i = 0; i < list.length; i++) { if (list[i].id === parts[1]) { return { type: parts[0], i: i }; } }
    return null;
  }
  function filterSet(ref) {
    var s = {};
    if (!ref) { return null; }
    if (ref.type === "e") {
      E[ref.i].ps.forEach(function (ps) { s[ps.p] = true; });
    } else {
      s[ref.i] = true;
      (P[ref.i].ties || []).forEach(function (j) { s[j] = true; });
      E.forEach(function (e) {
        if (e.ps.some(function (ps) { return ps.p === ref.i; })) { e.ps.forEach(function (ps) { s[ps.p] = true; }); }
      });
    }
    return s;
  }

  // ------------------------------------------------------------ order and groups
  function birthKey(p) { var lf = life(p); return lf && lf.b ? lf.b[0] : Infinity; }
  function startKey(p) { var lf = life(p); return lf ? (lf.b ? lf.b[0] : lf.s) : Infinity; }
  function cmp(a, b) {
    var ka = birthKey(P[a]), kb = birthKey(P[b]);
    if (ka !== kb) { return ka < kb ? -1 : 1; }
    var sa = startKey(P[a]), sb = startKey(P[b]);
    if (sa !== sb) { return sa < sb ? -1 : 1; }
    return P[a].n < P[b].n ? -1 : P[a].n > P[b].n ? 1 : 0;
  }
  function groupsOf(ids) {
    var key, label;
    if (state.order === "tabaqa") {
      key = function (p) { return p.tb || ""; };
      label = function (k) { return k ? t("js.group_tabaqa", { name: k }) : t("js.group_no_tabaqa"); };
    } else if (state.order === "kin") {
      key = function (p) { return p.kin >= 0 ? String(p.kin) : ""; };
      label = function (k) { return k ? D.kin[k] : t("js.group_no_kin"); };
    } else if (state.order === "tribe") {
      key = function (p) { return p.tr && p.tr.length ? p.tr[0] : ""; };
      label = function (k) { return k ? t("js.group_tribe", { name: k }) : t("js.group_no_tribe"); };
    } else {
      key = function (p) { return birthKey(p) === Infinity ? "" : "all"; };
      label = function (k) { return k ? "" : t("js.group_no_birth"); };
    }
    var g = {};
    ids.forEach(function (i) { var k = key(P[i]); (g[k] = g[k] || []).push(i); });
    var keys = Object.keys(g).sort(function (a, b) {
      if ((a === "") !== (b === "")) { return a === "" ? 1 : -1; }
      var ma = Math.min.apply(null, g[a].map(function (i) { return startKey(P[i]); }));
      var mb = Math.min.apply(null, g[b].map(function (i) { return startKey(P[i]); }));
      return ma !== mb ? (ma < mb ? -1 : 1) : (a < b ? -1 : 1);
    });
    return keys.map(function (k) { return { label: label(k), ids: g[k].sort(cmp) }; });
  }

  // ------------------------------------------------------------ layout
  function layout() {
    var ref = filterRef(), fs = filterSet(ref);
    var ids = [];
    P.forEach(function (p, i) { if (life(p) && (!fs || fs[i])) { ids.push(i); } });
    var groups = groupsOf(ids);
    var rows = [], y = 10, rowOf = {};
    groups.forEach(function (g, gi) {
      if (g.label) {
        var gh = gi === 0 ? 24 : 24 + GAP;
        rows.push({ g: g.label, y: y, h: gh });
        y += gh;
      } else if (gi > 0) {
        y += GAP;
      }
      g.ids.forEach(function (i) { rowOf[i] = rows.length; rows.push({ p: i, y: y, h: ROW }); y += ROW; });
    });
    var height = y + 16;
    // date domain
    var lo = Infinity, hi = -Infinity;
    ids.forEach(function (i) {
      var lf = life(P[i]);
      lo = Math.min(lo, lf.b ? lf.b[0] : lf.s);
      hi = Math.max(hi, lf.d ? lf.d[1] : lf.e);
    });
    var evs = [];
    E.forEach(function (e, ei) {
      var on = e.ps.filter(function (ps) { var pl = placementOf(ps); return rowOf[ps.p] !== undefined && pl && pl.ok; });
      if (on.length) { evs.push({ i: ei, on: on }); lo = Math.min(lo, e.lo); hi = Math.max(hi, e.hi); }
    });
    if (!isFinite(lo)) { lo = 0; hi = 1; }
    // age domain (years of the chosen unit)
    var u = state.units, amax = 1;
    ids.forEach(function (i) {
      var lf = life(P[i]);
      if (lf.age) { amax = Math.max(amax, lf.age[u].d ? lf.age[u].d[1] : lf.age[u].e); }
    });
    evs.forEach(function (ev) {
      ev.on.forEach(function (ps) { var pl = placementOf(ps); if (pl && pl[u]) { amax = Math.max(amax, pl[u][1]); } });
    });
    var avail = Math.max(240, scroller.clientWidth - namesWidth() - 2);
    var yearDays = D.unitDays.solar;
    var spanY = (hi - lo) / yearDays + 2 * (FADE + PAD) / 6;
    var kD = Math.max(5, (avail - 2 * PAD - 2 * FADE) / Math.max(10, (hi - lo) / yearDays)) * state.zoom / yearDays;
    var kA = Math.max(3.2, (avail - 2 * PAD - FADE) / Math.max(10, amax)) * state.zoom / D.unitDays[u];
    var wD = 2 * PAD + 2 * FADE + (hi - lo) * kD;
    var wA = 2 * PAD + FADE + amax * D.unitDays[u] * kA + 24;
    L = { ids: ids, rows: rows, rowOf: rowOf, height: height, lo: lo, hi: hi, kD: kD, kA: kA, wD: wD, wA: wA,
          evs: evs, ref: ref, units: u, amax: amax, spanY: spanY };
    return L;
  }
  function namesWidth() {
    var v = getComputedStyle(document.documentElement).getPropertyValue("--namew");
    return parseFloat(v) || 210;
  }
  function xD(j) { return PAD + FADE + (j - L.lo) * L.kD; }
  function xA(years) { return PAD + years * D.unitDays[L.units] * L.kA; }
  function mix(a, b) { return a + (b - a) * m; }
  function rowY(i) { var r = L.rows[L.rowOf[i]]; return r.y + ROW / 2; }

  // ------------------------------------------------------------ drawing
  function axisSVG(width) {
    var out = [];
    // by date: CE row and Hijri row (both computed at build time)
    var pxYear = L.kD * D.unitDays.solar;
    var step = [1, 2, 5, 10, 20, 25, 50, 100].filter(function (s) { return s * pxYear >= 54; })[0] || 100;
    var dOp = 1 - m, aOp = m;
    if (dOp > 0.01 && D.axis.ce) {
      out.push('<g opacity="' + dOp.toFixed(3) + '">');
      D.axis.ce.forEach(function (c) {
        if (((c[0] % step) + step) % step !== 0) { return; }
        var x = mix(xD(c[1]), xD(c[1]));
        if (x < 0 || x > width) { return; }
        out.push('<line class="tk" x1="' + x.toFixed(1) + '" y1="16" x2="' + x.toFixed(1) + '" y2="24"/>' +
                 '<text x="' + (x + 3).toFixed(1) + '" y="13">' + c[0] + "</text>");
      });
      var hstep = [1, 2, 5, 10, 20, 25, 50, 100].filter(function (s) { return s * pxYear * D.unitDays.lunar / D.unitDays.solar >= 62; })[0] || 100;
      out.push('<g class="hj">');
      D.axis.ah.forEach(function (c) {
        if (((c[0] - 1) % hstep + hstep) % hstep !== 0) { return; }
        var x = xD(c[1]);
        if (x < 0 || x > width) { return; }
        var lbl = c[0] >= 1 ? t("js.ah_tick", { y: c[0] }) : t("js.bh_tick", { y: 1 - c[0] });
        out.push('<line class="tk" x1="' + x.toFixed(1) + '" y1="40" x2="' + x.toFixed(1) + '" y2="48"/>' +
                 '<text x="' + (x + 3).toFixed(1) + '" y="38">' + h(lbl) + "</text>");
      });
      out.push("</g></g>");
    }
    if (aOp > 0.01) {
      var pxA = L.kA * D.unitDays[L.units];
      var astep = [1, 2, 5, 10, 20, 25, 50].filter(function (s) { return s * pxA >= 40; })[0] || 50;
      out.push('<g opacity="' + aOp.toFixed(3) + '">');
      for (var a = 0; a <= L.amax + astep; a += astep) {
        var x = xA(a);
        out.push('<line class="tk" x1="' + x.toFixed(1) + '" y1="30" x2="' + x.toFixed(1) + '" y2="48"/>' +
                 '<text x="' + (x + 3).toFixed(1) + '" y="27">' + a + "</text>");
      }
      out.push("</g>");
    }
    return '<svg class="axis" xmlns="' + NS + '" width="' + width.toFixed(0) + '" height="' + AXH + '" aria-hidden="true">' +
      out.join("") + "</svg>";
  }

  function gridSVG(width) {
    var out = [];
    var pxYear = L.kD * D.unitDays.solar;
    var step = [1, 2, 5, 10, 20, 25, 50, 100].filter(function (s) { return s * pxYear >= 54; })[0] || 100;
    if (m < 0.99 && D.axis.ce) {
      out.push('<g opacity="' + (1 - m).toFixed(3) + '">');
      D.axis.ce.forEach(function (c) {
        if (((c[0] % step) + step) % step !== 0) { return; }
        var x = xD(c[1]);
        if (x >= 0 && x <= width) { out.push('<line class="gline" x1="' + x.toFixed(1) + '" y1="0" x2="' + x.toFixed(1) + '" y2="' + L.height + '"/>'); }
      });
      out.push("</g>");
    }
    if (m > 0.01) {
      var pxA = L.kA * D.unitDays[L.units];
      var astep = [1, 2, 5, 10, 20, 25, 50].filter(function (s) { return s * pxA >= 40; })[0] || 50;
      out.push('<g opacity="' + m.toFixed(3) + '">');
      for (var a = 0; a <= L.amax + astep; a += astep) {
        var x = xA(a);
        out.push('<line class="gline" x1="' + x.toFixed(1) + '" y1="0" x2="' + x.toFixed(1) + '" y2="' + L.height + '"/>');
      }
      out.push("</g>");
    }
    L.rows.forEach(function (r) {
      if (r.g) { out.push('<line class="grule" x1="0" y1="' + (r.y + 0.5) + '" x2="' + width.toFixed(0) + '" y2="' + (r.y + 0.5) + '"/>'); }
    });
    return out.join("");
  }

  function seg(x1, x2) { return [Math.min(x1, x2), Math.max(x1, x2)]; }

  // geometry of one person's line at the current morph
  function personGeom(i) {
    var p = P[i], lf = life(p), u = L.units, g = { y: rowY(i), op: 1 };
    var canAge = !!lf.b;
    function X(dateJ, ageY) { return canAge ? mix(xD(dateJ), xA(ageY)) : xD(dateJ); }
    var ag = canAge ? lf.age[u] : null;
    if (lf.b) { g.b = [X(lf.b[0], 0), X(lf.b[1], 0)]; }
    if (lf.d) { g.d = [X(lf.d[0], ag ? ag.d[0] : 0), X(lf.d[1], ag ? ag.d[1] : 0)]; }
    if (lf.segment) { g.s = [X(lf.s, 0), X(lf.e, ag ? ag.e : 0)]; }
    g.x0 = X(lf.s, 0);
    g.x1 = X(lf.e, ag ? ag.e : 0);
    g.openStart = lf.open_start;
    g.openEnd = lf.open_end;
    if (!canAge) { g.op = 1 - m; }
    var xs = [g.x0, g.x1];
    if (g.b) { xs.push(g.b[0], g.b[1]); }
    if (g.d) { xs.push(g.d[0], g.d[1]); }
    g.min = Math.min.apply(null, xs) - (g.openStart ? FADE : 0);
    g.max = Math.max.apply(null, xs) + (g.openEnd ? FADE : 0);
    return g;
  }

  function nodeX(ev, ps) {
    var e = E[ev.i], pl = placementOf(ps), u = L.units;
    var d0 = xD(e.lo), d1 = xD(e.hi);
    if (pl && pl[u]) { return [mix(d0, xA(pl[u][0])), mix(d1, xA(pl[u][1]))]; }
    return [d0, d1];
  }

  function draw() {
    var width = Math.max(mix(L.wD, L.wA), scroller.clientWidth - namesWidth() - 2);
    var parts = [];
    parts.push('<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">' +
      '<rect width="6" height="6" fill="#f0a95a" fill-opacity="0.14"/><line x1="0" y1="0" x2="0" y2="6" stroke="#f0a95a" stroke-opacity="0.55" stroke-width="2"/></pattern>' +
      '<linearGradient id="fadeL" x1="0" x2="1" y1="0" y2="0"><stop offset="0" class="fade-0"/><stop offset="1" class="fade-1"/></linearGradient>' +
      '<linearGradient id="fadeR" x1="0" x2="1" y1="0" y2="0"><stop offset="0" class="fade-1"/><stop offset="1" class="fade-0"/></linearGradient></defs>');
    parts.push(gridSVG(width));
    // connectors: perpendicular, by date only; as wide as the date's uncertainty
    var conns = [];
    if (m < 0.999) {
      L.evs.forEach(function (ev) {
        if (ev.on.length < 2) { return; }
        var e = E[ev.i];
        var ys = ev.on.map(function (ps) { return rowY(ps.p); });
        var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
        var x0 = xD(e.lo), x1 = xD(e.hi), w = x1 - x0;
        var body;
        if (w < 3) {
          var xc = (x0 + x1) / 2;
          body = '<line class="conn" x1="' + xc.toFixed(1) + '" y1="' + y0 + '" x2="' + xc.toFixed(1) + '" y2="' + y1 + '"/>';
          x0 = xc - 6; w = 12;
        } else {
          body = '<rect class="cband" x="' + x0.toFixed(1) + '" y="' + y0 + '" width="' + w.toFixed(1) + '" height="' + (y1 - y0) + '"/>';
          if (w < 12) { x0 -= (12 - w) / 2; w = 12; }
        }
        conns.push('<g class="ev" data-ev="' + ev.i + '" tabindex="0" role="button" aria-label="' +
          h(t("js.conn_aria", { name: e.n, date: e.t, n: ev.on.length })) + '" opacity="' + (1 - m).toFixed(3) + '">' +
          body + '<rect class="chit" x="' + x0.toFixed(1) + '" y="' + y0 + '" width="' + w.toFixed(1) + '" height="' + (y1 - y0) + '"/></g>');
      });
    }
    parts.push('<g class="conns">' + conns.join("") + "</g>");
    // lines (halo first: it opens a visible gap wherever a line crosses a connector it is not part of)
    var lines = [];
    L.ids.forEach(function (i) {
      var p = P[i], g = personGeom(i), y = g.y;
      if (g.op <= 0.001) {
        lines.push('<text class="rowlbl" x="' + (PAD + 4) + '" y="' + (y + 4) + '" opacity="' + m.toFixed(3) + '">' + h(t("js.no_birth_row")) + "</text>");
        return;
      }
      var cls = "pl" + (isReviewOnly(p) ? " rv" : "");
      var s = ['<g class="' + cls + '" data-p="' + i + '" opacity="' + g.op.toFixed(3) + '">'];
      s.push('<line class="halo" x1="' + g.min.toFixed(1) + '" y1="' + y + '" x2="' + g.max.toFixed(1) + '" y2="' + y + '"/>');
      if (g.b) {
        var bw = Math.max(2, g.b[1] - g.b[0]);
        s.push(bw <= 2.5 ? '<line class="tick0" x1="' + g.b[0].toFixed(1) + '" y1="' + (y - 6) + '" x2="' + g.b[0].toFixed(1) + '" y2="' + (y + 6) + '"/>'
          : '<rect class="band" x="' + g.b[0].toFixed(1) + '" y="' + (y - 5) + '" width="' + bw.toFixed(1) + '" height="10" rx="3"/>');
      }
      if (g.s && g.s[1] > g.s[0]) {
        s.push('<line class="seg" x1="' + g.s[0].toFixed(1) + '" y1="' + y + '" x2="' + g.s[1].toFixed(1) + '" y2="' + y + '"/>');
      }
      if (g.d) {
        var dw = Math.max(2, g.d[1] - g.d[0]);
        s.push('<rect class="band" x="' + g.d[0].toFixed(1) + '" y="' + (y - 5) + '" width="' + dw.toFixed(1) + '" height="10" rx="3"/>');
      }
      if (g.openStart) {
        s.push('<rect x="' + (g.x0 - FADE).toFixed(1) + '" y="' + (y - 1.1) + '" width="' + FADE + '" height="2.2" fill="url(#fadeL)"/>');
      }
      if (g.openEnd) {
        s.push('<rect x="' + g.x1.toFixed(1) + '" y="' + (y - 1.1) + '" width="' + FADE + '" height="2.2" fill="url(#fadeR)"/>');
      }
      s.push('<line class="lhit" x1="' + g.min.toFixed(1) + '" y1="' + y + '" x2="' + g.max.toFixed(1) + '" y2="' + y + '"/>');
      s.push("</g>");
      lines.push(s.join(""));
    });
    parts.push('<g class="lines">' + lines.join("") + "</g>");
    if (m > 0.01 && L.ids.length && !L.ids.some(function (i) { return life(P[i]).b; })) {
      parts.push('<text class="rowlbl" x="' + (PAD + 4) + '" y="' + (L.height - 6) + '" opacity="' + m.toFixed(3) + '">' + h(t("js.none_by_age")) + "</text>");
    }
    // nodes: only where a connector meets a participant's line
    var nodes = [], labels = [], lastLbl = {};
    var all = [];
    L.evs.forEach(function (ev) {
      ev.on.forEach(function (ps) {
        var lf = life(P[ps.p]);
        var vis = lf.b ? 1 : 1 - m;
        if (vis <= 0.001) { return; }
        var xr = nodeX(ev, ps);
        all.push({ ev: ev, ps: ps, x0: xr[0], x1: xr[1], y: rowY(ps.p), op: vis });
      });
    });
    all.sort(function (a, b) { return a.y - b.y || a.x0 - b.x0; });
    all.forEach(function (n) {
      var w = n.x1 - n.x0, r = 4.5;
      var xc = (n.x0 + n.x1) / 2;
      var shape = w < 2 * r ? '<circle class="node" cx="' + xc.toFixed(1) + '" cy="' + n.y + '" r="' + r + '"'
        : '<rect class="node" x="' + n.x0.toFixed(1) + '" y="' + (n.y - r) + '" width="' + w.toFixed(1) + '" height="' + (2 * r) + '" rx="' + r + '"';
      nodes.push(shape + ' data-ev="' + n.ev.i + '" data-p="' + n.ps.p + '" opacity="' + n.op.toFixed(3) + '"/>');
      var pl = placementOf(n.ps), txt = pl && pl[L.units + "_text"] !== undefined ? pl[L.units + "_text"] : null;
      if (txt !== null) {
        var key = n.y, skip = lastLbl[key] !== undefined && xc - lastLbl[key] < 40;
        if (!skip) { lastLbl[key] = xc; }
        labels.push('<text class="lbl' + (skip ? " skip" : "") + '" data-ev="' + n.ev.i + '" x="' + (xc - 6).toFixed(1) + '" y="' + (n.y - 8) + '">' + h(txt) + "</text>");
      }
    });
    parts.push('<g class="nodes">' + nodes.join("") + "</g>");
    parts.push('<g class="labels">' + labels.join("") + "</g>");

    var svg = '<svg class="plot' + (m > 0.5 ? " m-age" : "") + '" xmlns="' + NS + '" width="' + width.toFixed(0) +
      '" height="' + L.height + '" role="group" aria-label="' + h(t("js.plot_aria")) + '">' + parts.join("") + "</svg>";
    var names = L.rows.map(function (r) {
      if (r.g) { return '<li class="gh" style="block-size:' + r.h + 'px"><span>' + hx(r.g) + "</span></li>"; }
      var p = P[r.p], rv = isReviewOnly(p);
      var label = p.n + (rv ? " " + t("js.review_mark") : "");
      return '<li style="block-size:' + ROW + 'px"><button type="button" data-p="' + r.p + '" class="' + (rv ? "rv" : "") +
        '" title="' + h(label) + '">' + hx(label) + "</button></li>";
    }).join("");
    var corner = m < 0.5 ? '<span>' + h(t("js.axis_ce")) + "</span><span>" + h(t("js.axis_ah")) + "</span>"
      : "<span>" + h(t("js.axis_age", { unit: t("units." + L.units) })) + "</span>";
    var focusKey = focusedKey();
    var sx = scroller.scrollLeft, sy = scroller.scrollTop;
    scroller.innerHTML = '<div class="ax-row" style="inline-size:' + (width + namesWidth()).toFixed(0) + 'px"><div class="corner">' + corner + "</div>" +
      axisSVG(width) + '</div><div class="body-row" style="inline-size:' + (width + namesWidth()).toFixed(0) + 'px"><ol class="names" aria-label="' + h(t("js.names_aria")) + '">' +
      names + "</ol>" + svg + "</div>";
    scroller.scrollLeft = sx;
    scroller.scrollTop = sy;
    applySelection();
    restoreFocus(focusKey);
  }

  function focusedKey() {
    var a = document.activeElement;
    if (!a || !scroller.contains(a)) { return null; }
    if (a.dataset.ev !== undefined) { return { ev: a.dataset.ev }; }
    if (a.dataset.p !== undefined) { return { p: a.dataset.p }; }
    return null;
  }
  function restoreFocus(k) {
    if (!k) { return; }
    var el = k.ev !== undefined ? scroller.querySelector('g.ev[data-ev="' + k.ev + '"]') : scroller.querySelector('.names button[data-p="' + k.p + '"]');
    if (el) { el.focus({ preventScroll: true }); }
  }

  // ------------------------------------------------------------ selection and details
  function applySelection() {
    var plot = scroller.querySelector("svg.plot");
    if (!plot) { return; }
    scroller.querySelectorAll(".sel").forEach(function (el) { el.classList.remove("sel"); });
    plot.classList.toggle("has-sel", !!sel && sel.type === "e");
    if (!sel) { return; }
    if (sel.type === "e") {
      scroller.querySelectorAll('[data-ev="' + sel.i + '"]').forEach(function (el) { el.classList.add("sel"); });
    } else {
      scroller.querySelectorAll('.pl[data-p="' + sel.i + '"], .names button[data-p="' + sel.i + '"]').forEach(function (el) { el.classList.add("sel"); });
    }
  }

  function statusText(st) { return t("status.label", { value: st ? t("status." + st) : t("status.none") }); }
  function ageText(pl) {
    var u = state.units, o = u === "lunar" ? "solar" : "lunar";
    if (!pl) { return ""; }
    if (!pl.ok) { return t("age.flag." + pl.flag); }
    if (pl[u + "_text"] === undefined) { return t("age.no_birth"); }
    return t("js.age_value", { age: pl[u + "_text"], unit: t("units." + u) }) + " · " +
      t("js.age_value", { age: pl[o + "_text"], unit: t("units." + o) });
  }
  function srcHTML(src) {
    var a = src.href ? '<a href="' + h(src.href) + '">' + hx(src.label) + "</a>" : hx(src.label);
    return a + (src.detail ? " · " + hx(src.detail) : "") + " · " + h(statusText(src.status));
  }
  function claimsHTML(p, kind) {
    var cs = p.c.filter(function (c) { return c.k === kind && (state.review || !c.rv); });
    if (!cs.length) { return '<dd class="computed">' + h(t(kind === "birth" ? "js.birth_unknown" : "js.death_unknown")) + "</dd>"; }
    return cs.map(function (c) {
      return "<dd>" + hx(c.t) + (c.rv ? ' <span class="tag">' + h(t("js.needs_review_tag")) + "</span>" : "") +
        '<div class="meta">' + srcHTML(c.src) + "</div>" +
        (c.nt.length ? '<div class="meta">' + c.nt.map(hx).join("<br>") + "</div>" : "") + "</dd>";
    }).join("");
  }

  function showDetails(html, focusHeading) {
    details.innerHTML = '<div class="details-inner"><button type="button" class="btn close" data-act="close" aria-label="' +
      h(t("js.close")) + '">×</button>' + html + "</div>";
    details.hidden = false;
    if (focusHeading) { details.focus({ preventScroll: true }); }
  }

  function personDetails(i, focus) {
    var p = P[i], lf = life(p), u = state.units, o = u === "lunar" ? "solar" : "lunar";
    var out = ['<h2 id="ll-details-h">' + hx(p.n) + "</h2>", "<dl>"];
    out.push("<dt>" + h(t("js.born")) + "</dt>" + claimsHTML(p, "birth"));
    out.push("<dt>" + h(t("js.died")) + "</dt>" + claimsHTML(p, "death"));
    if (lf && lf.age_at_death) {
      out.push("<dt>" + h(t("js.age_at_death")) + "</dt><dd>" + h(t("js.age_value", { age: lf.age_at_death[u], unit: t("units." + u) })) +
        " · " + h(t("js.age_value", { age: lf.age_at_death[o], unit: t("units." + o) })) +
        '<div class="meta">' + h(t("js.age_how")) + "</div></dd>");
    }
    if (lf && lf.conflict && lf.conflict.length) {
      out.push("<dt>" + h(t("js.conflict")) + "</dt><dd>" + h(t("js.conflict_birth_after_death")) + "</dd>");
    }
    if (p.tb) { out.push("<dt>" + h(t("js.tabaqa")) + "</dt><dd>" + hx(p.tb) + "</dd>"); }
    if (p.kin >= 0) { out.push("<dt>" + h(t("js.kin")) + "</dt><dd>" + hx(D.kin[String(p.kin)]) + "</dd>"); }
    if (p.tr && p.tr.length) { out.push("<dt>" + h(t("js.tribe")) + "</dt><dd>" + hx(p.tr.join(", ")) + "</dd>"); }
    if (p.oc && p.oc.length) {
      out.push("<dt>" + h(t("js.other_candidates")) + "</dt><dd>" + p.oc.map(function (q) {
        return /^Q\d+$/.test(q) ? '<a href="https://www.wikidata.org/wiki/' + q + '">' + q + "</a>" : h(q);
      }).join(", ") + "</dd>");
    }
    out.push("</dl>");
    var evs = [];
    E.forEach(function (e, ei) {
      e.ps.forEach(function (ps) {
        if (ps.p !== i) { return; }
        evs.push("<li><button type=\"button\" class=\"lk\" data-goto-ev=\"" + ei + "\">" + hx(e.n) + "</button> — " + hx(e.t) +
          '<div class="meta">' + h(ageText(placementOf(ps))) + " · " + hx(ps.how) + " · " + h(statusText(ps.st)) + "</div></li>");
      });
    });
    out.push("<h3>" + h(t("js.events_on_line", { n: evs.length })) + "</h3>");
    out.push(evs.length ? "<ul>" + evs.join("") + "</ul>" : '<p class="meta">' + h(t("js.no_events")) + "</p>");
    if (p.u) { out.push('<p><a href="' + h(p.u) + '">' + h(t("js.reader_page")) + "</a></p>"); }
    showDetails(out.join(""), focus);
  }

  function eventDetails(ei, focus) {
    var e = E[ei];
    var out = ['<h2 id="ll-details-h">' + hx(e.n) + "</h2>", "<p>" + hx(e.t) + "</p>"];
    if (e.nt.length) { out.push('<p class="meta">' + e.nt.map(hx).join("<br>") + "</p>"); }
    out.push('<p class="meta">' + h(t("js.event_source", { agents: e.ag.join(", ") || t("js.unknown") })) + "</p>");
    if (e.dis) { out.push('<p class="meta">' + h(t("date.disputed")) + "</p>"); }
    var order = [], byP = {};
    e.ps.forEach(function (ps) {
      if (!byP[ps.p]) { byP[ps.p] = []; order.push(ps.p); }
      byP[ps.p].push(ps);
    });
    var rows = order.map(function (pi) {
      var p = P[pi], first = byP[pi][0];
      var shown = L && L.rowOf[pi] !== undefined;
      var claims = byP[pi].map(function (ps) {
        var cit = ps.cit ? " · " + hx(ps.cit) : "";
        var ai = ps.ai ? " · " + h(t("js.ai_source")) : "";
        return '<div class="meta">' + hx(ps.how) + " · " + h(statusText(ps.st)) + cit + ai + "</div>";
      }).join("");
      return "<li><button type=\"button\" class=\"lk\" data-goto-p=\"" + pi + "\">" + hx(p.n) + "</button>" +
        (shown ? "" : ' <span class="tag">' + h(t("js.not_shown")) + "</span>") +
        '<div class="meta">' + h(ageText(placementOf(first))) + "</div>" + claims + "</li>";
    });
    out.push("<h3>" + h(t("js.took_part", { n: order.length })) + "</h3><ul>" + rows.join("") + "</ul>");
    if (e.oth.length) {
      out.push("<h3>" + h(t("js.also_no_dates", { n: e.oth.length })) + "</h3><ul>" +
        e.oth.map(function (o) { return "<li>" + (o.u ? '<a href="' + h(o.u) + '">' + hx(o.n) + "</a>" : hx(o.n)) + "</li>"; }).join("") + "</ul>");
    }
    if (e.u) { out.push('<p><a href="' + h(e.u) + '">' + h(t("js.reader_page_event")) + "</a></p>"); }
    showDetails(out.join(""), focus);
  }

  function select(s, focus) {
    sel = s;
    applySelection();
    if (!s) { details.hidden = true; return; }
    if (s.type === "e") { eventDetails(s.i, focus); } else { personDetails(s.i, focus); }
    requestAnimationFrame(function () { reveal(s); });
  }

  // keep the selected connector or line in view (the details panel narrows the chart)
  function reveal(s) {
    if (!L || !s) { return; }
    var x, y;
    if (s.type === "e") {
      var ev = L.evs.filter(function (v) { return v.i === s.i; })[0];
      if (!ev) { return; }
      x = Math.min.apply(null, ev.on.map(function (ps) { return nodeX(ev, ps)[0]; }));
      y = Math.min.apply(null, ev.on.map(function (ps) { return rowY(ps.p); }));
    } else {
      if (L.rowOf[s.i] === undefined) { return; }
      x = personGeom(s.i).min;
      y = rowY(s.i);
    }
    var viewW = scroller.clientWidth - namesWidth(), viewH = scroller.clientHeight - AXH;
    if (x < scroller.scrollLeft + 8 || x > scroller.scrollLeft + viewW - 40) { scroller.scrollLeft = Math.max(0, x - viewW / 3); }
    if (y < scroller.scrollTop + 8 || y > scroller.scrollTop + viewH - 20) { scroller.scrollTop = Math.max(0, y - viewH / 3); }
  }

  // ------------------------------------------------------------ orientation, table sync
  function orient() {
    var total = P.filter(function (p) { return life(p); }).length;
    var txt = t("js.showing", { n: L.ids.length, m: total, u: D.undated.length });
    if (L.ref) {
      var nm = L.ref.type === "e" ? E[L.ref.i].n : P[L.ref.i].n;
      txt += " · " + t(L.ref.type === "e" ? "js.filter_desc_event" : "js.filter_desc_person", { name: nm });
    }
    txt += " · " + t(state.align === "age" ? "js.mode_age" : "js.mode_date", { unit: t("units." + state.units) });
    countEl.textContent = txt;
    document.querySelector('[data-act="clear-filter"]').hidden = !state.filter;
  }

  function syncTable() {
    var shownEv = {};
    L.evs.forEach(function (ev) { shownEv[ev.i] = true; });
    document.querySelectorAll(".ll-table tbody tr").forEach(function (tr) {
      var i = +tr.dataset.p, v = tr.dataset.v, p = P[i];
      var want = state.review && p.v.a ? "a" : "b";
      tr.hidden = !(L.rowOf[i] !== undefined && v === want);
      tr.querySelectorAll("li[data-ev]").forEach(function (li) { li.hidden = !shownEv[+li.dataset.ev]; });
    });
  }

  // ------------------------------------------------------------ morph
  var anim = null;
  function morphTo(target) {
    if (anim) { cancelAnimationFrame(anim); anim = null; }
    if (reduceMotion) { m = target; draw(); return; }
    var from = m, t0 = null, dur = 650;
    function step(ts) {
      if (t0 === null) { t0 = ts; }
      var k = Math.min(1, (ts - t0) / dur);
      var e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      m = from + (target - from) * e;
      draw();
      if (k < 1) { anim = requestAnimationFrame(step); } else { anim = null; m = target; draw(); }
    }
    anim = requestAnimationFrame(step);
  }

  function refresh(keepSel) {
    layout();
    draw();
    orient();
    syncTable();
    writeHash();
    if (!keepSel) { select(null); } else if (sel) { select(sel, false); }
  }

  // ------------------------------------------------------------ zoom (buttons, ctrl+wheel, pinch)
  function setZoom(z, clientX) {
    z = Math.max(0.3, Math.min(30, z));
    var rect = scroller.getBoundingClientRect();
    var off = (clientX === undefined ? rect.left + rect.width / 2 : clientX) - rect.left - namesWidth();
    var before = scroller.scrollLeft + off;
    var ratio = z / state.zoom;
    state.zoom = z;
    layout();
    draw();
    scroller.scrollLeft = Math.max(0, before * ratio - off);
    writeHash();
  }
  scroller.addEventListener("wheel", function (e) {
    if (!e.ctrlKey) { return; }
    e.preventDefault();
    setZoom(state.zoom * (e.deltaY < 0 ? 1.12 : 1 / 1.12), e.clientX);
  }, { passive: false });
  var touches = {}, pinch = null;
  function tdist() {
    var k = Object.keys(touches);
    if (k.length < 2) { return null; }
    var a = touches[k[0]], b = touches[k[1]];
    return { d: Math.hypot(a.x - b.x, a.y - b.y), x: (a.x + b.x) / 2 };
  }
  scroller.addEventListener("pointerdown", function (e) {
    if (e.pointerType !== "touch") { return; }
    touches[e.pointerId] = { x: e.clientX, y: e.clientY };
    var td = tdist();
    if (td) { pinch = { d: td.d, z: state.zoom }; }
  });
  scroller.addEventListener("pointermove", function (e) {
    if (!touches[e.pointerId]) { return; }
    touches[e.pointerId] = { x: e.clientX, y: e.clientY };
    var td = tdist();
    if (pinch && td && td.d > 10) {
      var z = pinch.z * td.d / pinch.d;
      if (Math.abs(z - state.zoom) / state.zoom > 0.02) { setZoom(z, td.x); }
    }
  });
  function lift(e) { delete touches[e.pointerId]; if (Object.keys(touches).length < 2) { pinch = null; } }
  scroller.addEventListener("pointerup", lift);
  scroller.addEventListener("pointercancel", lift);

  // ------------------------------------------------------------ events
  scroller.addEventListener("click", function (e) {
    var el = e.target.closest("[data-ev],[data-p]");
    if (!el || !scroller.contains(el)) { return; }
    if (el.dataset.ev !== undefined) { select({ type: "e", i: +el.dataset.ev }, false); }
    else { select({ type: "p", i: +el.dataset.p }, false); }
  });
  scroller.addEventListener("keydown", function (e) {
    var el = e.target;
    if ((e.key === "Enter" || e.key === " ") && el.matches && el.matches("g.ev")) {
      e.preventDefault();
      select({ type: "e", i: +el.dataset.ev }, true);
    } else if (e.key === "+" || e.key === "=") { setZoom(state.zoom * 1.25); }
    else if (e.key === "-") { setZoom(state.zoom / 1.25); }
  });
  details.addEventListener("click", function (e) {
    var b = e.target.closest("button");
    if (!b) { return; }
    if (b.dataset.act === "close") { select(null); scroller.focus(); return; }
    if (b.dataset.gotoEv !== undefined) { select({ type: "e", i: +b.dataset.gotoEv }, true); }
    if (b.dataset.gotoP !== undefined) { select({ type: "p", i: +b.dataset.gotoP }, true); }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !details.hidden) { select(null); scroller.focus(); }
  });
  controls.addEventListener("change", function (e) {
    var el = e.target;
    if (el.name === "align") { state.align = el.value; writeHash(); orient(); morphTo(el.value === "age" ? 1 : 0); return; }
    if (el.name === "units") { state.units = el.value; refresh(true); return; }
    if (el.name === "order") { state.order = el.value; refresh(true); return; }
    if (el.name === "review") { state.review = el.checked; refresh(false); return; }
    if (el.name === "filter") { applyFilterInput(el.value); }
  });
  controls.querySelector('input[name="filter"]').addEventListener("input", function (e) {
    if (lookup[e.target.value]) { applyFilterInput(e.target.value); }
  });
  function applyFilterInput(v) {
    var ref = lookup[v];
    if (!ref) { return; }
    state.filter = ref.type + ":" + (ref.type === "e" ? E[ref.i].id : P[ref.i].id);
    refresh(false);
    select(ref, false);
  }
  controls.addEventListener("click", function (e) {
    var b = e.target.closest("button");
    if (!b) { return; }
    var act = b.dataset.act;
    if (act === "zoom-in") { setZoom(state.zoom * 1.4); }
    if (act === "zoom-out") { setZoom(state.zoom / 1.4); }
    if (act === "clear-filter") { state.filter = ""; controls.querySelector('input[name="filter"]').value = ""; refresh(false); }
    if (act === "home") { goHome(); }
  });

  function syncControls() {
    controls.querySelectorAll('input[name="align"]').forEach(function (r) { r.checked = r.value === state.align; });
    controls.querySelectorAll('input[name="units"]').forEach(function (r) { r.checked = r.value === state.units; });
    var o = controls.querySelector('select[name="order"]');
    o.value = state.order;
    o.querySelector('option[value="tribe"]').disabled = !hasTribes;
    o.querySelector('option[value="kin"]').disabled = !hasKin;
    o.querySelector('option[value="tabaqa"]').disabled = !hasTabaqa;
    if (!hasTribes) { o.querySelector('option[value="tribe"]').textContent = t("js.order_tribe_none"); }
    controls.querySelector('input[name="review"]').checked = state.review;
    var ref = filterRef();
    controls.querySelector('input[name="filter"]').value = ref ? (ref.type === "e" ? t("js.filter_event", { name: E[ref.i].n }) : t("js.filter_person", { name: P[ref.i].n })) : "";
  }

  function goHome() {
    state = Object.assign({}, DEFAULTS);
    m = 0;
    syncControls();
    refresh(false);
    // orientation: bring the Prophet's line into view when it is on the chart (no emphasis)
    var pi = -1;
    P.forEach(function (p, i) { if (p.pr && L.rowOf[i] !== undefined) { pi = i; } });
    if (pi >= 0) {
      var g = personGeom(pi);
      scroller.scrollTop = Math.max(0, L.rows[L.rowOf[pi]].y - scroller.clientHeight / 3);
      scroller.scrollLeft = Math.max(0, g.min - 60);
    } else {
      scroller.scrollTop = 0;
      scroller.scrollLeft = 0;
    }
  }

  var resizeT = null;
  window.addEventListener("resize", function () {
    clearTimeout(resizeT);
    resizeT = setTimeout(function () { layout(); draw(); }, 120);
  });

  readHash();
  buildLookup();
  syncControls();
  refresh(false);
  if (!location.hash) { goHome(); }
  if (filterRef()) { select(filterRef(), false); }
})();
