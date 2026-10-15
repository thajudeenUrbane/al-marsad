/* Review pages (slice 3b), inlined into every page by review/build_pages.py.
 *
 * Keeps each reviewer's decisions on the device (localStorage, every access in
 * try/catch, with an in-memory fallback and a warning when the browser will not keep
 * them), and makes ONE decision file in the format review/import_decisions.py reads
 * (docs/handover/slice-3a.md): shared through the phone's share sheet where the browser
 * can share files, otherwise downloaded. No request leaves the page, except that over
 * https or localhost it registers sw.js so visited pages open again offline.
 * Every visible string comes from the page (#rv-strings, from review/i18n/en.json).
 */
(function () {
  "use strict";

  var doc = document;
  var body = doc.body;
  var S = {};
  try { S = JSON.parse(doc.getElementById("rv-strings").textContent); } catch (e) { S = {}; }

  function t(key, vars) {
    var s = Object.prototype.hasOwnProperty.call(S, key) ? S[key] : key;
    return s.replace(/\{(\w+)\}/g, function (m, k) { return vars && vars[k] != null ? String(vars[k]) : m; });
  }
  function tn(key, n, vars) {
    vars = vars || {};
    vars.n = n;
    return t(key + (n === 1 ? ".one" : ".other"), vars);
  }
  function $(id) { return doc.getElementById(id); }
  function each(list, fn) { Array.prototype.forEach.call(list, fn); }

  var PREFIX = "marsad-review:1:";
  var K_REVIEWER = PREFIX + "reviewer";
  var ID_RE = /^agt:[0-9A-Za-z]{22}$/;
  var EMAIL_RE = /[\p{L}\p{N}_.+-]+@[\p{L}\p{N}_-]+\.[\p{L}\p{N}_.-]+/u;
  var PHONE_RE = /\+\d[\d\s().-]{6,}\d/;
  var CONTROL_RE = /[\u0000-\u0008\u000B-\u001F\u007F-\u009F]/g;
  var BATCH = body.getAttribute("data-batch") || "";
  var FILE = body.getAttribute("data-file") || "";
  var FP = body.getAttribute("data-fingerprint") || "";

  // ---- storage: localStorage when the browser keeps it, memory otherwise ----------------
  var mem = {};
  var persistent = true;
  function lost() {
    persistent = false;
    var w = $("storage-warning");
    if (w) { w.textContent = t("storage.off"); w.hidden = false; }
  }
  var store = {
    get: function (k) {
      try {
        var v = window.localStorage.getItem(k);
        if (v !== null) return v;
      } catch (e) { lost(); }
      return Object.prototype.hasOwnProperty.call(mem, k) ? mem[k] : null;
    },
    set: function (k, v) {
      mem[k] = v;
      try { window.localStorage.setItem(k, v); } catch (e) { lost(); }
    },
    del: function (k) {
      delete mem[k];
      try { window.localStorage.removeItem(k); } catch (e) { lost(); }
    },
    keys: function (prefix) {
      var found = {};
      Object.keys(mem).forEach(function (k) { if (k.indexOf(prefix) === 0) found[k] = 1; });
      try {
        var ls = window.localStorage;
        for (var i = 0; i < ls.length; i++) {
          var k = ls.key(i);
          if (k && k.indexOf(prefix) === 0) found[k] = 1;
        }
      } catch (e) { lost(); }
      return Object.keys(found);
    }
  };
  try {
    window.localStorage.setItem(PREFIX + "probe", "1");
    window.localStorage.removeItem(PREFIX + "probe");
  } catch (e) { lost(); }

  function parse(text) {
    try { return text ? JSON.parse(text) : null; } catch (e) { return null; }
  }

  // ---- the reviewer -----------------------------------------------------------------------
  function reviewer() {
    var v = store.get(K_REVIEWER);
    return v && ID_RE.test(v) ? v : null;
  }
  function normaliseId(s) {
    s = (s || "").trim();
    var m = s.match(/^https?:\/\/w3id\.org\/marsad\/id\/agent\/([0-9A-Za-z]{22})$/);
    if (m) return "agt:" + m[1];
    if (/^[0-9A-Za-z]{22}$/.test(s)) return "agt:" + s;
    return s;
  }
  function linkedId() {
    var m = (location.hash || "").match(/[#&]reviewer=([^&]+)/);
    if (!m) return null;
    try { return normaliseId(decodeURIComponent(m[1])); } catch (e) { return null; }
  }

  // ---- records: one per target, under the reviewer's ID ------------------------------------
  function recPrefix(r) { return PREFIX + r + ":"; }
  function sentKey(r) { return PREFIX + r + ":~sent"; }
  function allRecords(r) {
    var p = recPrefix(r);
    return store.keys(p).filter(function (k) { return k !== sentKey(r); })
      .map(function (k) { return parse(store.get(k)); })
      .filter(function (x) { return x && x.target; });
  }
  function clean(s) { return (s || "").replace(/\r\n?/g, "\n").replace(CONTROL_RE, "").trim(); }
  function today() {
    var d = new Date();
    return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
  }
  // null: finished; "": no decision yet; otherwise the i18n key of what is missing
  function problem(rec) {
    if (!rec || !rec.decision) return "";
    var note = clean(rec.note), cite = clean(rec.citation);
    if (rec.decision === "accept" && rec.needsCitation && !cite) return "msg.need_citation";
    if (rec.decision === "needs_discussion" && !note) return "msg.need_note";
    if (EMAIL_RE.test(note) || PHONE_RE.test(note) || EMAIL_RE.test(cite) || PHONE_RE.test(cite)) return "msg.contact";
    return null;
  }
  function asDecision(rec) {
    var d = { kind: rec.kind, target: rec.target, decision: rec.decision, checks: (rec.checks || []).slice() };
    var note = clean(rec.note), cite = clean(rec.citation);
    if (note) d.note = note;
    d.date = rec.date;
    if (cite) d.citation = cite;
    return d;
  }
  function sig(d) { return JSON.stringify([d.decision, d.checks, d.note || "", d.citation || "", d.date]); }
  function sentMap(r) { return parse(store.get(sentKey(r))) || { items: {} }; }

  // ---- cards --------------------------------------------------------------------------------
  var cards = Array.prototype.slice.call(doc.querySelectorAll(".card"));
  var current = null;
  // the controls are written once in the page (#decide-tpl) and copied into each card here
  var decideTpl = $("decide-tpl");
  cards.forEach(function (card) {
    var n = card.getAttribute("data-n");
    var col = card.querySelector(".decide-col");
    col.innerHTML = decideTpl ? decideTpl.innerHTML.replace(/__N__/g, n) : "";
    var hint = col.querySelector("[data-hint]");
    if (hint) hint.textContent = card.getAttribute("data-cite") === "1" ? t("field.citation.required") : t("field.citation.optional");
  });

  function readCard(card) {
    var chosen = card.querySelector('input[type="radio"]:checked');
    var checks = [];
    each(card.querySelectorAll('input[name="check"]'), function (box) { if (box.checked) checks.push(box.value); });
    return {
      decision: chosen ? chosen.value : "",
      checks: checks,
      note: card.querySelector("textarea").value,
      citation: card.querySelector('input[name="citation"]').value
    };
  }
  function cardRecord(card, r) {
    return parse(store.get(recPrefix(r) + card.getAttribute("data-target")));
  }
  function saveCard(card) {
    var r = reviewer();
    if (!r) return;
    var st = readCard(card);
    var key = recPrefix(r) + card.getAttribute("data-target");
    var prev = parse(store.get(key));
    if (!st.decision && !st.checks.length && !clean(st.note) && !clean(st.citation)) {
      if (prev) store.del(key);
    } else {
      var rec = {
        kind: card.getAttribute("data-kind"), target: card.getAttribute("data-target"),
        decision: st.decision, checks: st.checks, note: st.note, citation: st.citation, date: today(),
        needsCitation: card.getAttribute("data-cite") === "1", batch: BATCH, file: FILE,
        n: +card.getAttribute("data-n"), seq: +card.getAttribute("data-seq"), fp: FP,
        label: card.querySelector(".claim").textContent.trim().slice(0, 160)
      };
      if (prev && prev.date && prev.decision === rec.decision && JSON.stringify(prev.checks) === JSON.stringify(rec.checks) &&
          clean(prev.note) === clean(rec.note) && clean(prev.citation) === clean(rec.citation)) rec.date = prev.date;
      store.set(key, JSON.stringify(rec));
    }
    renderCard(card);
    refresh();
  }
  function renderCard(card) {
    var r = reviewer();
    var rec = r ? cardRecord(card, r) : null;
    var why = problem(rec);
    var msg = card.querySelector(".msg");
    var cite = card.querySelector('input[name="citation"]');
    var note = card.querySelector("textarea");
    card.classList.remove("is-accept", "is-reject", "is-needs_discussion", "is-incomplete");
    msg.className = "msg";
    msg.textContent = "";
    cite.removeAttribute("aria-invalid");
    note.removeAttribute("aria-invalid");
    cite.required = !!(rec && rec.decision === "accept" && card.getAttribute("data-cite") === "1");
    note.required = !!(rec && rec.decision === "needs_discussion");
    if (!rec || !rec.decision) return;
    card.classList.add("is-" + rec.decision);
    if (why) {
      card.classList.add("is-incomplete");
      msg.classList.add("bad");
      msg.textContent = t(why);
      if (why === "msg.need_citation") cite.setAttribute("aria-invalid", "true");
      if (why === "msg.need_note") note.setAttribute("aria-invalid", "true");
      return;
    }
    var sent = sentMap(r).items[rec.target];
    msg.classList.add("good");
    if (!sent) msg.textContent = t("msg.saved");
    else if (sent === sig(asDecision(rec))) msg.textContent = t("msg.sent");
    else { msg.className = "msg bad"; msg.textContent = t("msg.changed"); }
  }
  function fillCard(card, rec) {
    each(card.querySelectorAll('input[type="radio"]'), function (x) { x.checked = !!rec && x.value === rec.decision; });
    each(card.querySelectorAll('input[name="check"]'), function (x) { x.checked = !!rec && (rec.checks || []).indexOf(x.value) >= 0; });
    card.querySelector("textarea").value = rec ? rec.note || "" : "";
    card.querySelector('input[name="citation"]').value = rec ? rec.citation || "" : "";
  }
  function setEnabled(on) {
    cards.forEach(function (card) {
      card.setAttribute("aria-disabled", on ? "false" : "true");
      each(card.querySelectorAll(".decide-col input, .decide-col textarea, .decide-col button"), function (x) { x.disabled = !on; });
    });
  }
  function loadCards() {
    var r = reviewer();
    setEnabled(!!r);
    cards.forEach(function (card) {
      fillCard(card, r ? cardRecord(card, r) : null);
      renderCard(card);
    });
  }
  function clearCard(card) {
    var st = readCard(card);
    if ((clean(st.note) || clean(st.citation)) && !window.confirm(t("msg.clear_confirm"))) return;
    fillCard(card, null);
    saveCard(card);
  }

  // ---- progress, the index and the send panel ----------------------------------------------
  function refresh() {
    var r = reviewer();
    var recs = r ? allRecords(r) : [];
    var byTarget = {};
    recs.forEach(function (x) { byTarget[x.target] = x; });
    var prog = $("progress");
    if (prog) {
      var done = cards.filter(function (card) {
        var x = byTarget[card.getAttribute("data-target")];
        return x && problem(x) === null;
      }).length;
      prog.textContent = r ? t("progress", { done: done, total: cards.length }) : t("reviewer.needed");
    }
    each(doc.querySelectorAll("[data-batch][data-total]"), function (li) {
      var b = li.getAttribute("data-batch");
      var total = +li.getAttribute("data-total");
      var n = recs.filter(function (x) { return x.batch === b && problem(x) === null; }).length;
      var span = li.querySelector("[data-prog]");
      span.textContent = n ? t("progress", { done: n, total: total }) : "";
      span.classList.toggle("done", n >= total);
    });
    renderSend(r, recs);
  }
  function renderSend(r, recs) {
    var summary = $("send-summary");
    if (!summary) return;
    var ready = recs.filter(function (x) { return problem(x) === null; });
    var unfinished = recs.filter(function (x) { return x.decision && problem(x); });
    var sent = r ? sentMap(r) : { items: {} };
    var fresh = ready.filter(function (x) { return sent.items[x.target] !== sig(asDecision(x)); });
    var lines = [];
    if (!r) lines.push(t("reviewer.needed"));
    else if (!ready.length) lines.push(t("send.none"));
    else {
      lines.push(tn("send.ready", ready.length));
      if (sent.at) lines.push(tn("send.new", fresh.length));
    }
    if (unfinished.length) lines.push(tn("send.incomplete", unfinished.length));
    summary.textContent = lines.join(" ");
    var list = $("send-incomplete");
    list.textContent = "";
    unfinished.sort(bySeq).forEach(function (x) {
      var li = doc.createElement("li");
      var a = doc.createElement("a");
      a.href = (x.file === FILE ? "" : x.file) + "#c" + x.n;
      a.textContent = x.label + " — " + t(problem(x));
      li.appendChild(a);
      list.appendChild(li);
    });
    list.hidden = !unfinished.length;
    $("send-share").disabled = !ready.length;
    $("send-save").disabled = !ready.length;
    var last = $("send-last");
    last.textContent = sent.at ? t("send.last", { when: new Date(sent.at).toLocaleString() }) : "";
  }
  function bySeq(a, b) {
    return (a.seq || 0) - (b.seq || 0) || (a.target < b.target ? -1 : a.target > b.target ? 1 : 0);
  }

  // ---- the decision file --------------------------------------------------------------------
  function buildFile(r) {
    var ready = allRecords(r).filter(function (x) { return problem(x) === null; }).sort(bySeq);
    var fps = {};
    ready.forEach(function (x) { fps[x.fp || ""] = 1; });
    var out = { format: "marsad-review-decisions", version: 1, reviewer_id: r, created: new Date().toISOString() };
    var only = Object.keys(fps);
    if (only.length === 1 && only[0]) out.queue = only[0];
    out.decisions = ready.map(asDecision);
    return out;
  }
  function fileName(r) {
    var d = new Date();
    var hm = ("0" + d.getHours()).slice(-2) + ("0" + d.getMinutes()).slice(-2);
    return "marsad-decisions-" + today() + "-" + hm + "-" + r.slice(4, 10);
  }
  function status(text, bad) {
    var p = $("send-status");
    p.className = "msg " + (bad ? "bad" : "good");
    p.textContent = text;
  }
  function markSent(r, file) {
    var m = sentMap(r);
    m.items = m.items || {};
    file.decisions.forEach(function (d) { m.items[d.target] = sig(d); });
    m.at = file.created;
    store.set(sentKey(r), JSON.stringify(m));
    loadCards();
    refresh();
  }
  function download(text, name) {
    var url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    var a = doc.createElement("a");
    a.href = url;
    a.download = name;
    a.hidden = true;
    body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(url); a.remove(); }, 4000);
  }
  function canShare(f) {
    try { return !!(navigator.canShare && navigator.canShare({ files: [f] })); } catch (e) { return false; }
  }
  function send(saveOnly) {
    var r = reviewer();
    if (!r) return;
    var file = buildFile(r);
    if (!file.decisions.length) return;
    var text = JSON.stringify(file, null, 1) + "\n";
    var name = fileName(r);
    if (!saveOnly && navigator.share && typeof File === "function") {
      // Android browsers share only some file types (.txt, not .json): same content either way
      var options = [new File([text], name + ".json", { type: "application/json" }),
                     new File([text], name + ".txt", { type: "text/plain" })];
      for (var i = 0; i < options.length; i++) {
        if (!canShare(options[i])) continue;
        var f = options[i];
        navigator.share({ files: [f] }).then(function () {
          markSent(r, file);
          status(f.name.slice(-4) === ".txt" ? t("send.shared_txt", { file: f.name }) : t("send.shared", { file: f.name }));
        }, function (e) {
          if (e && e.name === "AbortError") status(t("send.cancelled"), true);
          else status(t("send.failed", { error: e && e.name ? e.name : String(e) }), true);
        });
        return;
      }
    }
    download(text, name + ".json");
    markSent(r, file);
    status(t("send.saved", { file: name + ".json" }));
  }

  // ---- reviewer setup -----------------------------------------------------------------------
  function renderWho() {
    var r = reviewer();
    $("who-text").textContent = r ? t("reviewer.current", { id: r }) : t("reviewer.none");
    $("who-change").hidden = !r;
    var box = $("reviewer");
    if (box) box.classList.toggle("is-set", !!r);
  }
  function openReviewer(prefill, note) {
    var box = $("reviewer");
    if (!box) return;
    box.classList.add("is-open");
    var input = $("reviewer-id");
    input.value = prefill || reviewer() || "";
    $("reviewer-msg").textContent = note || "";
  }
  function saveReviewer() {
    var v = normaliseId($("reviewer-id").value);
    var msg = $("reviewer-msg");
    if (!ID_RE.test(v)) {
      msg.className = "msg bad";
      msg.textContent = t("reviewer.invalid");
      return;
    }
    store.set(K_REVIEWER, v);
    msg.className = "msg good";
    msg.textContent = t("reviewer.saved");
    $("reviewer").classList.remove("is-open");
    if (location.hash) history.replaceState(null, "", location.pathname + location.search);
    renderWho();
    loadCards();
    refresh();
    if (cards.length) focusCard(cards[0]);
  }

  // ---- keyboard -----------------------------------------------------------------------------
  function focusCard(card) {
    if (!card) return;
    current = card;
    card.focus({ preventScroll: true });
    card.scrollIntoView({ block: "start" });
  }
  function currentCard() {
    var a = doc.activeElement;
    var c = a && a.closest ? a.closest(".card") : null;
    if (c) return c;
    if (current) return current;
    for (var i = 0; i < cards.length; i++) {
      if (cards[i].getBoundingClientRect().bottom > 0) return cards[i];
    }
    return null;
  }
  function move(card, delta) {
    var i = cards.indexOf(card);
    var next = cards[i + delta];
    if (next) focusCard(next);
    else if (delta > 0 && $("send")) { $("send").focus(); $("send").scrollIntoView({ block: "start" }); }
  }
  function choose(card, value) {
    var radio = card.querySelector('input[type="radio"][value="' + value + '"]');
    if (!radio || radio.disabled) return;
    radio.checked = true;
    saveCard(card);
    var why = problem(cardRecord(card, reviewer()));
    if (why === "msg.need_citation") card.querySelector('input[name="citation"]').focus();
    else if (why === "msg.need_note" || why === "msg.contact") card.querySelector("textarea").focus();
    else move(card, 1);
  }
  doc.addEventListener("keydown", function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey || e.isComposing) return;
    var el = e.target;
    var tag = el && el.tagName;
    if (tag === "TEXTAREA" || (tag === "INPUT" && el.type === "text") || tag === "SELECT" || (el && el.isContentEditable)) {
      var inCard = el.closest && el.closest(".card");
      if (e.key === "Escape" && inCard) { e.preventDefault(); focusCard(inCard); }
      else if (e.key === "Enter" && inCard && el.name === "citation") { e.preventDefault(); move(inCard, 1); }
      return;
    }
    var card = currentCard();
    var key = { KeyA: "accept", KeyR: "reject", KeyD: "needs_discussion" }[e.code];
    if (e.code === "KeyS" && $("send")) { e.preventDefault(); $("send").focus(); $("send").scrollIntoView({ block: "start" }); return; }
    if (!card) return;
    if (key) { e.preventDefault(); choose(card, key); return; }
    var digit = /^Digit([1-9])$/.exec(e.code);
    if (digit) {
      var box = card.querySelectorAll('input[name="check"]')[+digit[1] - 1];
      if (box && !box.disabled) { e.preventDefault(); box.checked = !box.checked; saveCard(card); }
      return;
    }
    if (e.code === "KeyJ") { e.preventDefault(); move(card, 1); }
    else if (e.code === "KeyK") { e.preventDefault(); move(card, -1); }
    else if (e.code === "KeyC") { e.preventDefault(); card.querySelector('input[name="citation"]').focus(); }
    else if (e.code === "KeyN") { e.preventDefault(); card.querySelector("textarea").focus(); }
    else if (e.code === "KeyX") { e.preventDefault(); clearCard(card); }
  });

  // ---- wiring -------------------------------------------------------------------------------
  var list = doc.querySelector(".cards");
  if (list) {
    list.addEventListener("change", function (e) { var c = e.target.closest(".card"); if (c) saveCard(c); });
    list.addEventListener("input", function (e) {
      if (e.target.matches("textarea, input[type=\"text\"]")) { var c = e.target.closest(".card"); if (c) saveCard(c); }
    });
    list.addEventListener("click", function (e) {
      var b = e.target.closest("[data-act=\"clear\"]");
      if (b) clearCard(b.closest(".card"));
    });
    list.addEventListener("focusin", function (e) { var c = e.target.closest(".card"); if (c) current = c; });
  }
  if ($("reviewer-save")) {
    $("reviewer-save").addEventListener("click", saveReviewer);
    $("reviewer-id").addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); saveReviewer(); } });
  }
  $("who-change").addEventListener("click", function () { openReviewer(); });
  if ($("send-share")) {
    $("send-share").addEventListener("click", function () { send(false); });
    $("send-save").addEventListener("click", function () { send(true); });
  }
  if ($("clear-device")) {
    $("clear-device").addEventListener("click", function () {
      var r = reviewer();
      if (!r) return;
      var keys = store.keys(recPrefix(r));
      var n = keys.filter(function (k) { return k !== sentKey(r); }).length;
      if (!n || !window.confirm(t("index.clear.confirm", { n: n, id: r }))) return;
      keys.forEach(function (k) { store.del(k); });
      $("clear-status").textContent = t("index.clear.done", { n: n });
      loadCards();
      refresh();
    });
  }
  window.addEventListener("storage", function () { renderWho(); loadCards(); refresh(); });
  window.addEventListener("pageshow", function (e) { if (e.persisted) { renderWho(); loadCards(); refresh(); } });

  renderWho();
  var fromLink = linkedId();
  if (fromLink && fromLink !== reviewer()) openReviewer(fromLink, t("reviewer.from_link", { id: fromLink }));
  loadCards();
  refresh();

  // offline: keep visited pages (https or localhost only; a page opened as a file needs nothing)
  if ("serviceWorker" in navigator && window.isSecureContext && /^https?:$/.test(location.protocol)) {
    navigator.serviceWorker.register(body.getAttribute("data-fetch")).then(function () {
      if (window.caches) return caches.open("marsad-review-1").then(function (c) { return c.add(location.href.split("#")[0]); });
    }).catch(function () {});
  }
})();
