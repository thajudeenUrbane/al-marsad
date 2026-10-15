/* al-Marṣad — ask the graph, in the browser.
 *
 * A port of ask/normalise.py (with site/names.py's normalise and skeleton_words, whose
 * tables it reads from the index), ask/dsl.py, ask/translate.py and ask/present.py.
 * ask/tests/test_parity.py runs both on the golden set and on extra
 * questions and requires the same answer objects and the same HTML. The rules, the
 * strings and the index come from ask-index.json, built by ask/build_ask.py; nothing
 * here calls a model or any other site. Works as a progressive enhancement: without
 * JavaScript the page lists the answers built ahead of time.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.MarsadAsk = factory();
}(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function create(data) {
    var RULES = data.rules, T = data.i18n;
    var NR = RULES.normalise, LK = RULES.linking, LIMITS = RULES.limits, TIME = RULES.time;
    var E = data.entities, C = data.claims, AGENTS_TABLE = data.agents;

    // ------------------------------------------------------------------ text helpers
    function replaceAll(s, a, b) { return s.split(a).join(b); }
    function stripSpaces(s) { return s.replace(/^ +| +$/g, ""); }
    function fmt(template, kw) {
      return template.replace(/\{([a-z_]+)\}/g, function (m, k) {
        if (!(k in kw) || kw[k] === undefined || kw[k] === null) throw new Error("missing value for {" + k + "}");
        return String(kw[k]);
      });
    }
    function quote(s) { return '"' + replaceAll(replaceAll(s, "\\", "\\\\"), '"', '\\"') + '"'; }
    function esc(s) {
      s = String(s);
      return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
    }
    function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
    function sortNum(a) { return a.slice().sort(function (x, y) { return x - y; }); }
    function uniqSorted(a) {
      var s = sortNum(a), out = [];
      for (var i = 0; i < s.length; i++) if (i === 0 || s[i] !== s[i - 1]) out.push(s[i]);
      return out;
    }
    function jsonEq(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
    function pad(n, w) { var s = String(n); while (s.length < w) s = "0" + s; return s; }

    // ------------------------------------------------------------------ fold (site/display.py)
    var MARKS = data.norm.marks, CCC = data.norm.ccc;
    function combining(cp) {
      var lo = 0, hi = CCC.length - 1;
      while (lo <= hi) {
        var mid = (lo + hi) >> 1;
        if (cp < CCC[mid][0]) hi = mid - 1;
        else if (cp > CCC[mid][1]) lo = mid + 1;
        else return true;
      }
      return false;
    }
    function fold(text) {
      text = text.normalize("NFC");
      var out = "";
      for (var ch of text) {
        if (ch.length === 1 && MARKS.indexOf(ch) >= 0) { out += "'"; continue; }
        for (var c of ch.normalize("NFD")) if (!combining(c.codePointAt(0))) out += c;
      }
      return out;
    }

    // ------------------------------------------------------------------ site/names.py
    // normalise and skeleton_words, step for step; every table is names.RULES (data.norm.names)
    var SR = data.norm.names;
    var SR_DROP = Array.from(SR.drop), SR_NONWORD = new RegExp(SR.nonword, "g"), SR_ABD = new RegExp(SR.abd);
    var SR_KEEP = new RegExp(SR.sk_keep), SR_MARKS = /\p{M}/gu;
    function siteNormalise(text) {
      var s = "", t = "", words = [], out = [], i;
      for (var ch of text) if (SR_DROP.indexOf(ch) < 0) s += ch;
      s = s.normalize("NFKD").replace(SR_MARKS, "").toLowerCase();
      for (var c of s) t += has(SR.chars, c) ? SR.chars[c] : c;
      t = t.replace(SR_NONWORD, " ");
      t.split(" ").forEach(function (raw) {
        var parts = raw.split("-").filter(function (x) { return x; });
        parts.forEach(function (x, k) { if (!(k < parts.length - 1 && SR.articles.indexOf(x) >= 0)) words.push(x); });
      });
      for (i = 0; i < words.length; i++) {
        var w = words[i], more = i < words.length - 1;
        if (more && SR.lone_articles.indexOf(w) >= 0) continue;
        if (w.indexOf(SR.ar_article) === 0 && w.length >= 4) w = w.slice(2);
        if (more) {
          if (has(SR.particles, w)) w = SR.particles[w];
          else if (SR_ABD.test(w)) w = "abd";
        }
        out.push(w);
      }
      return out.join(" ");
    }
    function collapseRuns(s) {
      var out = "";
      for (var i = 0; i < s.length; i++) if (i === 0 || s[i] !== s[i - 1]) out += s[i];
      return out;
    }
    function skeletonWords(normal) {
      var out = [];
      normal.split(" ").forEach(function (w) {
        var k = "", i = 0;
        while (i < w.length) {
          var two = w.slice(i, i + 2);
          if (has(SR.sk_digraphs, two)) { k += SR.sk_digraphs[two]; i += 2; continue; }
          var ch = w[i];
          if (has(SR.sk_chars, ch)) k += SR.sk_chars[ch];
          else if (SR_KEEP.test(ch)) k += ch;
          i += 1;
        }
        k = collapseRuns(k);
        if (k.length > 1 && k[k.length - 1] === "h") k = k.slice(0, -1);
        if (k) out.push(k);
      });
      return out;
    }

    // ------------------------------------------------------------------ normalise.py
    var RX_SPACES = new RegExp(NR.spaces, "g"), RX_HON = new RegExp(NR.honorific_paren, "g");
    var RX_POSS = new RegExp(NR.possessive, "g");
    var RX_ALLAH = new RegExp("^(" + NR.allah_heads.join("|") + ")(" + NR.allah_tails.join("|") + ")$");

    function textKey(text) {
      var s = fold(text || "").toLowerCase(), i;
      for (i = 0; i < NR.arabic_map.length; i++) s = replaceAll(s, NR.arabic_map[i][0], NR.arabic_map[i][1]);
      for (var ch of NR.drop_chars) s = replaceAll(s, ch, "");
      for (i = 0; i < NR.punct_map.length; i++) s = replaceAll(s, NR.punct_map[i][0], NR.punct_map[i][1]);
      s = s.replace(RX_HON, " ");
      s = s.replace(RX_SPACES, " ");
      return stripSpaces(s);
    }
    function nameTokens(text) {
      var s = fold(text || "").toLowerCase().replace(RX_HON, " ");
      s = s.replace(RX_POSS, "");
      var words = siteNormalise(s).split(" ").filter(function (w) { return w && NR.stop_words.indexOf(w) < 0; });
      var merged = [], i = 0;
      while (i < words.length) {
        var t = words[i];
        if (NR.allah_heads.indexOf(t) >= 0 && i + 1 < words.length && NR.allah_tails.indexOf(words[i + 1]) >= 0) {
          merged.push(t + "ullah"); i += 2; continue;
        }
        var m = RX_ALLAH.exec(t);
        merged.push(m ? m[1] + "ullah" : t);
        i += 1;
      }
      return merged;
    }
    function sound(word) { var k = skeletonWords(word); return k.length ? k[0] : ""; }
    function levenshtein(a, b) {
      var prev = [], cur, i, j;
      for (j = 0; j <= b.length; j++) prev.push(j);
      for (i = 1; i <= a.length; i++) {
        cur = [i];
        for (j = 1; j <= b.length; j++) {
          var cost = a[i - 1] === b[j - 1] ? 0 : 1;
          cur.push(Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost));
        }
        prev = cur;
      }
      return prev[b.length];
    }
    function close(a, b, loose) {
      if (a === b) return true;
      var sa = sound(a);
      if (sa && sa === sound(b) && (loose || sa.length >= LK.sound_exact_min_len)) return true;
      var shortest = Math.min(a.length, b.length), limit;
      if (shortest >= LK.fuzzy_two_min_len) limit = 2;
      else if (shortest >= LK.fuzzy_one_min_len) limit = 1;
      else return false;
      if (Math.abs(a.length - b.length) > limit) return false;
      return levenshtein(a, b) <= limit;
    }
    function arrEq(a, b) {
      if (a.length !== b.length) return false;
      for (var i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
      return true;
    }
    function runInside(m, n) {
      var k = m.length;
      for (var i = 1; i < n.length - k + 1; i++) if (arrEq(n.slice(i, i + k), m)) return true;
      return false;
    }
    function allClose(m, n, loose) {
      for (var i = 0; i < m.length; i++) if (!close(m[i], n[i], loose)) return false;
      return true;
    }
    function score(m, n) {
      if (!m.length || !n.length) return 0;
      if (arrEq(m, n)) return 6;
      var k = m.length;
      if (k === n.length && allClose(m, n, false)) return 5;
      if (k <= n.length && arrEq(n.slice(0, k), m)) return 4;
      if (k <= n.length && allClose(m, n, true)) return 3;
      if (runInside(m, n)) return 2;
      var ms = m.join(""), ns = n.join("");
      if (ms === ns) return 2;
      if (ms.length >= LK.squash_prefix_min_len && ns.indexOf(ms) === 0) return 1;
      if (m.every(function (t) { return n.indexOf(t) >= 0; })) return 1;
      if (ms.length >= LK.squash_contains_min_len && ns.indexOf(ms) >= 0) return 1;
      return 0;
    }

    // ------------------------------------------------------------------ dsl.py
    var KINDS = ["person", "group", "place", "event", "story"], AGENT_KINDS = ["person", "group"];
    var NEGATIVE = ["absent_from"], PLACE_LINKS = ["took_place_at", "occurred_at"], LEFT_OUT = ["rejected", "superseded"];
    var SET_TYPES = ["agents", "events", "stories", "places"];
    var TIES = ["any", "parent", "father", "mother", "child", "spouse", "sibling"];
    var SIGS = {
      participants: { pos: ["target"], kw: { as: ["any", "leader"] }, ret: "agents" },
      people: { pos: [], kw: { at: "place", from: "year", to: "year" }, need: ["at"], ret: "agents" },
      absent: { pos: ["target"], kw: {}, ret: "agents" },
      events: { pos: [], kw: { at: "place", involving: "agent", from: "year", to: "year" }, need_any: true, ret: "events" },
      stories: { pos: [], kw: { involving: "agent" }, need: ["involving"], ret: "stories" },
      relatives: { pos: ["person"], kw: { tie: TIES.slice() }, ret: "agents" },
      connected: { pos: ["agent"], kw: { via: ["any", "ties", "events"] }, ret: "agents" },
      between: { pos: ["agent", "happening_or_place"], kw: {}, ret: "links" },
      path: { pos: ["entity", "entity"], kw: { max: "steps" }, ret: "path" },
      when: { pos: ["dated"], kw: {}, ret: "dates" },
      where: { pos: ["happening"], kw: {}, ret: "places" },
      about: { pos: ["entity"], kw: {}, ret: "about" },
      both: { pos: ["set", "set"], kw: {}, ret: "same" },
      either: { pos: ["set", "set"], kw: {}, ret: "same" },
      except: { pos: ["set", "set"], kw: {}, ret: "same" },
      count: { pos: ["set"], kw: {}, ret: "count" },
      reviewed: { pos: ["set"], kw: {}, ret: "first" }
    };
    var REF_KINDS = {
      person: ["person"], agent: ["person", "group"], place: ["place"],
      entity: ["person", "group", "place", "event", "story"],
      happening: ["event", "story"], happening_or_place: ["event", "story", "place"],
      dated: ["event", "story", "person"]
    };
    var DEFAULTS = { "participants|as": "any", "relatives|tie": "any", "connected|via": "any", "path|max": LIMITS.path_default };

    function DslError(key, params) { this.key = key; this.params = params || {}; }
    function dslErr(key, params) { return new DslError(key, params); }

    function near(tok) { return tok.t === "end" ? "" : String(tok.v); }
    function alpha(c) { return (c >= "a" && c <= "z") || (c >= "A" && c <= "Z") || c === "_"; }
    function alnum(c) { return alpha(c) || (c >= "0" && c <= "9"); }

    function scan(text) {
      var toks = [], i = 0, n = text.length, j, buf;
      while (i < n) {
        var c = text[i];
        if (" \t\n\r".indexOf(c) >= 0) { i += 1; continue; }
        if ("(),:".indexOf(c) >= 0) { toks.push({ t: c, v: c }); i += 1; continue; }
        if (c === '"') {
          j = i + 1; buf = "";
          while (j < n && text[j] !== '"') {
            if (text[j] === "\\" && j + 1 < n) { buf += text[j + 1]; j += 2; continue; }
            buf += text[j]; j += 1;
          }
          if (j >= n) throw dslErr("error.unterminated");
          toks.push({ t: "str", v: buf }); i = j + 1; continue;
        }
        if (c === "#") {
          j = i + 1;
          while (j < n && alnum(text[j]) && text[j] !== "_") j += 1;
          if (j === i + 1) throw dslErr("error.syntax", { near: "#" });
          toks.push({ t: "pid", v: text.slice(i + 1, j) }); i = j; continue;
        }
        if (c >= "0" && c <= "9") {
          j = i;
          while (j < n && text[j] >= "0" && text[j] <= "9") j += 1;
          if (j - i > 6) throw dslErr("error.number", { near: text.slice(i, j) });
          toks.push({ t: "num", v: parseInt(text.slice(i, j), 10) }); i = j; continue;
        }
        if (alpha(c)) {
          j = i;
          while (j < n && alnum(text[j])) j += 1;
          toks.push({ t: "id", v: text.slice(i, j).toLowerCase() }); i = j; continue;
        }
        throw dslErr("error.character", { near: String.fromCodePoint(text.codePointAt(i)) });
      }
      toks.push({ t: "end", v: "" });
      return toks;
    }

    function parse(text) {
      if (Array.from(text).length > LIMITS.dsl_max) throw dslErr("error.too_long");
      var toks = scan(text), pos = 0;
      function peek(k) { return toks[Math.min(pos + (k || 0), toks.length - 1)]; }
      function take() { return toks[pos++]; }
      function expect(t) {
        var tok = take();
        if (tok.t !== t) throw dslErr("error.expected", { want: t, near: near(tok) });
        return tok;
      }
      function value(depth) {
        if (depth > LIMITS.max_depth) throw dslErr("error.too_deep");
        var tok = peek(), nxt;
        if (tok.t === "id") {
          nxt = peek(1);
          if (nxt.t === "(") return call(depth);
          if (KINDS.indexOf(tok.v) >= 0 && (nxt.t === "str" || nxt.t === "pid")) {
            take(); take();
            if (nxt.t === "str") return { t: "ref", kind: tok.v, label: nxt.v };
            return { t: "ref", kind: tok.v, pid: nxt.v };
          }
          take();
          return { t: "word", w: tok.v };
        }
        if (tok.t === "num") {
          take();
          nxt = peek();
          if (nxt.t === "id" && (nxt.v === "ah" || nxt.v === "ce")) { take(); return { t: "year", n: tok.v, era: nxt.v }; }
          return { t: "num", n: tok.v };
        }
        throw dslErr("error.unexpected", { near: near(tok) });
      }
      function call(depth) {
        var name = take().v;
        expect("(");
        var args = [], kw = {};
        if (peek().t !== ")") {
          while (true) {
            if (peek().t === "id" && peek(1).t === ":") {
              var key = take().v;
              take();
              if (has(kw, key)) throw dslErr("error.duplicate", { op: name, key: key });
              kw[key] = value(depth + 1);
            } else {
              if (Object.keys(kw).length) throw dslErr("error.positional", { op: name });
              args.push(value(depth + 1));
            }
            if (peek().t === ",") { take(); continue; }
            break;
          }
        }
        expect(")");
        return { t: "op", op: name, args: args, kw: kw };
      }
      var node = value(0);
      if (peek().t !== "end") throw dslErr("error.trailing", { near: near(peek()) });
      return node;
    }

    function julianFromJdn(jdn) {
      var c = jdn + 32082, d = Math.floor((4 * c + 3) / 1461), e = c - Math.floor((1461 * d) / 4);
      var m = Math.floor((5 * e + 2) / 153), day = e - Math.floor((153 * m + 2) / 5) + 1;
      var month = m + 3 - 12 * Math.floor(m / 10), year = d - 4800 + Math.floor(m / 10);
      return pad(year, 4) + "-" + pad(month, 2) + "-" + pad(day, 2);
    }
    function ahYearStartJdn(y) { return 1948440 + 354 * (y - 1) + Math.floor((3 + 11 * y) / 30); }
    function yearBounds(n, era) {
      if (era === "ah") return [julianFromJdn(ahYearStartJdn(n)), julianFromJdn(ahYearStartJdn(n + 1) - 1)];
      return [pad(n, 4) + "-01-01", pad(n, 4) + "-12-31"];
    }

    // engine state
    var touch = E.map(function () { return []; }), byKey = {}, byRef = {};
    C.forEach(function (c, j) { touch[c.s].push(j); if (c.o !== c.s) touch[c.o].push(j); });
    E.forEach(function (e, i) {
      byRef[e.r] = i;
      e.keys.forEach(function (k) {
        var key = e.k + "|" + k.join(" ");
        if (!has(byKey, key)) byKey[key] = [];
        if (byKey[key].indexOf(i) < 0) byKey[key].push(i);
      });
    });
    function kind(i) { return E[i].k; }
    function st(c) { return has(c, "st") ? c.st : null; }
    function usable(c) { return LEFT_OUT.indexOf(st(c)) < 0; }
    function positive(c) { return c.k === "p" || (c.k === "a" && NEGATIVE.indexOf(c.p) < 0); }
    function isLeader(c) { return (c.k === "a" && c.p === "led") || (c.k === "p" && c.rk === "leader"); }
    function refText(i) {
      var e = E[i];
      if (e.u) return e.k + " " + quote(e.l);
      return e.k + " #" + e.r.split("/").slice(1).join("/");
    }

    function resolve(node) {
      var k = node.kind;
      if (has(node, "pid")) {
        var i = byRef[k + "/" + node.pid];
        if (i === undefined) throw dslErr("error.no_id", { kind: k, id: node.pid });
        return i;
      }
      var found = byKey[k + "|" + nameTokens(node.label).join(" ")] || [];
      if (!found.length) throw dslErr("error.not_found", { kind: k, label: node.label });
      if (found.length > 1) throw dslErr("error.ambiguous", { kind: k, label: node.label, n: found.length });
      return found[0];
    }

    var opsCount = 0;
    function validate(node) { opsCount = 0; return check(node, 0); }
    function argOf(op, want, node, depth, where) {
      if (Array.isArray(want)) {
        if (node.t !== "word" || want.indexOf(node.w) < 0) throw dslErr("error.word", { op: op, key: where, allowed: want.join(", ") });
        return node;
      }
      if (want === "year") {
        if (node.t !== "year") throw dslErr("error.type", { op: op, key: where, want: "year" });
        var n = node.n, era = node.era;
        var ok = era === "ah" ? (1 <= n && n <= TIME.max_ah) : (TIME.min_ce <= n && n <= TIME.max_ce);
        if (!ok) throw dslErr("error.year", { year: n + " " + era.toUpperCase() });
        var b = yearBounds(n, era);
        return { t: "year", n: n, era: era, start: b[0], end: b[1] };
      }
      if (want === "steps") {
        if (node.t !== "num" || !(1 <= node.n && node.n <= LIMITS.path_max)) throw dslErr("error.steps", { max: LIMITS.path_max });
        return node;
      }
      if (want === "target" || want === "set") {
        if (node.t === "ref" && want === "target") {
          if (node.kind !== "event" && node.kind !== "story") throw dslErr("error.type", { op: op, key: where, want: "target" });
          return { t: "ref", kind: node.kind, e: resolve(node) };
        }
        if (node.t !== "op") throw dslErr("error.type", { op: op, key: where, want: want });
        var sub = check(node, depth + 1);
        var okTypes = want === "target" ? ["events", "stories"] : SET_TYPES;
        if (okTypes.indexOf(sub.ty) < 0) throw dslErr("error.type", { op: op, key: where, want: want });
        return sub;
      }
      var kinds = REF_KINDS[want];
      if (node.t !== "ref" || kinds.indexOf(node.kind) < 0) throw dslErr("error.type", { op: op, key: where, want: want });
      return { t: "ref", kind: node.kind, e: resolve(node) };
    }
    function check(node, depth) {
      if (node.t !== "op") throw dslErr("error.not_op");
      if (depth > LIMITS.max_depth) throw dslErr("error.too_deep");
      opsCount += 1;
      if (opsCount > LIMITS.max_ops) throw dslErr("error.too_many");
      var op = node.op, sig = has(SIGS, op) ? SIGS[op] : null;
      if (!sig) throw dslErr("error.unknown_op", { op: op });
      if (node.args.length !== sig.pos.length) throw dslErr("error.arity", { op: op, n: sig.pos.length });
      var args = [], kw = {}, k;
      for (k = 0; k < sig.pos.length; k++) args.push(argOf(op, sig.pos[k], node.args[k], depth, String(k + 1)));
      Object.keys(node.kw).forEach(function (key) {
        if (!has(sig.kw, key)) throw dslErr("error.keyword", { op: op, key: key });
        kw[key] = argOf(op, sig.kw[key], node.kw[key], depth, key);
      });
      (sig.need || []).forEach(function (key) { if (!has(kw, key)) throw dslErr("error.missing", { op: op, key: key }); });
      if (sig.need_any && !Object.keys(kw).length) throw dslErr("error.filter", { op: op });
      if (has(kw, "from") && has(kw, "to") && kw.from.start > kw.to.end) throw dslErr("error.range");
      if (op === "path" && args[0].e === args[1].e) throw dslErr("error.same");
      var ret = sig.ret;
      if (ret === "same") {
        if (args[0].ty !== args[1].ty) throw dslErr("error.mixed", { op: op });
        ret = args[0].ty;
      } else if (ret === "first") ret = args[0].ty;
      return { t: "op", op: op, args: args, kw: kw, ty: ret };
    }

    function text(node) {
      var t = node.t;
      if (t === "ref") {
        if (has(node, "e")) return refText(node.e);
        if (has(node, "label")) return node.kind + " " + quote(node.label);
        return node.kind + " #" + node.pid;
      }
      if (t === "year") return node.n + " " + node.era.toUpperCase();
      if (t === "num") return String(node.n);
      if (t === "word") return node.w;
      var op = node.op, parts = node.args.map(text);
      var order = has(SIGS, op) ? Object.keys(SIGS[op].kw) : Object.keys(node.kw);
      order.forEach(function (key) {
        if (!has(node.kw, key)) return;
        var v = node.kw[key], d = DEFAULTS[op + "|" + key];
        if (d !== undefined && ((v.t === "word" && v.w === d) || (v.t === "num" && v.n === d))) return;
        parts.push(key + ": " + text(v));
      });
      return op + "(" + parts.join(", ") + ")";
    }

    // ------------------------------------------------------------------ execution
    function word(node, key) { return has(node.kw, key) ? node.kw[key].w : DEFAULTS[node.op + "|" + key]; }
    function add(rows, i, js) { if (!rows.has(i)) rows.set(i, []); Array.prototype.push.apply(rows.get(i), js); }
    function makeRows(rows, tags) {
      return sortNum(Array.from(rows.keys())).map(function (i) {
        var row = { e: i, c: uniqSorted(rows.get(i)) };
        if (tags && tags.has(i)) row.tag = tags.get(i);
        return row;
      });
    }
    function makeSet(of, rows, notes, tags, extra) {
      var res = { type: "set", of: of, rows: makeRows(rows, tags), notes: notes };
      if (extra) Object.keys(extra).forEach(function (k) { res[k] = extra[k]; });
      return res;
    }
    function targets(node) {
      if (node.t === "ref") return { list: [node.e], searched: null, notes: [] };
      var sub = execute(node);
      return { list: sub.rows.map(function (r) { return r.e; }), searched: sub.rows, notes: sub.notes };
    }
    function windowOf(node) {
      var f = has(node.kw, "from") ? node.kw.from : null, t = has(node.kw, "to") ? node.kw.to : null;
      if (!f && !t) return null;
      return { s: f ? f.start : null, e: t ? t.end : null, ah: !!((f && f.era === "ah") || (t && t.era === "ah")) };
    }
    function timeTag(ent, w) {
      var dates = ent.dates || [], starts = [], ends = [];
      dates.forEach(function (d) { if (d.s) starts.push(d.s); if (d.e) ends.push(d.e); });
      if (!starts.length || !ends.length) return "undated";
      var es = starts.slice().sort()[0], ee = ends.slice().sort()[ends.length - 1];
      var within = (w.s === null || es >= w.s) && (w.e === null || ee <= w.e);
      if (within) return "within";
      var overlaps = (w.e === null || es <= w.e) && (w.s === null || ee >= w.s);
      return overlaps ? "overlaps" : null;
    }
    function timeNotes(w, tags, undated, undatedDirect) {
      var notes = [];
      if (w === null) return notes;
      if (w.ah) notes.push({ key: "note.time_ah" });
      var n = 0;
      tags.forEach(function (v) { if (v === "overlaps") n += 1; });
      if (n) notes.push({ key: "note.time_overlaps", n: n });
      if (undated) notes.push({ key: "note.time_undated", n: undated });
      if (undatedDirect) notes.push({ key: "note.time_undated_direct", n: undatedDirect });
      return notes;
    }
    function leftOut(n) { return n ? [{ key: "note.left_out", n: n }] : []; }
    function participation(list, leader) {
      var rows = new Map(), absent = [], left = 0;
      list.forEach(function (t) {
        touch[t].forEach(function (j) {
          var c = C[j];
          if (c.o !== t || (c.k !== "a" && c.k !== "p") || AGENT_KINDS.indexOf(kind(c.s)) < 0) return;
          if (!usable(c)) { left += 1; return; }
          if (!positive(c)) { absent.push(j); return; }
          if (leader && !isLeader(c)) return;
          add(rows, c.s, [j]);
        });
      });
      return { rows: rows, absent: uniqSorted(absent), left: left };
    }

    var OPS = {
      participants: function (node) {
        var tg = targets(node.args[0]);
        var p = participation(tg.list, word(node, "as") === "leader");
        var notes = tg.notes.concat(leftOut(p.left));
        if (tg.list.some(function (t) { return kind(t) === "story"; })) notes.push({ key: "note.story_list" });
        var extra = { absent: p.absent };
        if (tg.searched !== null) extra.searched = tg.searched;
        return makeSet("agents", p.rows, notes, null, extra);
      },
      absent: function (node) {
        var tg = targets(node.args[0]);
        var p = participation(tg.list, false), rows = new Map();
        p.absent.forEach(function (j) { add(rows, C[j].s, [j]); });
        var extra = tg.searched !== null ? { searched: tg.searched } : null;
        return makeSet("agents", rows, tg.notes.concat(leftOut(p.left)), null, extra);
      },
      events: function (node) {
        var kw = node.kw, at = has(kw, "at") ? kw.at.e : null, inv = has(kw, "involving") ? kw.involving.e : null;
        var w = windowOf(node), rows = new Map(), tags = new Map(), undated = 0;
        E.forEach(function (ent, i) {
          if (ent.k !== "event") return;
          var ev = [], hits;
          if (at !== null) {
            hits = touch[i].filter(function (j) { var c = C[j]; return c.s === i && c.o === at && PLACE_LINKS.indexOf(c.p) >= 0 && usable(c); });
            if (!hits.length) return;
            ev = ev.concat(hits);
          }
          if (inv !== null) {
            hits = touch[i].filter(function (j) { var c = C[j]; return c.s === inv && c.o === i && positive(c) && usable(c); });
            if (!hits.length) return;
            ev = ev.concat(hits);
          }
          if (w !== null) {
            var tag = timeTag(ent, w);
            if (tag === null) return;
            if (tag === "undated") { undated += 1; return; }
            tags.set(i, tag);
          }
          rows.set(i, ev);
        });
        return makeSet("events", rows, timeNotes(w, tags, undated, 0), tags);
      },
      people: function (node) {
        var place = node.kw.at.e;
        var kwCopy = {};
        Object.keys(node.kw).forEach(function (k) { kwCopy[k] = node.kw[k]; });
        var evs = OPS.events({ op: "events", kw: kwCopy });
        var p = participation(evs.rows.map(function (r) { return r.e; }), false);
        var rows = p.rows, left = p.left, w = windowOf(node), undatedDirect = 0;
        touch[place].forEach(function (j) {
          var c = C[j];
          if (c.o !== place || c.k !== "a" || c.c !== "spatial" || AGENT_KINDS.indexOf(kind(c.s)) < 0) return;
          if (!usable(c)) { left += 1; return; }
          if (w !== null) { undatedDirect += 1; return; }
          add(rows, c.s, [j]);
        });
        var tags = new Map();
        evs.rows.forEach(function (r) { if (r.tag) tags.set(r.e, r.tag); });
        var tn = timeNotes(w, tags, 0, undatedDirect);
        var notes = [{ key: "note.people_at" }].concat(evs.notes).concat(tn.filter(function (n) { return n.key === "note.time_undated_direct"; })).concat(leftOut(left));
        return makeSet("agents", rows, notes, null, { absent: p.absent, searched: evs.rows });
      },
      stories: function (node) {
        var x = node.kw.involving.e, rows = new Map();
        touch[x].forEach(function (j) {
          var c = C[j];
          if (c.s === x && c.k === "a" && kind(c.o) === "story" && usable(c)) add(rows, c.o, [j]);
        });
        return makeSet("stories", rows, rows.size ? [{ key: "note.story_list" }] : []);
      },
      relatives: function (node) {
        var p = node.args[0].e, tie = word(node, "tie"), rows = new Map();
        touch[p].forEach(function (j) {
          var c = C[j];
          if (c.k !== "a" || c.c !== "kinship" || !usable(c)) return;
          var other = c.s === p ? c.o : c.s;
          if (other === p) return;
          var pred = c.p, subj = c.s === p;
          var ok = (tie === "any"
            || (tie === "parent" && ((!subj && (pred === "father_of" || pred === "mother_of")) || (subj && pred === "child_of")))
            || (tie === "father" && !subj && pred === "father_of")
            || (tie === "mother" && !subj && pred === "mother_of")
            || (tie === "child" && ((subj && (pred === "father_of" || pred === "mother_of")) || (!subj && pred === "child_of")))
            || (tie === "spouse" && pred === "spouse_of")
            || (tie === "sibling" && pred === "sibling_of"));
          if (ok) add(rows, other, [j]);
        });
        return makeSet("agents", rows, []);
      },
      connected: function (node) {
        var x = node.args[0].e, via = word(node, "via"), rows = new Map(), notes = [];
        if (via === "any" || via === "ties") {
          touch[x].forEach(function (j) {
            var c = C[j];
            if (c.k !== "a" || !usable(c)) return;
            var other = c.s === x ? c.o : c.s;
            if (other !== x && AGENT_KINDS.indexOf(kind(other)) >= 0) add(rows, other, [j]);
          });
        }
        if (via === "any" || via === "events") {
          touch[x].forEach(function (j) {
            var c = C[j];
            if (c.s !== x || !positive(c) || kind(c.o) !== "event" || !usable(c)) return;
            var ev = c.o;
            touch[ev].forEach(function (j2) {
              var c2 = C[j2];
              if (c2.o !== ev || c2.s === x || (c2.k !== "a" && c2.k !== "p") || !positive(c2)
                || AGENT_KINDS.indexOf(kind(c2.s)) < 0 || !usable(c2)) return;
              add(rows, c2.s, [j, j2]);
            });
          });
          notes.push({ key: "note.same_event" });
        }
        return makeSet("agents", rows, rows.size ? notes : []);
      },
      between: function (node) {
        var x = node.args[0].e, y = node.args[1].e, list = [y], links = new Map(), rows = new Map();
        if (kind(y) === "place") {
          touch[y].forEach(function (j) {
            var c = C[j];
            if (c.o === y && PLACE_LINKS.indexOf(c.p) >= 0 && kind(c.s) === "event" && usable(c)) {
              if (!links.has(c.s)) list.push(c.s);
              add(links, c.s, [j]);
            }
          });
        }
        list.forEach(function (t) {
          touch[t].forEach(function (j) {
            var c = C[j];
            if (usable(c) && ((c.s === x && c.o === t) || (c.s === t && c.o === x))) add(rows, t, [j]);
          });
          if (rows.has(t) && links.has(t)) add(rows, t, links.get(t));
        });
        return { type: "links", rows: makeRows(rows, null), notes: [], a: x, b: y };
      },
      path: function (node) {
        var x = node.args[0].e, y = node.args[1].e;
        var mx = has(node.kw, "max") ? node.kw.max.n : DEFAULTS["path|max"];
        var prev = new Map([[x, null]]), depth = new Map([[x, 0]]), queue = [x], k = 0, found = false;
        while (k < queue.length && !found) {
          var n = queue[k];
          k += 1;
          if (depth.get(n) >= mx) continue;
          var tl = touch[n];
          for (var q = 0; q < tl.length; q++) {
            var j = tl[q], c = C[j];
            if (!usable(c)) continue;
            var m = c.s === n ? c.o : c.s;
            if (prev.has(m)) continue;
            prev.set(m, [n, j]);
            depth.set(m, depth.get(n) + 1);
            if (m === y) { found = true; break; }
            queue.push(m);
          }
        }
        var steps = [];
        if (found) {
          var cur = y;
          while (prev.get(cur) !== null) {
            var pv = prev.get(cur);
            steps.push({ a: pv[0], c: pv[1], b: cur });
            cur = pv[0];
          }
          steps.reverse();
        }
        return { type: "path", steps: steps, a: x, b: y, max: mx, notes: steps.length ? [{ key: "note.path" }] : [] };
      },
      when: function (node) {
        var x = node.args[0].e, ent = E[x], field = ent.k === "person" ? "death" : "dates";
        return { type: "dates", e: x, field: field, dates: ent[field] || [], notes: [{ key: "note.fields" }] };
      },
      where: function (node) {
        var x = node.args[0].e, rows = new Map();
        touch[x].forEach(function (j) {
          var c = C[j];
          if (c.s === x && PLACE_LINKS.indexOf(c.p) >= 0 && kind(c.o) === "place" && usable(c)) add(rows, c.o, [j]);
        });
        return makeSet("places", rows, []);
      },
      about: function (node) {
        var x = node.args[0].e;
        var counts = { stories: 0, events: 0, places: 0, groups: 0, kinship: 0, people: 0 }, status = {};
        touch[x].forEach(function (j) {
          var c = C[j], other = c.s === x ? c.o : c.s, k = kind(other), key;
          if (k === "story") key = "stories";
          else if (k === "event") key = "events";
          else if (k === "place") key = "places";
          else if (k === "group") key = "groups";
          else if (c.c === "kinship") key = "kinship";
          else key = "people";
          counts[key] += 1;
          var s = st(c) || "none";
          status[s] = (status[s] || 0) + 1;
        });
        var sorted = {};
        Object.keys(status).sort().forEach(function (k) { sorted[k] = status[k]; });
        return { type: "about", e: x, counts: counts, n: touch[x].length, status: sorted, notes: [] };
      },
      count: function (node) {
        var sub = execute(node.args[0]);
        return { type: "count", n: sub.rows.length, set: sub, notes: [{ key: "note.count" }] };
      },
      reviewed: function (node) {
        var sub = execute(node.args[0]), rows = new Map(), tags = new Map();
        sub.rows.forEach(function (r) {
          var keep = r.c.filter(function (j) { return st(C[j]) === "accepted"; });
          if (keep.length) { rows.set(r.e, keep); if (r.tag) tags.set(r.e, r.tag); }
        });
        return makeSet(sub.of, rows, sub.notes.slice().concat([{ key: "note.reviewed" }]), tags);
      }
    };
    function setop(node, mode) {
      var a = execute(node.args[0]), b = execute(node.args[1]);
      var ra = new Map(), rb = new Map(), keep = [];
      a.rows.forEach(function (r) { ra.set(r.e, r); });
      b.rows.forEach(function (r) { rb.set(r.e, r); });
      if (mode === "both") ra.forEach(function (r, e) { if (rb.has(e)) keep.push(e); });
      else if (mode === "either") {
        ra.forEach(function (r, e) { keep.push(e); });
        rb.forEach(function (r, e) { if (!ra.has(e)) keep.push(e); });
      } else ra.forEach(function (r, e) { if (!rb.has(e)) keep.push(e); });
      var rows = new Map(), tags = new Map();
      keep.forEach(function (e) {
        var claims = (ra.has(e) ? ra.get(e).c.slice() : []).concat(rb.has(e) && mode !== "except" ? rb.get(e).c.slice() : []);
        rows.set(e, claims);
        var tag = (ra.get(e) || rb.get(e)).tag;
        if (tag) tags.set(e, tag);
      });
      var notes = [];
      a.notes.concat(b.notes).forEach(function (n) {
        if (!notes.some(function (m) { return jsonEq(m, n); })) notes.push(n);
      });
      if (mode === "except") notes.push({ key: "note.except" });
      return makeSet(a.of, rows, notes, tags);
    }
    OPS.both = function (node) { return setop(node, "both"); };
    OPS.either = function (node) { return setop(node, "either"); };
    OPS.except = function (node) { return setop(node, "except"); };
    function execute(node) { return OPS[node.op](node); }

    // ------------------------------------------------------------------ plain language
    function plain(node) {
      var t = node.t;
      if (t === "ref") return E[node.e].n;
      if (t === "year") return node.n + " " + node.era.toUpperCase();
      if (t === "num") return String(node.n);
      if (t === "word") return node.w;
      var op = node.op, a = node.args, kw = node.kw;
      if (op === "participants") return fmt(T[word(node, "as") === "leader" ? "plain.participants_leader" : "plain.participants"], { target: plain(a[0]) });
      if (op === "people") {
        if (has(kw, "from") || has(kw, "to")) return fmt(T["plain.people_range"], { place: plain(kw.at), range: range(kw) });
        return fmt(T["plain.people"], { place: plain(kw.at) });
      }
      if (op === "absent") return fmt(T["plain.absent"], { target: plain(a[0]) });
      if (op === "events") {
        var parts = [];
        if (has(kw, "at")) parts.push(fmt(T["plain.f_at"], { place: plain(kw.at) }));
        if (has(kw, "involving")) parts.push(fmt(T["plain.f_involving"], { agent: plain(kw.involving) }));
        if (has(kw, "from") || has(kw, "to")) parts.push(range(kw));
        return fmt(T["plain.events"], { filters: parts.join(T["plain.and"]) });
      }
      if (op === "stories") return fmt(T["plain.stories"], { agent: plain(kw.involving) });
      if (op === "relatives") return fmt(T["plain.relatives_" + word(node, "tie")], { person: plain(a[0]) });
      if (op === "connected") return fmt(T["plain.connected_" + word(node, "via")], { agent: plain(a[0]) });
      if (op === "between") return fmt(T[kind(a[1].e) === "place" ? "plain.between_place" : "plain.between"], { a: plain(a[0]), b: plain(a[1]) });
      if (op === "path") return fmt(T["plain.path"], { a: plain(a[0]), b: plain(a[1]), max: has(kw, "max") ? kw.max.n : DEFAULTS["path|max"] });
      if (op === "when") return fmt(T[kind(a[0].e) === "person" ? "plain.when_death" : "plain.when"], { x: plain(a[0]) });
      if (op === "where") return fmt(T["plain.where"], { x: plain(a[0]) });
      if (op === "about") return fmt(T["plain.about"], { x: plain(a[0]) });
      if (op === "both" || op === "either" || op === "except") return fmt(T["plain." + op], { a: plain(a[0]), b: plain(a[1]) });
      if (op === "count") return fmt(T["plain.count"], { set: plain(a[0]) });
      if (op === "reviewed") return fmt(T["plain.reviewed"], { set: plain(a[0]) });
      throw dslErr("error.unknown_op", { op: op });
    }
    function range(kw) {
      var f = has(kw, "from") ? kw.from : null, t = has(kw, "to") ? kw.to : null;
      if (f && t && f.n === t.n && f.era === t.era) return fmt(T["plain.range_in"], { start: plain(f) });
      if (f && t) return fmt(T["plain.range_between"], { start: plain(f), end: plain(t) });
      if (f) return fmt(T["plain.range_from"], { start: plain(f) });
      return fmt(T["plain.range_to"], { end: plain(t) });
    }

    // ------------------------------------------------------------------ translate.py
    var RX_CACHE = {};
    function rx(p) { if (!has(RX_CACHE, p)) RX_CACHE[p] = new RegExp(p); return RX_CACHE[p]; }
    function stripTrailing(q) { return q.replace(rx(RULES.cleanup.trailing), ""); }
    function stripFillers(q) { return stripSpaces(q.replace(rx(RULES.cleanup.fillers), "")); }
    function classifyRefusal(q) {
      var padded = " " + q + " ";
      for (var i = 0; i < RULES.refusals.length; i++) {
        var cls = RULES.refusals[i];
        if (cls.unless && rx(cls.unless).test(padded)) continue;
        for (var k = 0; k < cls.patterns.length; k++) if (rx(cls.patterns[k]).test(padded)) return cls["class"];
      }
      return null;
    }

    function scored(mention) {
      var m = nameTokens(mention), out = [];
      if (!m.length) return out;
      E.forEach(function (e, i) {
        var best = 0;
        e.keys.forEach(function (k) { var s = score(m, k); if (s > best) best = s; });
        if (best >= LK.min_score) out.push([best, i]);
      });
      out.sort(function (x, y) { return (y[0] - x[0]) || (x[1] - y[1]); });
      return out;
    }
    function link(mention, kinds, minScore) {
      var allc = scored(mention);
      var inkind = allc.filter(function (x) { return kinds.indexOf(E[x[1]].k) >= 0; });
      if (!inkind.length || inkind[0][0] < minScore) {
        var others = allc.filter(function (x) { return x[0] >= 2; }).map(function (x) { return x[1]; }).slice(0, LK.max_alternatives);
        return { status: minScore > 1 ? "below" : "none", others: others };
      }
      var best = inkind[0][0];
      var top = inkind.filter(function (x) { return x[0] === best; }).map(function (x) { return x[1]; });
      for (var q = 0; q < kinds.length; q++) {
        var tk = top.filter(function (i) { return E[i].k === kinds[q]; });
        if (tk.length) { top = tk; break; }
      }
      if (top.length > 1) {
        var kd = E[top[0]].k;
        var cands = inkind.filter(function (x) { return E[x[1]].k === kd && x[0] >= best - LK.ambiguity_margin; }).map(function (x) { return x[1]; });
        return { status: "ambiguous", cands: cands.slice(0, LK.max_candidates), n: cands.length };
      }
      var chosen = top[0];
      var alts = inkind.filter(function (x) {
        if (x[1] === chosen) return false;
        if (E[x[1]].k !== E[chosen].k) return x[0] >= LK.alternatives_min_score;
        return x[0] >= LK.alternatives_same_kind_min_score;
      }).map(function (x) { return x[1]; });
      return { status: "ok", e: chosen, score: best, alts: alts.slice(0, LK.max_alternatives) };
    }

    function Unsupported(reason) { this.reason = reason; }
    function era(e) {
      if (!e) return null;
      if (e === "ad") return "ce";
      if (e === "bce") return "bh";
      return e;
    }
    function timeWindow(q) {
      var m = rx(TIME.range).exec(q), rest, y1, e1, y2, e2, tail;
      if (m) { rest = m[1]; y1 = parseInt(m[2], 10); e1 = m[3]; y2 = parseInt(m[4], 10); e2 = m[5]; tail = m[6]; }
      else {
        m = rx(TIME.single).exec(q);
        if (m) { rest = m[1]; y1 = parseInt(m[2], 10); e1 = m[3]; y2 = y1; e2 = e1; tail = m[4]; }
        else {
          m = rx(TIME.single_bare).exec(q);
          if (!m) return { q: q, w: null, notes: [] };
          rest = m[1]; y1 = parseInt(m[2], 10); e1 = null; y2 = y1; e2 = null; tail = m[3];
        }
      }
      if (tail) rest = rest + " " + tail;
      e1 = era(e1); e2 = era(e2);
      if (e1 === "bh" || e2 === "bh") throw new Unsupported("time_bh");
      var notes = [], a = e1 || e2, b = e2 || e1;
      if (!a) {
        if (y1 <= TIME.bare_ah_max && y2 <= TIME.bare_ah_max) { a = b = "ah"; notes.push({ key: "note.time_assumed_ah" }); }
        else if (y1 >= TIME.min_ce && y2 >= TIME.min_ce) { a = b = "ce"; }
        else throw new Unsupported("time_era");
      }
      return { q: stripSpaces(rest), w: { from: [y1, a], to: [y2, b] }, notes: notes };
    }
    function timeText(w) {
      if (!w) return "";
      return ", from: " + w.from[0] + " " + w.from[1].toUpperCase() + ", to: " + w.to[0] + " " + w.to[1].toUpperCase();
    }
    function expand(stype, e) {
      var ref = refText(e);
      if (stype === "presence") return E[e].k === "place" ? "people(at: " + ref + "{time})" : "participants(" + ref + ")";
      if (stype === "happening_set" && E[e].k === "place") return "events(at: " + ref + "{time})";
      return ref;
    }
    function build(shape, chosen, w, reviewed) {
      var t = shape.dsl;
      Object.keys(chosen).forEach(function (num) { t = replaceAll(t, "{" + num + "}", expand(chosen[num][0], chosen[num][1])); });
      var usedTime = t.indexOf("{time}") >= 0;
      if (w && !usedTime) throw new Unsupported("time_needs_place");
      t = replaceAll(replaceAll(t, "{time}", timeText(w)), "(, ", "(");
      if (reviewed) {
        t = t.indexOf("count(") === 0 ? "count(reviewed(" + t.slice(6) + ")" : "reviewed(" + t + ")";
        try { validate(parse(t)); } catch (err) {
          if (err instanceof DslError) throw new Unsupported("reviewed_needs_list");
          throw err;
        }
      }
      return t;
    }
    function withChoice(chosen, num, stype, e) {
      var out = {};
      Object.keys(chosen).forEach(function (k) { out[k] = chosen[k]; });
      out[num] = [stype, e];
      return out;
    }
    function fill(shape, m, w, reviewed) {
      var slots = [], i;
      if (shape.pair) {
        var whole = m[1], found = null, from = 0, at;
        var kinds = RULES.slots.presence.kinds;
        while ((at = whole.indexOf(" and ", from)) >= 0) {
          var left = stripSpaces(whole.slice(0, at));
          var right = stripSpaces(whole.slice(at + 5)).replace(/^(?:at|in) /, "");
          var la = link(left, kinds, LK.pair_min_score), lb = link(right, kinds, LK.pair_min_score);
          if (la.status === "ok" && lb.status === "ok" && la.e !== lb.e) { found = [la, lb, left, right]; break; }
          from = at + 5;
        }
        if (!found) return null;
        slots = [["1", "presence", found[0], found[2]], ["2", "presence", found[1], found[3]]];
      } else {
        var nums = Object.keys(shape.slots).sort();
        for (i = 0; i < nums.length; i++) {
          var num = nums[i], stype = shape.slots[num];
          var mention = stripSpaces(m[parseInt(num, 10)] || "");
          var res = link(mention, RULES.slots[stype].kinds, shape.min_score || 1);
          if (res.status === "below") return null;
          slots.push([num, stype, res, mention]);
        }
      }
      var notes = shape.note ? [{ key: "note." + shape.note }] : [];
      for (i = 0; i < slots.length; i++) {
        if (slots[i][2].status === "none") {
          return { outcome: "not_found", mention: slots[i][3], kinds: RULES.slots[slots[i][1]].kinds, others: slots[i][2].others };
        }
      }
      var chosen = {}, nChosen = 0;
      slots.forEach(function (s) { if (s[2].status === "ok") { chosen[s[0]] = [s[1], s[2].e]; nChosen += 1; } });
      for (i = 0; i < slots.length; i++) {
        var sl = slots[i];
        if (sl[2].status === "ambiguous") {
          var options = sl[2].cands.map(function (c) {
            var dsl = null;
            if (nChosen === slots.length - 1) {
              try { dsl = build(shape, withChoice(chosen, sl[0], sl[1], c), w, reviewed); } catch (err) {
                if (!(err instanceof Unsupported)) throw err;
                dsl = null;
              }
            }
            return { e: c, dsl: dsl };
          });
          return { outcome: "ambiguous", mention: sl[3], options: options, n: sl[2].n };
        }
      }
      var dslText = build(shape, chosen, w, reviewed), alts = [];
      slots.forEach(function (s) {
        var opts = [];
        (s[2].alts || []).forEach(function (a) {
          try { opts.push({ e: a, dsl: build(shape, withChoice(chosen, s[0], s[1], a), w, reviewed) }); } catch (err) {
            if (!(err instanceof Unsupported)) throw err;
          }
        });
        if (opts.length) alts.push({ mention: s[3], options: opts });
      });
      return { outcome: "query", dsl: dslText, notes: notes, alts: alts };
    }
    function translate(q) {
      try {
        var reviewed = false, i, k;
        for (i = 0; i < RULES.status_suffix.length; i++) {
          var sm = rx(RULES.status_suffix[i]).exec(q);
          if (sm) { q = stripSpaces(sm[1]); reviewed = true; break; }
        }
        var tw = timeWindow(q);
        q = tw.q;
        for (i = 0; i < RULES.shapes.length; i++) {
          var shape = RULES.shapes[i];
          if (shape.needs_time && tw.w === null) continue;
          for (k = 0; k < shape.patterns.length; k++) {
            var m = rx(shape.patterns[k]).exec(q);
            if (!m) continue;
            var res = fill(shape, m, tw.w, reviewed);
            if (res === null) continue;
            if (res.outcome === "query") res.notes = tw.notes.concat(res.notes);
            return res;
          }
        }
        return { outcome: "unsupported", reason: "generic" };
      } catch (err) {
        if (err instanceof Unsupported) return { outcome: "unsupported", reason: err.reason };
        throw err;
      }
    }
    function refsOf(node) {
      var out = [];
      (function walk(n) {
        if (n.t === "ref" && has(n, "e")) { if (out.indexOf(n.e) < 0) out.push(n.e); }
        else if (n.t === "op") {
          n.args.forEach(walk);
          Object.keys(n.kw).forEach(function (k) { walk(n.kw[k]); });
        }
      })(node);
      return out;
    }
    function runQuery(textIn, out, notes, alts) {
      var typed;
      try { typed = validate(parse(textIn)); } catch (err) {
        if (!(err instanceof DslError)) throw err;
        out.outcome = "invalid"; out.dsl = textIn; out.error = { key: err.key, params: err.params };
        return out;
      }
      out.outcome = "answer";
      out.dsl = text(typed);
      out.plain = plain(typed);
      out.result = execute(typed);
      out.refs = refsOf(typed);
      out.notes = (notes || []).slice();
      out.alts = (alts || []).slice();
      return out;
    }
    function answer(question) {
      var raw = String(question || "").replace(rx("^(?:" + NR.spaces + ")|(?:" + NR.spaces + ")$"), "");
      var out = { q: raw, version: data.version };
      if (!raw) { out.outcome = "empty"; return out; }
      if (Array.from(raw).length > LIMITS.question_max) { out.outcome = "too_long"; return out; }
      if (rx(RULES.dsl_direct).test(raw.toLowerCase())) { out.direct = 1; return runQuery(raw, out); }
      var q = stripTrailing(textKey(raw));
      var cls = classifyRefusal(q);
      if (cls) { out.outcome = "refusal"; out.refusal = cls; return out; }
      q = stripFillers(q);
      var res = translate(q);
      if (res.outcome !== "query") { Object.keys(res).forEach(function (k) { out[k] = res[k]; }); return out; }
      return runQuery(res.dsl, out, res.notes, res.alts);
    }

    // ------------------------------------------------------------------ present.py
    var AR_RUN = new RegExp(data.norm.arabic_run, "g"), PBUH = data.norm.pbuh;
    function markArabic(escaped) {
      var out = escaped.replace(AR_RUN, function (m) { return '<span lang="ar" dir="rtl">' + m + "</span>"; });
      return replaceAll(out, PBUH, '<span class="pbuh" lang="ar" dir="rtl">' + PBUH + "</span>");
    }
    function Presenter(base, examples) {
      var P = this;
      function h(s) { return markArabic(esc(s)); }
      function t(key, kw) { return fmt(T[key], kw || {}); }
      function hk(key, kw) { return fmt(h(T[key]), kw || {}); }
      function plural(key, n) { return key + (n === 1 ? ".one" : ".other"); }
      function noteText(note) {
        var n = has(note, "n") ? note.n : null;
        var key = note.key + (n !== null && n !== 1 ? ".other" : ".one");
        return n !== null ? t(key, { n: n }) : t(key);
      }
      function href(i) { return base + E[i].r + "/"; }
      function linkTo(i) { return '<a href="' + esc(href(i)) + '">' + h(E[i].n) + "</a>"; }
      function kindTag(i) { return '<span class="kind">(' + h(T["kind." + E[i].k]) + ")</span>"; }
      function status(s) {
        var word = has(T, "status." + (s || "none")) ? T["status." + (s || "none")] : (s || "");
        var cls = "status-" + esc(s || "none");
        return '<span class="status ' + cls + '">' + h(t("status.label", { value: word })) + "</span>";
      }
      function source(c) {
        var label = h(T["claim.source"]);
        if (c.cit) {
          var cit = h(c.cit);
          if (has(c, "sty")) cit = '<a href="' + esc(href(c.sty)) + '">' + cit + "</a>";
          return '<span class="source">' + label + " " + cit + "</span>";
        }
        if (c.src) return '<span class="source">' + label + " " + h(c.src) + "</span>";
        if (has(c, "by")) return '<span class="source">' + h(t("claim.recorded_by", { value: AGENTS_TABLE[c.by] })) + "</span>";
        return '<span class="source not-recorded">' + label + " " + h(T["claim.not_recorded"]) + "</span>";
      }
      function claim(j, cls) {
        var c = C[j], pred = c.k === "a" ? (c.pl || c.p) : T["claim." + c.p];
        var out = '<li class="' + (cls || "claim") + '"><p class="claim-text">' + linkTo(c.s) + ' <span class="rel">' + h(pred) + "</span> " + linkTo(c.o) + "</p>";
        if (c.role) out += '<p class="claim-role">' + h(c.k === "p" ? t("claim.role", { value: c.role }) : c.role) + "</p>";
        if (c.q && c.q.length) out += '<p class="claim-marker">' + h(t("claim.marker", { value: c.q.join("; ") })) + "</p>";
        var sep = ' <span class="sep" aria-hidden="true">&middot;</span> ';
        var meta = status(st(c)) + sep + source(c);
        if (c.ai) meta += sep + '<span class="ai-note">' + h(T["claim.ai"]) + "</span>";
        return out + '<p class="claim-meta">' + meta + "</p></li>";
      }
      function claims(js) {
        if (!js.length) return "";
        return '<ul class="claim-list">' + js.map(function (j) { return claim(j); }).join("") + "</ul>";
      }
      function claimsFolded(js) {
        if (js.length <= LIMITS.claims_shown) return claims(js);
        var rest = js.slice(LIMITS.claims_shown);
        return claims(js.slice(0, LIMITS.claims_shown)) + '<details class="more-claims"><summary>'
          + h(t(plural("answer.more_claims", rest.length), { n: rest.length })) + "</summary>" + claims(rest) + "</details>";
      }
      function row(r) {
        var i = r.e, head = linkTo(i) + " " + kindTag(i), dates = E[i].dates || [];
        if (dates.length && dates[0].t) head += ' <span class="row-date">' + h(dates[0].t) + "</span>";
        if (r.tag === "overlaps") head += ' <span class="tag">' + h(T["answer.overlaps"]) + "</span>";
        return '<li class="row"><p class="row-head">' + head + "</p>" + claimsFolded(r.c) + "</li>";
      }
      function rows(list) {
        var shown = list.slice(0, LIMITS.rows_shown);
        var out = '<ol class="rows">' + shown.map(row).join("") + "</ol>";
        if (list.length > shown.length) out += '<p class="note">' + h(t("answer.more", { shown: shown.length, n: list.length })) + "</p>";
        return out;
      }
      function statusSummary(js) {
        var ids = uniqSorted(js);
        if (!ids.length) return "";
        var acc = ids.filter(function (j) { return st(C[j]) === "accepted"; }).length, txt;
        if (acc === 0) txt = T["answer.status_none"];
        else if (acc === ids.length) txt = t("answer.status_all", { n: ids.length });
        else txt = t("answer.status_some", { a: acc, n: ids.length });
        return '<p class="status-summary">' + h(txt) + "</p>";
      }
      function whyEmpty(refs) {
        var cnt = data.counts;
        var out = "<p>" + h(t("answer.empty_why", { person: cnt.person, event: cnt.event, place: cnt.place, story: cnt.story })) + "</p>";
        var gaps = [];
        refs.forEach(function (i) { (E[i].gaps || []).forEach(function (g) { if (gaps.indexOf(g) < 0) gaps.push(g); }); });
        if (gaps.length) out += "<p>" + h(T["answer.gaps"]) + '</p><ul class="gaps">' + gaps.map(function (g) { return "<li>" + h(g) + "</li>"; }).join("") + "</ul>";
        return out;
      }
      function notesHtml(list) {
        if (!list.length) return "";
        return '<div class="notes"><h3>' + h(T["answer.notes"]) + "</h3><ul>" + list.map(function (n) { return "<li>" + h(noteText(n)) + "</li>"; }).join("") + "</ul></div>";
      }
      function asked(q) { return '<p class="asked"><span class="k">' + h(T["answer.question"]) + "</span> " + h(q) + "</p>"; }
      function open(outcome, key) {
        return '<section class="answer outcome-' + outcome + '" aria-labelledby="answer-h"><h2 id="answer-h" tabindex="-1">' + h(T[key]) + "</h2>";
      }
      function choice(i, dsl) {
        var attr = dsl ? ' data-dsl="' + esc(dsl) + '"' : "";
        return '<li><a href="' + esc(href(i)) + '"' + attr + ">" + h(E[i].n) + "</a> " + kindTag(i) + "</li>";
      }
      function setBody(res, refs) {
        var list = res.rows, used = [], out = "";
        list.forEach(function (r) { used = used.concat(r.c); });
        used = used.concat(res.absent || []);
        (res.searched || []).forEach(function (r) { used = used.concat(r.c); });
        if (list.length) {
          out += '<p class="lead">' + h(t(plural("answer.lead." + res.of, list.length), { n: list.length })) + "</p>";
          out += statusSummary(used);
        } else out += '<p class="lead empty">' + h(T["answer.empty"]) + "</p>" + whyEmpty(refs);
        if (res.searched && res.searched.length) {
          out += '<details class="searched-events"><summary>' + h(T["answer.searched_events"]) + ' <span class="count">(' + res.searched.length + ")</span></summary>" + rows(res.searched) + "</details>";
        }
        if (list.length) out += rows(list);
        if (res.absent && res.absent.length) out += '<h3 class="absent-h">' + h(T["answer.absent"]) + "</h3>" + claims(res.absent);
        return out;
      }
      function body(ans) {
        var res = ans.result, refs = ans.refs || [], ty = res.type, n, js, items;
        if (ty === "set") return setBody(res, refs);
        if (ty === "count") return setBody(res.set, refs);
        if (ty === "path") {
          if (!res.steps.length) return '<p class="lead empty">' + h(t("answer.path_none", { max: res.max, a: E[res.a].n, b: E[res.b].n })) + "</p>" + whyEmpty(refs);
          n = res.steps.length;
          js = res.steps.map(function (s) { return s.c; });
          return '<p class="lead">' + hk(plural("answer.path_lead", n), { a: linkTo(res.a), b: linkTo(res.b), n: String(n) }) + "</p>" + statusSummary(js)
            + '<ol class="path claim-list">' + js.map(function (j) { return claim(j, "claim step"); }).join("") + "</ol>";
        }
        if (ty === "links") {
          var a = linkTo(res.a), b = linkTo(res.b);
          if (!res.rows.length) return '<p class="lead empty">' + hk("answer.links_none", { a: a, b: b }) + "</p>" + whyEmpty(refs);
          var used = [];
          res.rows.forEach(function (r) { used = used.concat(r.c); });
          n = uniqSorted(used.filter(function (j) { return C[j].s === res.a || C[j].o === res.a; })).length;
          return '<p class="lead">' + hk(plural("answer.links_lead", n), { a: a, b: b, n: String(n) }) + "</p>" + statusSummary(used) + rows(res.rows);
        }
        if (ty === "dates") {
          var x = linkTo(res.e);
          if (!res.dates.length) return '<p class="lead empty">' + hk("answer.dates_none", { x: x }) + "</p>" + whyEmpty(refs);
          items = res.dates.map(function (d) {
            return "<li><p>" + h(d.t || "") + "</p>" + (d.notes || []).map(function (nt) { return '<p class="note">' + h(nt) + "</p>"; }).join("") + "</li>";
          }).join("");
          var by = E[res.e].by;
          var meta = '<span class="status status-none">' + h(T["answer.field_status"]) + "</span>";
          if (by !== undefined && by !== null) meta += ' <span class="sep" aria-hidden="true">&middot;</span> <span class="source">' + h(t("answer.recorded_by", { by: AGENTS_TABLE[by] })) + "</span>";
          return '<p class="lead">' + hk("answer.dates_lead", { x: x }) + '</p><ul class="dates">' + items + '</ul><p class="claim-meta">' + meta + "</p>";
        }
        if (ty === "about") {
          var i = res.e, xx = linkTo(i), out;
          if (!res.n) out = '<p class="lead">' + hk("answer.about_none", { x: xx }) + "</p>";
          else out = '<p class="lead">' + hk(plural("answer.about_lead", res.n), { x: xx, n: String(res.n) }) + "</p>";
          items = Object.keys(res.counts).filter(function (k) { return res.counts[k]; }).map(function (k) {
            return "<li>" + h(t(plural("about." + k, res.counts[k]), { n: res.counts[k] })) + "</li>";
          }).join("");
          if (items) out += '<ul class="plain counts">' + items + "</ul>";
          var stt = res.status, total = 0;
          Object.keys(stt).forEach(function (k) { total += stt[k]; });
          if (total) {
            var acc = stt.accepted || 0, txt;
            if (acc === 0) txt = T["answer.status_none"];
            else if (acc === total) txt = t("answer.status_all", { n: total });
            else txt = t("answer.status_some", { a: acc, n: total });
            out += '<p class="status-summary">' + h(txt) + "</p>";
          }
          if (E[i].cov) out += '<p class="coverage">' + h(t("answer.coverage", { value: E[i].cov })) + "</p>";
          out += '<p><a href="' + esc(href(i)) + '">' + h(T["answer.open_page"]) + "</a></p>";
          return out;
        }
        return "";
      }
      function altsHtml(list) {
        return list.map(function (a) {
          return '<div class="alts"><p>' + h(t("answer.alts", { mention: a.mention })) + '</p><ul class="plain">'
            + a.options.map(function (o) { return choice(o.e, o.dsl); }).join("") + "</ul></div>";
        }).join("");
      }
      P.render = function (ans) {
        var oc = ans.outcome, q = has(ans, "q") ? ans.q : "";
        if (oc === "answer") {
          var res = ans.result;
          var allNotes = (ans.notes || []).concat(res.notes || []).concat((res.set || {}).notes || []);
          return open("answer", "answer.heading") + asked(q)
            + '<p class="searched">' + h(t("answer.searched", { plain: ans.plain })) + "</p>"
            + '<details class="query"><summary>' + h(T["answer.query"]) + '</summary><p><code class="dsl">' + esc(ans.dsl) + '</code></p><p class="note">' + h(T["answer.query_note"]) + "</p></details>"
            + altsHtml(ans.alts || []) + body(ans) + notesHtml(allNotes)
            + '<p class="composed">' + h(T["answer.composed"]) + " " + h(t("answer.version", { v: ans.version })) + "</p></section>";
        }
        if (oc === "refusal") {
          return open("refusal", "refusal.heading") + asked(q) + '<p class="refusal-reason">' + h(T["refusal." + ans.refusal + ".reason"]) + "</p>"
            + "<p>" + h(T["refusal." + ans.refusal + ".offer"]) + "</p></section>";
        }
        if (oc === "unsupported") {
          var ex = examples.map(function (x) { return '<li><a href="' + esc(base + "ask/q/" + x[1] + "/") + '">' + h(x[0]) + "</a></li>"; }).join("");
          return open("unsupported", "unsupported.heading") + asked(q) + "<p>" + h(T["unsupported." + ans.reason]) + "</p>"
            + (ex ? "<p>" + h(T["unsupported.examples"]) + '</p><ul class="plain examples">' + ex + "</ul>" : "") + "</section>";
        }
        if (oc === "ambiguous") {
          var more = ans.n > ans.options.length ? '<p class="note">' + h(T["ambiguous.more"]) + "</p>" : "";
          return open("ambiguous", "ambiguous.heading") + asked(q) + "<p>" + h(t("ambiguous.lead", { mention: ans.mention, n: ans.n })) + "</p>"
            + '<ul class="plain choices">' + ans.options.map(function (o) { return choice(o.e, o.dsl); }).join("") + "</ul>" + more + "</section>";
        }
        if (oc === "not_found") {
          var kinds = ans.kinds.map(function (k) { return T["kind." + k]; }).join(T["kind.or"]), others = "", gapHtml = "";
          if (ans.others && ans.others.length) others = "<p>" + h(T["notfound.others"]) + '</p><ul class="plain">' + ans.others.map(function (i) { return choice(i, null); }).join("") + "</ul>";
          var gaps = data.gaps || [];
          if (gaps.length) gapHtml = '<details class="gaps"><summary>' + h(T["answer.gaps"]) + "</summary><ul>" + gaps.map(function (g) { return "<li>" + h(g) + "</li>"; }).join("") + "</ul></details>";
          return open("not-found", "notfound.heading") + asked(q) + "<p>" + h(t("notfound.lead", { kinds: kinds, mention: ans.mention })) + "</p>"
            + others + whyEmpty([]) + gapHtml + "</section>";
        }
        if (oc === "invalid") {
          var err = ans.error, params = {};
          Object.keys(err.params).forEach(function (k) { params[k] = err.params[k]; });
          if (err.key === "error.type" && has(params, "want")) params.want = T["want." + params.want];
          return open("invalid", "invalid.heading") + asked(q) + '<p><code class="dsl">' + esc(ans.dsl) + "</code></p>"
            + '<p class="error">' + h(t(err.key, params)) + "</p></section>";
        }
        if (oc === "too_long") return open("empty", "unsupported.heading") + "<p>" + h(t("toolong.lead", { max: LIMITS.question_max })) + "</p></section>";
        return open("empty", "unsupported.heading") + "<p>" + h(T["empty.lead"]) + "</p></section>";
      };
    }

    return {
      textKey: textKey, nameTokens: nameTokens, score: score, fold: fold,
      classifyRefusal: classifyRefusal, answer: answer, yearBounds: yearBounds,
      render: function (ans, base) { return new Presenter(base, data.examples || []).render(ans); }
    };
  }

  // ------------------------------------------------------------------ the page
  function boot(doc, win) {
    var form = doc.getElementById("ask-form");
    if (!form) return;
    var input = doc.getElementById("ask-q"), out = doc.getElementById("ask-answer");
    var status = doc.getElementById("ask-status"), nojs = doc.getElementById("ask-nojs");
    var api = null, loading = null;
    form.hidden = false;
    if (nojs) nojs.hidden = true;
    function load() {
      if (api) return Promise.resolve(api);
      if (!loading) {
        status.textContent = form.getAttribute("data-loading");
        loading = win.fetch(form.getAttribute("data-index")).then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        }).then(function (d) {
          api = create(d);
          status.textContent = "";
          return api;
        }).catch(function (err) {
          status.textContent = form.getAttribute("data-failed");
          loading = null;
          throw err;
        });
      }
      return loading;
    }
    function show(q) {
      return load().then(function (a) {
        out.innerHTML = a.render(a.answer(q), "../");
        var h = out.querySelector("h2");
        if (h) h.focus();
        try { win.history.replaceState(null, "", "#q=" + encodeURIComponent(q)); } catch (e) { /* the address is a convenience */ }
      }).catch(function () { /* the status line already says the graph could not be loaded */ });
    }
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var q = input.value.trim();
      if (q) show(q);
    });
    input.addEventListener("focus", function () { load().catch(function () {}); }, { once: true });
    doc.addEventListener("click", function (ev) {
      var t = ev.target && ev.target.closest ? ev.target.closest("[data-dsl],[data-q]") : null;
      if (!t || !(form.contains(t) || out.contains(t))) return;
      ev.preventDefault();
      var q = t.getAttribute("data-dsl") || t.getAttribute("data-q");
      input.value = q;
      show(q);
    });
    var m = /^#q=(.*)$/.exec(win.location.hash);
    if (m) {
      var q0;
      try { q0 = decodeURIComponent(m[1]); } catch (e) { q0 = ""; }
      if (q0) { input.value = q0; show(q0); }
    }
  }

  if (typeof document !== "undefined" && typeof window !== "undefined") boot(document, window);
  return { create: create, boot: boot };
}));
