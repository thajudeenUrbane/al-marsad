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
 * from the page (#search-strings, from site/i18n/en.json or ar.json). The first request is
 * the index the page names in data-fetch (search-index/index.json, a manifest: the rules and
 * the shards); a query then loads the shards its longest word is filed under, from the same
 * folder (slice 11b: one file for all 8,000 names was over the page budget). A name is filed
 * under the first two letters of each word and of each word's sound skeleton; a shard that
 * grew too large is cut again by the third letter (the manifest's "split"). On an Arabic page (html
 * lang="ar") the result count picks the Arabic plural form (count_zero ... count_other)
 * and the query typed is isolated inside the sentence, whichever script it is in.
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

  // at most one edit apart: a letter changed, added or dropped, or two neighbours swapped
  function withinOne(a, b) {
    if (a === b) return true;
    var la = a.length, lb = b.length, i = 0;
    if (Math.abs(la - lb) > 1) return false;
    while (i < Math.min(la, lb) && a[i] === b[i]) i++;
    if (la === lb) {
      return a.slice(i + 1) === b.slice(i + 1) ||
        (i + 1 < la && a[i] === b[i + 1] && a[i + 1] === b[i] && a.slice(i + 2) === b.slice(i + 2));
    }
    if (la > lb) return a.slice(i + 1) === b.slice(i);
    return a.slice(i) === b.slice(i + 1);
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
        return [n - 1, n, n + 1].some(function (m) { return withinOne(q.c, s.slice(0, m)); });
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
  var RTL = document.documentElement.dir === "rtl";
  function category(n) {
    if (!RTL) return n === 1 ? "one" : "other";
    var m = n % 100;
    return n === 0 ? "zero" : n === 1 ? "one" : n === 2 ? "two" : m >= 3 && m <= 10 ? "few" : m >= 11 ? "many" : "other";
  }
  function quoted(q) { return RTL ? "\u2068" + q + "\u2069" : q; }   // first-strong isolate: Arabic or Latin query
  var ARABIC = /[\u0600-\u06ff]/; // Arabic script in the query
  var engine = null, manifest = null, timer = null, shards = {}, folder = null, runId = 0;
  var base = form.getAttribute("data-base") || "";

  // one result line, as the A-Z pages write it (render.py search_row)
  function row(it) {
    var li = document.createElement("li"), a = document.createElement("a");
    a.href = base + it.u + "/";
    a.textContent = it.n;
    li.appendChild(a);
    (it.a || []).forEach(function (n, i) {
      li.appendChild(document.createTextNode(" "));
      if (i) {
        var sep = document.createElement("span");
        sep.className = "sep";
        sep.setAttribute("aria-hidden", "true");
        sep.textContent = "/";
        li.appendChild(sep);
        li.appendChild(document.createTextNode(" "));
      }
      var s = document.createElement("span");
      s.className = "name-ar";
      s.lang = "ar";
      s.dir = "rtl";
      s.textContent = n;
      li.appendChild(s);
    });
    var meta = document.createElement("span");
    meta.className = "meta";
    meta.textContent = has(S.types, it.t) ? S.types[it.t] : it.t;
    li.appendChild(document.createTextNode(" "));
    li.appendChild(meta);
    var cov = document.createElement("span"), sr = document.createElement("span");
    cov.className = "cov";
    sr.className = "sr-only";
    sr.textContent = S.coverage_sr + " ";
    cov.appendChild(sr);
    cov.appendChild(document.createTextNode(has(S.coverage, it.v) ? S.coverage[it.v] : S.coverage[""]));
    li.appendChild(document.createTextNode(" "));
    li.appendChild(cov);
    return li;
  }

  // the shards a query needs: its longest word's first two letters, as written and as sounded
  function wanted(q) {
    var skip = new Set(manifest.skip), best = "";
    engine.normalise(q).split(" ").forEach(function (w) {
      if (w.length >= 2 && !skip.has(w) && w.length > best.length) best = w;
    });
    if (!best) return null;
    var keys = [];
    // a shard that grew too large is cut by a third letter (manifest.split): a longer word loads
    // its piece, a two-letter word every piece
    function add(w) {
      var two = w.slice(0, 3), three = w.slice(0, 4);
      if (has(manifest.split, two)) {
        if (w.length >= 4) keys.push(three);
        else keys = keys.concat(manifest.split[two], [two]);
      } else {
        keys.push(two);
      }
    }
    add("n" + best);
    var sk = engine.skeletonWords(best)[0] || "";
    if (sk.length >= 2) add("s" + sk);
    return keys.filter(function (k, i) { return has(manifest.shards, k) && keys.indexOf(k) === i; });
  }

  // a shard's file: its key with every character outside a-z and 0-9 as _<hex> (build.py shard_file)
  function file(k) {
    var out = "";
    for (var c of k) out += /[a-z0-9]/i.test(c) && c.charCodeAt(0) < 128 ? c : "_" + c.codePointAt(0).toString(16);
    return out + ".json";
  }

  function shard(k) {
    if (!shards[k]) {
      shards[k] = fetch(new URL(file(k), folder).href)
        .then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
        .then(function (d) {
          return engine.prepare(d.items).map(function (p, i) { p.it = d.items[i]; return p; });
        });
      shards[k].catch(function () { delete shards[k]; });
    }
    return shards[k];
  }

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
    list.slice(0, LIMIT).forEach(function (f) { ul.appendChild(row(f[2])); });
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
    var keys = wanted(q);
    if (!keys) {
      status.textContent = S.short;
      results.hidden = true;
      empty.hidden = true;
      all.hidden = false;
      return;
    }
    var mine = ++runId;
    Promise.all(keys.map(shard)).then(function (lists) {
      if (mine !== runId) return;   // a later keystroke has its own search
      var seen = {}, items = [];
      lists.forEach(function (l) {
        l.forEach(function (p) { if (!seen[p.u]) { seen[p.u] = p; items.push(p); } });
      });
      items.sort(function (a, b) { return a.it.o - b.it.o; });   // index order, so ties rank as over the whole index
      show(q, engine.search(items, q).map(function (f) { return [f[0], f[1], seen[f[0]].it]; }));
    }, function () {
      if (mine === runId) status.textContent = fmt(S.none, { q: quoted(q) });
    });
  }

  function show(q, found) {
    all.hidden = true;
    if (!found.length) {
      status.textContent = fmt(S.none, { q: quoted(q) });
      results.hidden = true;
      empty.hidden = false;
      return;
    }
    empty.hidden = true;
    status.textContent = fmt(S["count_" + category(found.length)] || S.count_other, { n: found.length, q: quoted(q) });
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
      manifest = data;
      folder = new URL(form.getAttribute("data-fetch"), location.href).href;
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
