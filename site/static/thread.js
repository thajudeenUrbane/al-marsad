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
 * Every visible string and all the data come from the thread files (site/thread.py, built from
 * the graph and site/i18n/en.json or ar.json) or from the page; this file holds neither.
 * The first request is the file the page names in data-fetch; following someone loads their
 * file, thread/<type>/<id>.json, the one their own page names, on the same site. Files merge:
 * an entity keeps the index it has in the whole index, in every file.
 *
 * On an Arabic page (html lang="ar", thread.json from ar.json) the recorded names stay as
 * recorded: each is marked lang="en" dir="ltr" (or isolated inside a sentence), and the
 * count in the lead picks the Arabic plural form (zero, one, two, few, many, other).
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

  var AR = document.documentElement.lang === "ar";
  var base = root.getAttribute("data-base") || "";
  var selfKey = root.getAttribute("data-self");
  var pageTitle = document.title;
  var FOLLOW = { person: true, group: true };
  var LIMIT = 12;   // people shown per moment before "Show N more"
  var D = null, S = null, byKey = {}, touching = {}, loaded = {}, seenClaim = {}, view = null, trail = [];

  // ------------------------------------------------------------------ data
  function has(obj, k) { return Object.prototype.hasOwnProperty.call(obj, k); }
  function fmt(s, v) { return String(s).replace(/\{(\w+)\}/g, function (m, k) { return has(v, k) ? String(v[k]) : m; }); }
  function kind(i) { return D.k[D.e[i][0]]; }
  function key(i) { return kind(i) + "/" + D.e[i][1]; }
  function name(i) { return D.e[i][2]; }
  function iso(s) { return AR ? "\u2066" + s + "\u2069" : s; }   // a recorded name inside a sentence keeps its direction
  function data(n) { if (AR) { n.setAttribute("lang", "en"); n.setAttribute("dir", "ltr"); } return n; }
  function category(n) {
    if (!AR) return n === 1 ? "one" : "other";
    var m = n % 100;
    return n === 0 ? "zero" : n === 1 ? "one" : n === 2 ? "two" : m >= 3 && m <= 10 ? "few" : m >= 11 ? "many" : "other";
  }
  function when(i) { return D.e[i][3] || ""; }
  function day(i) { return D.e[i][4] || ""; }
  function num(i) { return typeof D.e[i][5] === "number" ? D.e[i][5] : Infinity; }
  function href(i) { return base + key(i) + "/"; }
  function isMoment(i) { var k = kind(i); return k === "event" || k === "story"; }

  // A file: {s: strings, k: kinds, e: {index: row}, p: {moment: [place]}, c: [[subject, object,
  // label, status, role, source, ai]] where label, status, role and source index the file's
  // tables l, t ([key, text]), o and u (a source is text, or [index in h, the rest]: h holds the
  // edition a citation names before its place); x: {moment: [how many others, [some of them]]}}
  function merge(data) {
    if (!D) { D = { k: data.k, e: {}, p: {}, c: [], x: {} }; S = data.s; }
    Object.keys(data.e).forEach(function (i) {
      if (!has(D.e, i)) { D.e[i] = data.e[i]; byKey[key(+i)] = +i; touching[i] = touching[i] || []; }
    });
    Object.keys(data.p).forEach(function (m) { D.p[m] = data.p[m]; });
    Object.keys(data.x).forEach(function (m) { if (!has(D.x, m)) D.x[m] = data.x[m]; });
    data.c.forEach(function (row) {
      // the file's tables resolved, so rows from different files compare and merge
      var u = data.u[row[5]];
      if (Array.isArray(u)) u = data.h[u[0]] + u[1];   // the edition, written once per file, and the place in it
      var c = [row[0], row[1], data.l[row[2]], data.t[row[3]], data.o[row[4]], u, row[6]];
      var sig = JSON.stringify(c);
      if (seenClaim[sig]) return;
      seenClaim[sig] = true;
      var n = D.c.push(c) - 1;
      touching[c[0]].push(n);
      if (c[1] !== c[0]) touching[c[1]].push(n);
    });
  }

  // the file for a person or group, once; url is the page's own data-fetch for itself
  function load(k, url) {
    k = k || selfKey;
    if (!loaded[k]) {
      loaded[k] = fetch(url || (k === selfKey ? root.getAttribute("data-fetch") : base + "thread/" + k + ".json"))
        .then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
        .then(merge);
      loaded[k].catch(function () { delete loaded[k]; });   // a later click may try again
    }
    return loaded[k];
  }
  function loadAll(keys) { return Promise.all([load()].concat(keys.map(function (k) { return load(k); }))); }

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
    all.forEach(function (m) { m.o = +m.o; });
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

  // who else shares a moment: the file lists some of them and how many there are in all
  function alsoHere(e, f) {
    var x = D.x[String(e)] || [0, []];
    var list = x[1].filter(function (o) { return o !== f && has(D.e, String(o)); });
    return { list: list, total: Math.max(x[0], list.length) };
  }

  // ------------------------------------------------------------------ drawing
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  function link(i, cls) {
    var a = data(el("a", cls, name(i)));
    a.href = href(i);
    if (FOLLOW[kind(i)]) a.setAttribute("data-follow", key(i));
    return a;
  }

  // The claim as a short sentence: the moment's own record is its title and the person
  // whose thread it is goes without saying, unless the claim runs towards them.
  function sentence(n, f, m) {
    var c = D.c[n], words = [];
    if (c[0] !== f && c[0] !== m.o) words.push([name(c[0]), true]);
    words.push([c[2], false]);
    if (c[1] !== m.o && (c[1] !== f || c[0] !== f)) words.push([name(c[1]), true]);
    return words;
  }

  function sentenceNode(words) {
    var p = el("p", "m-line");
    if (!AR) { p.textContent = words.map(function (w) { return w[0]; }).join(" "); return p; }
    if (words.some(function (w) { return !w[1] && w[0].charAt(0) === "⁦"; })) {
      // the relation is recorded in English, so the whole sentence is English
      p.textContent = words.map(function (w) { return w[0].replace(/[⁦⁩]/g, ""); }).join(" ");
      return data(p);
    }
    words.forEach(function (w, i) {
      if (i) p.appendChild(document.createTextNode(" "));
      if (w[1]) p.appendChild(data(el("span", null, w[0])));
      else p.appendChild(document.createTextNode(w[0]));
    });
    return p;
  }

  function claimNodes(n, f, m, box) {
    var c = D.c[n];
    box.appendChild(sentenceNode(sentence(n, f, m)));
    if (c[4]) box.appendChild(el("p", "m-role", c[4]));
    var meta = el("p", "m-meta");
    var st = c[3];
    meta.appendChild(el("span", "status status-" + st[0], st[1]));
    if (c[5]) { meta.appendChild(document.createTextNode(" ")); meta.appendChild(el("span", "m-src", c[5])); }
    box.appendChild(meta);
  }

  // the others the file lists, then a link to the moment's own page, which names everyone
  function alsoNode(also, m) {
    var p = el("p", "m-also");
    p.appendChild(el("span", "m-also-label", S.also));
    also.list.slice(0, LIMIT).forEach(function (o) { p.appendChild(link(o, "chip")); });
    var rest = also.total - Math.min(also.list.length, LIMIT);
    if (rest > 0) {
      var more = el("a", "m-more", fmt(S.more, { n: rest }));
      more.href = href(m);
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
      if (when(m.o)) {
        var date = el("span", "m-date", when(m.o));
        if (AR) date.setAttribute("dir", "auto");
        head.appendChild(date);
      }
      places.forEach(function (p) { head.appendChild(link(p, "m-place")); });
      li.appendChild(head);
    }
    var h = el("h3", "m-title");
    h.appendChild(link(m.o));
    li.appendChild(h);
    m.lines.forEach(function (c) { claimNodes(c, f, m, li); });
    if (isMoment(m.o)) {
      var also = alsoHere(m.o, f);
      if (also.list.length) li.appendChild(alsoNode(also, m.o));
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
    var h1 = data(el("h1", null, name(f)));
    h1.id = "thread-h";
    view.appendChild(h1);
    if (key(f) !== selfKey) {
      var page = el("a", "thread-page", fmt(S.open_page, { name: iso(name(f)) }));
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
          var cur = data(el("span", null, name(t)));
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
      view.appendChild(el("p", "not-recorded", fmt(S.none, { name: iso(name(f)) })));
    } else {
      view.appendChild(el("p", "thread-lead", fmt(S["lead." + category(total)] || S["lead.other"], { n: total })));
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
    document.title = fmt(S.title, { name: iso(name(f)) });
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
    status.textContent = root.getAttribute("data-loading");
    load(key(i)).then(function () {
      status.textContent = "";
      go(at >= 0 ? trail.slice(0, at + 1) : trail.concat([i]), "push");
    }, failed);
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
    loadAll(target ? [target] : []).then(function () {
      openBtn.disabled = false;
      status.textContent = "";
      var self = byKey[selfKey];
      if (self === undefined) return failed();
      var t = [self], to = target ? byKey[target] : undefined;
      if (to !== undefined && to !== self) t.push(to);
      go(t, how);
    }, failed);
  }

  function fromHash() {
    var m = /^#thread(?:=([a-z]+\/[0-9A-Za-z]+))?$/.exec(location.hash);
    return m ? { key: m[1] || selfKey } : null;
  }

  root.hidden = false;
  openBtn.addEventListener("click", function () { start(undefined, "push"); });
  openBtn.addEventListener("pointerenter", function () { load(); }, { once: true });   // fetch while the pointer is on its way
  window.addEventListener("popstate", function (ev) {
    var st = ev.state;
    if (st && st.thread) {
      loadAll(st.thread).then(function () {
        var t = st.thread.map(function (k) { return byKey[k]; }).filter(function (i) { return i !== undefined; });
        if (t.length) go(t, null);
        else close(false);
      }, failed);
    } else if (view && !view.hidden) {
      close(false);
    }
  });
  function openFromHash() {
    var wanted = fromHash();
    if (wanted) start(wanted.key === selfKey ? undefined : wanted.key, "replace");
  }
  window.addEventListener("hashchange", openFromHash);   // a #thread address typed or linked on this page
  openFromHash();
})();
