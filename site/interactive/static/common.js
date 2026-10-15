/* Shared by the timeline and the map (slice 10). No UI text lives here: every string comes from
 * the page's data.json ("strings"), which the builder fills from the i18n files. HTML from the
 * data (fields ending in _html) was escaped by the builder; everything else is set as text.
 * The view state (focus, year, window, zoom, selection) lives in the URL fragment, so a view can
 * be shared as a link and reopened as it was. */
(function () {
  "use strict";
  var IX = (window.IX = {});

  IX.reduceMotion = function () {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  };

  IX.fmt = function (s, vars) {
    return String(s).replace(/\{(\w+)\}/g, function (m, k) {
      return vars && Object.prototype.hasOwnProperty.call(vars, k) ? String(vars[k]) : m;
    });
  };

  /* el("p", {class: "x", text: "..."}, [children]); "html" only for builder-escaped fields */
  IX.el = function (tag, attrs, children) {
    var n = document.createElement(tag);
    IX.set(n, attrs);
    (children || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  };
  IX.svg = function (tag, attrs, children) {
    var n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    IX.set(n, attrs);
    (children || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  };
  IX.set = function (n, attrs) {
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === "text") n.textContent = v;
      else if (k === "html") n.innerHTML = v;
      else n.setAttribute(k, v === true ? "" : v);
    });
    return n;
  };

  /* fetch data.json and hand it to `done`; the loading and failure messages are attributes of
     the container (written by the builder), since data.json may be what failed */
  IX.load = function (app, done) {
    var msg = app.querySelector(".ix-nojs");
    app.setAttribute("aria-busy", "true");
    if (msg) msg.textContent = app.getAttribute("data-loading") || msg.textContent;
    fetch(app.getAttribute("data-fetch"), { credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
      .then(function (data) {
        app.textContent = "";
        done(data);
        app.removeAttribute("aria-busy");
        app.setAttribute("data-ready", "1");
      })
      .catch(function (err) {
        app.removeAttribute("aria-busy");
        app.textContent = "";
        if (msg) {
          msg.textContent = app.getAttribute("data-failed") || "";
          app.appendChild(msg);
        }
        app.setAttribute("data-ready", "error");
        if (window.console) console.error(err);
      });
  };

  /* ------------------------------------------------------------------ view state in the URL */
  IX.readState = function () {
    var out = {};
    var h = (location.hash || "").replace(/^#/, "");
    h.split("&").forEach(function (part) {
      if (!part) return;
      var i = part.indexOf("=");
      var k = decodeURIComponent(i < 0 ? part : part.slice(0, i));
      out[k] = i < 0 ? "" : decodeURIComponent(part.slice(i + 1));
    });
    return out;
  };
  IX.stateString = function (st) {
    return Object.keys(st).filter(function (k) {
      return st[k] !== null && st[k] !== undefined && st[k] !== "";
    }).map(function (k) {
      return encodeURIComponent(k) + "=" + encodeURIComponent(st[k]).replace(/%2F/g, "/").replace(/%2C/g, ",");
    }).join("&");
  };
  IX.writeState = function (st) {
    var s = IX.stateString(st);
    try { history.replaceState(null, "", s ? "#" + s : location.pathname + location.search); } catch (e) { /* file: */ }
  };

  /* ------------------------------------------------------------------ shared controls */
  /* a labelled control: the label and its current value on one line, the input below */
  IX.control = function (labelText, input, output, extra) {
    var head = IX.el("div", { class: "ix-ctl-head" },
      [IX.el("label", { for: input.id, text: labelText }), output || null, extra || null]);
    return IX.el("div", { class: "ix-ctl" }, [head, input]);
  };

  /* <select> of the people, groups and places a view links to; value "" is nobody/nowhere */
  IX.focusSelect = function (S, focus, value, onChange) {
    var sel = IX.el("select", { id: "ix-focus" });
    sel.appendChild(IX.el("option", { value: "", text: S["ix.ctl.focus_none"] }));
    var groups = {};
    focus.forEach(function (f) {
      var g = groups[f.kind];
      if (!g) {
        g = groups[f.kind] = IX.el("optgroup", { label: S["ix.ctl.focus_group." + f.kind] || f.kind });
        sel.appendChild(g);
      }
      g.appendChild(IX.el("option", { value: f.id, text: f.name + " (" + f.items.length + ")" }));
    });
    sel.value = value || "";
    if (sel.value !== (value || "")) sel.value = "";
    sel.addEventListener("change", function () { onChange(sel.value); });
    return { box: IX.control(S["ix.ctl.focus"], sel), input: sel };
  };

  /* the year cursor: a range over whole CE years, off until it is moved or set */
  IX.yearControl = function (S, first, last, value, onChange) {
    var input = IX.el("input", { id: "ix-year", type: "range", min: String(first), max: String(last), step: "1",
      value: String(value === null ? first : value) });
    var out = IX.el("output", { for: "ix-year", id: "ix-year-out" });
    var clear = IX.el("button", { type: "button", class: "ix-year-clear", text: S["ix.ctl.year_clear"] });
    var api = {
      value: value,
      box: null,
      set: function (v, silent) {
        api.value = v;
        if (v === null) {
          out.textContent = S["ix.ctl.year_off"];
          input.setAttribute("aria-valuetext", S["ix.ctl.year_off"]);
          clear.hidden = true;
        } else {
          input.value = String(v);
          var txt = IX.fmt(S["ix.ctl.year_value"], { year: v });
          out.textContent = txt;
          input.setAttribute("aria-valuetext", txt);
          clear.hidden = false;
        }
        if (!silent) onChange(v);
      }
    };
    input.addEventListener("input", function () { api.set(parseInt(input.value, 10)); });
    clear.addEventListener("click", function () { api.set(null); input.focus(); });
    api.box = IX.control(S["ix.ctl.year"], input, out, clear);
    api.input = input;
    api.set(value, true);
    return api;
  };

  IX.summary = function () {
    return IX.el("p", { class: "ix-summary", role: "status", "aria-live": "polite" });
  };

  /* A record's text, cloned from its entry in the page's text version (which the builder
     generates from the same data), without the entry's name link. null if there is none. */
  IX.recordOf = function (id) {
    var q = window.CSS && CSS.escape ? CSS.escape(id) : id.replace(/["\\]/g, "\\$&");
    var li = document.querySelector('.ix-text li[data-id="' + q + '"]');
    if (!li) return null;
    var frag = document.createDocumentFragment();
    Array.prototype.forEach.call(li.children, function (c) {
      if (!c.classList.contains("ix-alt-name") && !c.classList.contains("name-ar")) frag.appendChild(c.cloneNode(true));
    });
    return frag;
  };

  /* index: item id -> item */
  IX.byId = function (list) {
    var m = {};
    list.forEach(function (x) { m[x.id] = x; });
    return m;
  };
}());
