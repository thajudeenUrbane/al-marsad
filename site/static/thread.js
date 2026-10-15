/* "Follow the thread" on person and group pages: a progressive enhancement.
 *
 * A port of the person thread in generation-1/wider-network.template.html. Without this
 * file the page is complete: every event, story and tie is listed with its links, its
 * status and its source. With it, the "Follow the thread" button opens a view of
 * everything recorded for the person, in order: dated events by the earliest day recorded
 * for them; then the stories in reading order (no date is recorded for them, so they are
 * never placed in time); then undated events, ties to people and groups, and places.
 * Everyone who shares a moment is a link to their page; following it moves the thread on
 * to them in place, and the path so far stays at the top. Back and forward step through
 * the path, the address (#thread=<type>/<id>) can be shared, and a modified click (a new
 * tab, say) is left to the browser. Escape or the close button returns to the page.
 *
 * Every visible string and all the data come from thread.json (site/thread.py, built from
 * the graph and site/i18n/en.json) or from the page; this file holds neither. The only
 * request is the file the page names in data-fetch, on the same site.
 */
(function () {
  "use strict";
  var root = document.getElementById("thread-root");
  var main = document.getElementById("main");
  if (!root || !main || !window.fetch || !window.history || !history.pushState) return;
  var article = main.querySelector("article");
  var openBtn = root.querySelector(".thread-open");
  var status = root.querySelector(".thread-status");
  if (!article || !openBtn) return;

  var base = root.getAttribute("data-base") || "";
  var selfKey = root.getAttribute("data-self");
  var pageTitle = document.title;
  var FOLLOW = { person: true, group: true };
  var LIMIT = 12;   // people shown per moment before "Show N more"
  var D = null, S = null, byKey = {}, touching = [], loading = null, view = null, trail = [];

  // ------------------------------------------------------------------ data
  function has(obj, k) { return Object.prototype.hasOwnProperty.call(obj, k); }
  function fmt(s, v) { return String(s).replace(/\{(\w+)\}/g, function (m, k) { return has(v, k) ? String(v[k]) : m; }); }
  function kind(i) { return D.k[D.e[i][0]]; }
  function key(i) { return kind(i) + "/" + D.e[i][1]; }
  function name(i) { return D.e[i][2]; }
  function when(i) { return D.e[i][3] || ""; }
  function day(i) { return D.e[i][4] || ""; }
  function num(i) { return typeof D.e[i][5] === "number" ? D.e[i][5] : Infinity; }
  function href(i) { return base + key(i) + "/"; }
  function isMoment(i) { var k = kind(i); return k === "event" || k === "story"; }

  function prepare(data) {
    D = data;
    S = data.s;
    for (var i = 0; i < D.e.length; i++) { byKey[key(i)] = i; touching.push([]); }
    D.c.forEach(function (c, n) { touching[c[0]].push(n); touching[c[1]].push(n); });
  }

  function load() {
    if (!loading) {
      loading = fetch(root.getAttribute("data-fetch"))
        .then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
        .then(prepare);
      loading.catch(function () { loading = null; });   // a later click may try again
    }
    return loading;
  }

  // One moment per event or story the person is linked to, one per person, group or
  // place they are tied to; every claim or link behind it is a line of the moment.
  function moments(f) {
    var by = {}, all = [];
    touching[f].forEach(function (n) {
      var c = D.c[n], o = c[0] === f ? c[1] : c[0];
      if (!by[o]) { by[o] = { o: o, lines: [] }; all.push(by[o]); }
      by[o].lines.push(n);
    });
    var g = { dated: [], stories: [], undated: [], people: [], places: [] };
    all.forEach(function (m) {
      var k = kind(m.o);
      if (isMoment(m.o)) g[day(m.o) ? "dated" : k === "story" ? "stories" : "undated"].push(m);
      else g[k === "place" ? "places" : "people"].push(m);
    });
    var byIndex = function (a, b) { return a.o - b.o; };   // the index is in A-Z order within a type
    g.dated.sort(function (a, b) { return day(a.o) < day(b.o) ? -1 : day(a.o) > day(b.o) ? 1 : a.o - b.o; });
    g.stories.sort(function (a, b) { return num(a.o) - num(b.o) || a.o - b.o; });
    g.undated.sort(byIndex);
    g.people.sort(byIndex);
    g.places.sort(byIndex);
    return g;
  }

  function alsoHere(e, f) {
    var seen = {}, out = [];
    touching[e].forEach(function (n) {
      var c = D.c[n], o = c[0] === e ? c[1] : c[0];
      if (o !== f && FOLLOW[kind(o)] && !seen[o]) { seen[o] = true; out.push(o); }
    });
    return out.sort(function (a, b) { return a - b; });
  }

  // ------------------------------------------------------------------ drawing
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  function link(i, cls) {
    var a = el("a", cls, name(i));
    a.href = href(i);
    if (FOLLOW[kind(i)]) a.setAttribute("data-follow", key(i));
    return a;
  }

  // The claim as a short sentence: the moment's own record is its title and the person
  // whose thread it is goes without saying, unless the claim runs towards them.
  function sentence(n, f, m) {
    var c = D.c[n], words = [];
    if (c[0] !== f && c[0] !== m.o) words.push(name(c[0]));
    words.push(D.l[c[2]]);
    if (c[1] !== m.o && (c[1] !== f || c[0] !== f)) words.push(name(c[1]));
    return words.join(" ");
  }

  function claimNodes(n, f, m, box) {
    var c = D.c[n];
    box.appendChild(el("p", "m-line", sentence(n, f, m)));
    if (c[4] && D.o[c[4]]) box.appendChild(el("p", "m-role", D.o[c[4]]));
    var meta = el("p", "m-meta");
    var st = D.t[c[3]];
    meta.appendChild(el("span", "status status-" + st[0], st[1]));
    if (c[5] && D.u[c[5]]) { meta.appendChild(document.createTextNode(" ")); meta.appendChild(el("span", "m-src", D.u[c[5]])); }
    box.appendChild(meta);
  }

  function alsoNode(list) {
    var p = el("p", "m-also");
    p.appendChild(el("span", "m-also-label", S.also));
    list.forEach(function (o, n) {
      var a = link(o, "chip");
      if (n >= LIMIT) a.hidden = true;
      p.appendChild(a);
    });
    if (list.length > LIMIT) {
      var more = el("button", "m-more", fmt(S.more, { n: list.length - LIMIT }));
      more.type = "button";
      more.addEventListener("click", function () {
        var hidden = p.querySelectorAll("a[hidden]");
        for (var i = 0; i < hidden.length; i++) hidden[i].hidden = false;
        if (hidden.length) hidden[0].focus();
        p.removeChild(more);
      });
      p.appendChild(more);
    }
    return p;
  }

  function momentNode(m, f, n) {
    var li = el("li", "moment m-" + kind(m.o));
    li.style.animationDelay = Math.min(n, 12) * 35 + "ms";
    var places = (D.p[String(m.o)] || []);
    if (when(m.o) || places.length) {
      var head = el("p", "m-when");
      if (when(m.o)) head.appendChild(el("span", "m-date", when(m.o)));
      places.forEach(function (p) { head.appendChild(link(p, "m-place")); });
      li.appendChild(head);
    }
    var h = el("h3", "m-title");
    h.appendChild(link(m.o));
    li.appendChild(h);
    m.lines.forEach(function (c) { claimNodes(c, f, m, li); });
    if (isMoment(m.o)) {
      var also = alsoHere(m.o, f);
      if (also.length) li.appendChild(alsoNode(also));
    }
    return li;
  }

  function render(f) {
    if (!view) {
      view = el("section", "thread-view");
      view.id = "thread-view";
      view.tabIndex = -1;
      view.setAttribute("aria-labelledby", "thread-h");
      view.addEventListener("click", onClick);
      view.addEventListener("keydown", function (ev) { if (ev.key === "Escape") close(true); });
      main.insertBefore(view, article);
    }
    view.textContent = "";
    view.hidden = false;
    article.hidden = true;

    var bar = el("div", "thread-bar");
    var shut = el("button", "thread-close", S.close);
    shut.type = "button";
    shut.addEventListener("click", function () { close(true); });
    bar.appendChild(shut);
    view.appendChild(bar);
    view.appendChild(el("p", "kicker", S.kicker));
    var h1 = el("h1", null, name(f));
    h1.id = "thread-h";
    view.appendChild(h1);
    if (key(f) !== selfKey) {
      var page = el("a", "thread-page", fmt(S.open_page, { name: name(f) }));
      page.href = href(f);
      var pp = el("p");
      pp.appendChild(page);
      view.appendChild(pp);
    }
    if (trail.length > 1) {
      var nav = el("nav", "thread-path");
      nav.setAttribute("aria-label", S.path);
      nav.appendChild(el("span", "thread-path-label", S.path));
      var ol = el("ol");
      trail.forEach(function (t, n) {
        var li = el("li");
        if (n === trail.length - 1) {
          var cur = el("span", null, name(t));
          cur.setAttribute("aria-current", "step");
          li.appendChild(cur);
        } else {
          var back = link(t);
          back.setAttribute("data-step", String(n));
          li.appendChild(back);
        }
        ol.appendChild(li);
      });
      nav.appendChild(ol);
      view.appendChild(nav);
    }

    var g = moments(f);
    var total = g.dated.length + g.stories.length + g.undated.length + g.people.length + g.places.length;
    if (!total) {
      view.appendChild(el("p", "not-recorded", fmt(S.none, { name: name(f) })));
    } else {
      view.appendChild(el("p", "thread-lead", fmt(total === 1 ? S["lead.one"] : S["lead.other"], { n: total })));
      var n = 0;
      [["dated", "group_dated"], ["stories", "group_stories"], ["undated", "group_undated"],
       ["people", "group_people"], ["places", "group_places"]].forEach(function (pair) {
        var list = g[pair[0]];
        if (!list.length) return;
        view.appendChild(el("h2", "thread-group", S[pair[1]]));
        var line = el("ol", "thread-line");
        list.forEach(function (m) { line.appendChild(momentNode(m, f, n++)); });
        view.appendChild(line);
      });
    }
    view.appendChild(el("p", "thread-note note", S.note));
    document.title = fmt(S.title, { name: name(f) });
    view.focus();
    view.scrollIntoView({ block: "start" });
  }

  // ------------------------------------------------------------------ moving along
  function hashFor(f) {
    return key(f) === selfKey ? "#thread" : "#thread=" + key(f);
  }

  function go(t, how) {
    trail = t;
    var f = t[t.length - 1];
    var state = { thread: t.map(key) };
    if (how === "push") history.pushState(state, "", hashFor(f));
    else if (how === "replace") history.replaceState(state, "", hashFor(f));
    render(f);
  }

  function follow(i) {
    var at = trail.indexOf(i);
    go(at >= 0 ? trail.slice(0, at + 1) : trail.concat([i]), "push");
  }

  function close(push) {
    if (view) view.hidden = true;
    article.hidden = false;
    document.title = pageTitle;
    if (push) history.pushState(null, "", location.pathname + location.search);
    openBtn.focus();
  }

  function onClick(ev) {
    var a = ev.target.closest ? ev.target.closest("a[data-follow]") : null;
    if (!a || ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    var i = byKey[a.getAttribute("data-follow")];
    if (i === undefined) return;
    ev.preventDefault();
    follow(i);
  }

  function failed() {
    status.textContent = root.getAttribute("data-failed");
    openBtn.disabled = false;
  }

  function start(target, how) {
    openBtn.disabled = true;
    status.textContent = root.getAttribute("data-loading");
    load().then(function () {
      openBtn.disabled = false;
      status.textContent = "";
      var self = byKey[selfKey];
      if (self === undefined) return failed();
      var t = [self];
      if (target !== undefined && target !== self) t.push(target);
      go(t, how);
    }, failed);
  }

  function fromHash() {
    var m = /^#thread(?:=([a-z]+\/[0-9A-Za-z]+))?$/.exec(location.hash);
    return m ? { key: m[1] || selfKey } : null;
  }

  root.hidden = false;
  openBtn.addEventListener("click", function () { start(undefined, "push"); });
  openBtn.addEventListener("pointerenter", load, { once: true });   // fetch while the pointer is on its way
  window.addEventListener("popstate", function (ev) {
    var st = ev.state;
    if (st && st.thread) {
      load().then(function () {
        var t = st.thread.map(function (k) { return byKey[k]; }).filter(function (i) { return i !== undefined; });
        if (t.length) go(t, null);
        else close(false);
      }, failed);
    } else if (view && !view.hidden) {
      close(false);
    }
  });
  var initial = fromHash();
  if (initial) {
    load().then(function () { start(byKey[initial.key], "replace"); }, failed);
  }
})();
