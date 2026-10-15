/* Name search for the reader tier, a progressive enhancement of the search page.
 *
 * Without this file the site is complete: the search box on every page submits to
 * search/, which lists every name from A to Z. With it, the search page filters that
 * list as you type and shows the matching lines.
 *
 * makeEngine() is a step-for-step port of site/names.py (normalise, skeleton, search).
 * It holds no table of its own: every table comes from search.json ("rules"), which
 * site/build.py writes from names.RULES. site/tests/test_search.py runs this file and
 * the Python on the same cases and fails on any difference. Every visible string comes
 * from the page (#search-strings, from site/i18n/en.json). The only request is the
 * index the page names in data-fetch, on the same site.
 */
(function () {
  "use strict";

  function has(obj, k) {
    return Object.prototype.hasOwnProperty.call(obj, k);
  }

  function collapse(s) {
    var out = "";
    for (var i = 0; i < s.length; i++) if (i === 0 || s[i] !== s[i - 1]) out += s[i];
    return out;
  }

  function osa(a, b) {
    var d = [], i, j;
    for (i = 0; i <= a.length; i++) {
      d.push(new Array(b.length + 1).fill(0));
      d[i][0] = i;
    }
    for (j = 0; j <= b.length; j++) d[0][j] = j;
    for (i = 1; i <= a.length; i++) {
      for (j = 1; j <= b.length; j++) {
        var cost = a[i - 1] === b[j - 1] ? 0 : 1;
        d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost);
        if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
          d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
        }
      }
    }
    return d[a.length][b.length];
  }

  function makeEngine(R) {
    var drop = new Set(Array.from(R.drop));
    var nonword = new RegExp(R.nonword, "g");
    var articles = new Set(R.articles);
    var lone = new Set(R.lone_articles);
    var abd = new RegExp(R.abd);
    var keep = new RegExp(R.sk_keep);
    var marks = /\p{M}/gu;
    var NO_MATCH = R.tiers;

    function normalise(text) {
      var s = "", t = "";
      for (var ch of text) if (!drop.has(ch)) s += ch;
      s = s.normalize("NFKD").replace(marks, "").toLowerCase();
      for (var c of s) t += has(R.chars, c) ? R.chars[c] : c;
      t = t.replace(nonword, " ");
      var words = [], out = [];
      t.split(" ").forEach(function (raw) {
        var parts = raw.split("-").filter(Boolean);
        parts.forEach(function (p, i) {
          if (!(i < parts.length - 1 && articles.has(p))) words.push(p);
        });
      });
      words.forEach(function (w, i) {
        var more = i < words.length - 1;
        if (more && lone.has(w)) return;
        if (w.indexOf(R.ar_article) === 0 && w.length >= 4) w = w.slice(2);
        if (more) {
          if (has(R.particles, w)) w = R.particles[w];
          else if (abd.test(w)) w = "abd";
        }
        out.push(w);
      });
      return out.join(" ");
    }

    function skeletonWords(normal) {
      var out = [];
      normal.split(" ").forEach(function (w) {
        var k = "", i = 0;
        while (i < w.length) {
          var two = w.slice(i, i + 2);
          if (has(R.sk_digraphs, two)) {
            k += R.sk_digraphs[two];
            i += 2;
            continue;
          }
          var ch = w[i];
          if (has(R.sk_chars, ch)) k += R.sk_chars[ch];
          else if (keep.test(ch)) k += ch;
          i += 1;
        }
        k = collapse(k);
        if (k.length > 1 && k[k.length - 1] === "h") k = k.slice(0, -1);
        if (k) out.push(k);
      });
      return out;
    }

    function skeleton(normal) {
      return collapse(skeletonWords(normal).join(""));
    }

    function key(normal) {
      var words = normal.split(" ").filter(Boolean), csufs = [], sufs = [], i;
      var sw = skeletonWords(normal);
      for (i = 0; i < words.length; i++) csufs.push(words.slice(i).join(""));
      for (i = 0; i < sw.length; i++) sufs.push(collapse(sw.slice(i).join("")));
      return { c: words.join(""), words: words, csufs: csufs, sk: collapse(sw.join("")), sufs: sufs };
    }

    function near(q, k) {
      var n = q.c.length;
      if (n < R.min_near) return false;
      return k.csufs.some(function (s) {
        return [n - 1, n, n + 1].some(function (m) { return osa(q.c, s.slice(0, m)) <= 1; });
      });
    }

    function tier(q, k) {
      if (q.c === k.c) return 0;
      if (k.c.indexOf(q.c) === 0) return 1;
      if (q.words.every(function (qw) {
        return k.words.some(function (kw) { return kw.indexOf(qw) === 0; });
      })) return 2;
      if (q.c.length >= R.min_inside && k.c.indexOf(q.c) >= 0) return 3;
      if (q.sk && q.sk === k.sk) return 4;
      if (q.sk.length >= R.min_sound_start && k.sk.indexOf(q.sk) === 0) return 5;
      if (near(q, k)) return 6;
      if (q.sk.length >= R.min_sound_start && k.sufs.some(function (s) { return s.indexOf(q.sk) === 0; })) return 7;
      if (q.sk.length >= R.min_inside && k.sk.indexOf(q.sk) >= 0) return 8;
      return NO_MATCH;
    }

    function prepare(items) {
      return items.map(function (it) {
        return { u: it.u, keys: it.k.map(function (k) { return key(k); }) };
      });
    }

    function search(items, query) {
      var q = key(normalise(query)), found = [];
      if (!q.c) return [];
      items.forEach(function (it, pos) {
        var tiers = it.keys.map(function (k) { return [tier(q, k), k.c.length]; });
        var best = tiers.reduce(function (a, b) { return b[0] < a[0] || (b[0] === a[0] && b[1] < a[1]) ? b : a; });
        if (best[0] < NO_MATCH) found.push([best[0], tiers[0][0], best[1], pos]); // tiers[0]: the name as shown
      });
      found.sort(function (a, b) { return a[0] - b[0] || a[1] - b[1] || a[2] - b[2] || a[3] - b[3]; });
      return found.map(function (f) { return [items[f[3]].u, f[0]]; });
    }

    return { normalise: normalise, skeleton: skeleton, skeletonWords: skeletonWords,
             prepare: prepare, search: search, similarFrom: R.similar_from };
  }

  if (typeof module === "object" && module.exports) {
    module.exports = { makeEngine: makeEngine };
    return;
  }

  // ------------------------------------------------------------------ the page
  var form = document.getElementById("search-form");
  if (!form || !window.fetch || !String.prototype.normalize || !window.URLSearchParams) return;
  var input = document.getElementById("search-q");
  var status = document.getElementById("search-status");
  var results = document.getElementById("search-results");
  var empty = document.getElementById("search-empty");
  var all = document.getElementById("search-all");
  var nojs = document.getElementById("search-nojs");
  var S = JSON.parse(document.getElementById("search-strings").textContent);
  var LIMIT = 50;
  var ARABIC = /[\u0600-\u06ff]/; // Arabic script in the query
  var engine = null, items = null, timer = null;

  // the A-Z lines already on the page, by their url path ("person/ID")
  var rows = new Map();
  all.querySelectorAll(".index-list li").forEach(function (li) {
    var a = li.querySelector("a");
    if (a) rows.set(a.getAttribute("href").replace(/^(\.\.\/)+/, "").replace(/\/$/, ""), li);
  });

  function fmt(s, v) {
    return s.replace(/\{(\w+)\}/g, function (m, k) { return has(v, k) ? String(v[k]) : m; });
  }

  function para(text) {
    var p = document.createElement("p");
    p.className = "note";
    p.textContent = text;
    return p;
  }

  function group(title, list, notes) {
    var h = document.createElement("h2");
    h.textContent = fmt(title, { n: list.length });
    results.appendChild(h);
    notes.forEach(function (n) { results.appendChild(para(n)); });
    var ul = document.createElement("ul");
    ul.className = "index-list";
    list.slice(0, LIMIT).forEach(function (f) {
      var li = rows.get(f[0]);
      if (li) ul.appendChild(li.cloneNode(true));
    });
    results.appendChild(ul);
    if (list.length > LIMIT) results.appendChild(para(fmt(S.more, { n: LIMIT })));
  }

  function run(text, updateUrl) {
    var q = text.trim();
    if (updateUrl && window.history && history.replaceState) {
      history.replaceState(null, "", q ? "?q=" + encodeURIComponent(q) : location.pathname);
    }
    results.textContent = "";
    if (!q) {
      status.textContent = "";
      results.hidden = true;
      empty.hidden = true;
      all.hidden = false;
      return;
    }
    var found = engine.search(items, q);
    all.hidden = true;
    if (!found.length) {
      status.textContent = fmt(S.none, { q: q });
      results.hidden = true;
      empty.hidden = false;
      return;
    }
    empty.hidden = true;
    status.textContent = fmt(found.length === 1 ? S.count_one : S.count_other, { n: found.length, q: q });
    var close = found.filter(function (f) { return f[1] < engine.similarFrom; });
    var similar = found.filter(function (f) { return f[1] >= engine.similarFrom; });
    if (close.length) group(S.matching, close, []);
    if (similar.length) group(S.similar, similar, [S.similar_note].concat(ARABIC.test(q) ? [S.arabic_note] : []));
    results.hidden = false;
  }

  form.addEventListener("submit", function (ev) {
    if (!engine) return; // not ready: let the browser load search/?q=... instead
    ev.preventDefault();
    clearTimeout(timer);
    run(input.value, true);
  });

  fetch(form.getAttribute("data-fetch"))
    .then(function (r) {
      if (!r.ok) throw new Error(String(r.status));
      return r.json();
    })
    .then(function (data) {
      engine = makeEngine(data.rules);
      items = engine.prepare(data.items);
      nojs.hidden = true;
      input.value = new URLSearchParams(location.search).get("q") || "";
      run(input.value, false);
      input.addEventListener("input", function () {
        clearTimeout(timer);
        timer = setTimeout(function () { run(input.value, true); }, 150);
      });
    })
    .catch(function () { /* the note and the A-Z list stay: the page works as without JavaScript */ });
})();
