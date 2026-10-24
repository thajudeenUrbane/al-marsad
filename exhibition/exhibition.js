/* al-Marṣad exhibition: the halls, the keys, the presenter notes, the timer and the live views.
   Everything it loads comes from this machine (exhibition/serve.py); nothing goes out.

   Keys: ← → (PageUp, PageDown, Space) move between halls, 1–8 jump, Home/End; P notes; T timer
   (Shift+T restarts it); F full screen; S still picture instead of the live view; Esc closes the
   full view, hands the keys back from a live view, or closes the notes.
   ?notes opens the same walk as a notes window for a second screen; the two follow each other. */
(() => {
  "use strict";
  const N = window.EXHIBITION_NUMBERS || {};
  const PBUH = "peace and blessings be upon him";
  const PLAN = [1, 2, 6, 5, 3, 2, 4, 1]; // minutes planned for each hall: 24 in all
  const START = PLAN.map((_, i) => PLAN.slice(0, i).reduce((a, b) => a + b, 0));
  const ASK_HALL = 6, ASK_BY = 20 * 60; // the requests (hall 7) begin by minute 20
  const STILL_AFTER = 12000; // a live view that is not ready by then shows its still picture
  const ATLAS_LANG = "marsad-atlas-lang";
  // In Arabic the Atlas lays its language note over the stage; these rows keep them apart.
  const ATLAS_PATCH = ".app{grid-template-rows:auto auto auto 1fr}#lang-note{grid-row:2}.app>p.band:not(#lang-note){grid-row:3}#stage{grid-row:4}";

  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const root = document.documentElement;
  const halls = $$(".hall");
  const sheet = $("#sheet"), timerEl = $("#timer");
  const notesWindow = new URLSearchParams(location.search).has("notes");
  let bc = null;
  try { bc = new BroadcastChannel("marsad-exhibition"); } catch (e) { /* one window only */ }
  let current = -1, t0 = 0, tick = 0, expandedFig = null;

  /* ---------------- numbers and text from numbers.js ---------------- */
  const en = new Intl.NumberFormat("en-GB"), ar = new Intl.NumberFormat("ar-u-nu-arab");
  const get = key => key.split(".").reduce((o, k) => (o == null ? undefined : o[k]), N);

  function sign() {
    const s = document.createElement("span");
    s.className = "hon";
    s.setAttribute("role", "img");
    s.setAttribute("aria-label", PBUH);
    s.textContent = "ﷺ";
    return s;
  }
  // Text from the data, with each ﷺ set as an honorific that never starts a line.
  function setText(el, text) {
    el.textContent = "";
    String(text).split("ﷺ").forEach((part, i, all) => {
      if (i) el.append(sign());
      el.append(i < all.length - 1 ? part.replace(/ $/, " ") : part);
    });
  }
  function fill() {
    $$("[data-n]").forEach(el => {
      const v = get(el.dataset.n);
      if (v === undefined) return;
      el.textContent = typeof v === "number" ? (el.closest('[lang="ar"]') ? ar : en).format(v) : String(v);
    });
    $$("[data-t]").forEach(el => {
      const v = get(el.dataset.t);
      if (v !== undefined) setText(el, v);
    });
  }
  // The words "(peace and blessings be upon him)" go with the first ﷺ on each screen.
  function firstMention() {
    halls.forEach(hall => {
      const first = $$(`.hon[aria-label="${PBUH}"]`, hall).find(s => !s.closest(".notes"));
      if (!first) return;
      const at = first.closest(".nw") || first;
      const after = at.nextElementSibling;
      if (after && after.classList.contains("words")) return;
      const w = document.createElement("span");
      w.className = "words";
      w.setAttribute("aria-hidden", "true");
      w.textContent = "(peace and blessings be upon him)";
      at.after(" ", w);
    });
  }
  // The presenter's name and contact live in a git-ignored file; without it the line stays blank.
  function presenter() {
    return fetch("presenter.local.json", { cache: "no-store" })
      .then(r => (r.ok ? r.json() : {}))
      .catch(() => ({}))
      .then(p => $$("[data-presenter]").forEach(el => {
        const v = p && p[el.dataset.presenter];
        if (typeof v === "string" && v.trim()) el.textContent = v.trim();
      }));
  }

  /* ---------------- halls ---------------- */
  function show(i, quiet, first) {
    i = Math.max(0, Math.min(halls.length - 1, i | 0));
    if (i === current) return;
    const from = current;
    collapse();
    halls.forEach((h, k) => h.classList.toggle("on", k === i));
    current = i;
    history.replaceState(null, "", "#hall-" + (i + 1));
    const a = document.activeElement;
    if (a && a.tagName === "IFRAME") a.blur();
    if (!notesWindow) halls[i].focus({ preventScroll: true });
    bar();
    notes();
    [i, i + 1].forEach(load);
    // Unless T started it already, the timer starts on leaving the opening, which is given its planned minute.
    if (!t0 && !first && i > 0) startTimer(from === 0 ? Date.now() - PLAN[0] * 60000 : 0);
    paintTimer();
    if (!quiet && bc) bc.postMessage({ type: "hall", i, t0 });
  }
  const next = () => show(current + 1), prev = () => show(current - 1);

  function bar() {
    $(".bar .n").textContent = `${current + 1} / ${halls.length}`;
    $(".bar .t").textContent = halls[current].dataset.title;
    $(".bar .prev").disabled = current === 0;
    $(".bar .next").disabled = current === halls.length - 1;
  }
  function notes() {
    const h = halls[current], src = $(".notes", h), after = halls[current + 1];
    $(".sheet-title", sheet).textContent = `${current + 1} / ${halls.length} · ${h.dataset.title}`;
    $(".sheet-next", sheet).textContent = after ? `Next: ${after.dataset.title}` : "The last hall";
    $(".sheet-body", sheet).innerHTML = src ? src.innerHTML : "";
  }
  function toggleSheet(on) {
    if (!notesWindow) sheet.hidden = on === undefined ? !sheet.hidden : !on;
  }

  /* ---------------- timer ---------------- */
  const mmss = s => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  function startTimer(at, quiet) {
    t0 = at || Date.now();
    clearInterval(tick);
    tick = setInterval(paintTimer, 1000);
    paintTimer();
    if (!quiet && bc) bc.postMessage({ type: "timer", t0 });
  }
  function paintTimer() {
    if (current < 0) return;
    let clock = "00:00", plan = "starts with the next hall", late = false;
    if (t0) {
      const s = Math.max(0, Math.floor((Date.now() - t0) / 1000)), end = (START[current] + PLAN[current]) * 60;
      clock = mmss(s);
      plan = `hall ${current + 1}: planned ${START[current]}–${START[current] + PLAN[current]} min`;
      if (current < ASK_HALL && s >= ASK_BY) { late = true; plan = "begin the requests now (hall 7)"; }
      else if (s > end + 60) { late = true; plan += ", running long"; }
    }
    $(".clock", timerEl).textContent = clock;
    $(".plan", timerEl).textContent = plan;
    timerEl.classList.toggle("late", late);
  }
  function toggleTimer() {
    if (!notesWindow) timerEl.hidden = !timerEl.hidden;
    if (!t0) startTimer();
  }
  function restartTimer() {
    timerEl.hidden = false;
    startTimer();
  }

  function toggleFull() {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    else if (root.requestFullscreen) root.requestFullscreen().catch(() => {});
  }

  /* ---------------- live views: the Atlas and the expeditions, same origin ---------------- */
  function load(i) {
    const h = halls[i];
    if (!h || notesWindow) return;
    $$("figure.live", h).forEach(fig => {
      if (fig.dataset.loaded) return;
      fig.dataset.loaded = "1";
      const iframe = $("iframe", fig), first = $(".steps [data-hash]", fig);
      if (fig.dataset.live === "atlas") {
        try { localStorage.setItem(ATLAS_LANG, JSON.stringify("en")); } catch (e) { /* the Atlas then follows the browser */ }
      }
      iframe.addEventListener("load", () => framed(fig, iframe));
      press(fig, first);
      iframe.src = fig.dataset.src + (first ? first.dataset.hash : "");
      fig._wait = setTimeout(() => { if (!fig.dataset.ready) still(fig, true, "auto"); }, STILL_AFTER);
    });
  }
  function framed(fig, iframe) {
    let win, doc;
    try { win = iframe.contentWindow; doc = iframe.contentDocument; } catch (e) { return; }
    if (!doc || !doc.documentElement || win.location.href === "about:blank") return;
    win.addEventListener("keydown", e => fromFrame(e, win));
    if (fig.dataset.live !== "atlas") return ready(fig);
    const st = doc.createElement("style");
    st.textContent = ATLAS_PATCH;
    doc.head.append(st);
    const done = () => doc.documentElement.dataset.ready === "1";
    if (done()) return ready(fig);
    const mo = new MutationObserver(() => { if (done()) { mo.disconnect(); ready(fig); } });
    mo.observe(doc.documentElement, { attributes: true, attributeFilter: ["data-ready"] });
  }
  function ready(fig) {
    fig.dataset.ready = "1";
    clearTimeout(fig._wait);
    if (fig.dataset.mode === "auto") still(fig, false);
  }
  function press(fig, btn) {
    $$(".steps [data-hash]", fig).forEach(b => b.setAttribute("aria-pressed", String(b === btn)));
  }
  function step(fig, btn) {
    press(fig, btn);
    if (fig.classList.contains("still-on")) still(fig, true, fig.dataset.mode);
    const iframe = $("iframe", fig), hash = btn.dataset.hash;
    if (!fig.dataset.ready) { iframe.src = fig.dataset.src + hash; return; }
    try {
      const win = iframe.contentWindow;
      if (win.location.hash === hash && win.__atlas && win.__atlas.applyViewState) win.__atlas.applyViewState(hash);
      else win.location.hash = hash;
    } catch (e) {
      iframe.src = fig.dataset.src + hash;
    }
  }
  function still(fig, on, why) {
    const img = $(".still", fig), note = $(".frame-note", fig);
    if (on) {
      const b = $('.steps [aria-pressed="true"]', fig);
      const src = (b && b.dataset.still) || img.dataset.src;
      if (img.getAttribute("src") !== src) img.src = src;
    }
    img.hidden = !on;
    note.hidden = !on;
    fig.classList.toggle("still-on", on);
    fig.dataset.mode = on ? why || "manual" : "";
  }
  function toggleStill() {
    const fig = expandedFig || (halls[current] && $("figure.live", halls[current]));
    if (fig) still(fig, !fig.classList.contains("still-on"), "manual");
  }
  function expand(fig) {
    expandedFig = fig;
    fig.classList.add("expanded");
    document.body.classList.add("expanded");
    let x = $(".unexpand", fig);
    if (!x) {
      x = document.createElement("button");
      x.type = "button";
      x.className = "unexpand";
      x.textContent = "Close the full view (Esc)";
      x.onclick = () => collapse();
      $(".frame", fig).append(x);
    }
    $("iframe", fig).focus();
  }
  function collapse() {
    if (!expandedFig) return false;
    expandedFig.classList.remove("expanded");
    document.body.classList.remove("expanded");
    expandedFig = null;
    if (current >= 0) halls[current].focus({ preventScroll: true });
    return true;
  }
  // Keys pressed inside a live view. The halaqa room steps with PageUp/PageDown itself (for
  // clickers), so those move halls only outside it; Esc always hands the keys back to the walk.
  function fromFrame(e, win) {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === "Escape") {
      if (!collapse()) halls[current].focus({ preventScroll: true });
      return;
    }
    if ((e.key === "PageDown" || e.key === "PageUp") && !/^#halaqa-/.test(win.location.hash)) {
      e.preventDefault();
      if (e.key === "PageDown") next(); else prev();
    }
  }

  /* ---------------- keys ---------------- */
  function onKey(e) {
    if (e.metaKey || e.ctrlKey || e.altKey || e.defaultPrevented) return;
    const t = e.target, tag = t && t.tagName, k = e.key;
    if (t && (t.isContentEditable || tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT")) return;
    if ((k === " " || k === "Enter") && t && t.closest && t.closest("button, a")) return;
    if (k === "ArrowRight" || k === "PageDown" || k === " ") next();
    else if (k === "ArrowLeft" || k === "PageUp") prev();
    else if (k === "Home") show(0);
    else if (k === "End") show(halls.length - 1);
    else if (/^[1-8]$/.test(k)) show(+k - 1);
    else if (k === "p" || k === "P") toggleSheet();
    else if (k === "t" || k === "T") (e.shiftKey ? restartTimer : toggleTimer)();
    else if (k === "f" || k === "F") toggleFull();
    else if (k === "s" || k === "S") toggleStill();
    else if (k === "Escape") {
      if (!collapse()) {
        if (notesWindow || sheet.hidden) return;
        toggleSheet(false);
      }
    } else return;
    e.preventDefault();
  }

  /* ---------------- start ---------------- */
  if (notesWindow) {
    root.classList.add("notes-window");
    sheet.hidden = false;
    timerEl.hidden = false;
    document.title = "Notes · al-Marṣad";
  }
  halls.forEach(h => { h.tabIndex = -1; });
  fill();
  firstMention();
  $(".bar .prev").onclick = prev;
  $(".bar .next").onclick = next;
  $(".bar .open-notes").onclick = () => window.open(location.pathname + "?notes" + location.hash, "marsad-notes", "width=1000,height=760");
  if (notesWindow) $(".bar .open-notes").hidden = true;
  $$("figure.live").forEach(fig => {
    $$(".steps [data-hash]", fig).forEach(b => { b.onclick = () => step(fig, b); });
    const ex = $(".steps .expand", fig);
    if (ex) ex.onclick = () => expand(fig);
  });
  document.addEventListener("keydown", onKey);
  if (bc) {
    bc.onmessage = ({ data: m }) => {
      if (!m) return;
      if (m.type === "hello") { bc.postMessage({ type: "state", i: current, t0 }); return; }
      if (m.t0 && m.t0 !== t0) startTimer(m.t0, true);
      if (typeof m.i === "number" && m.i !== current) show(m.i, true);
    };
  }
  const at = location.hash.match(/^#hall-(\d+)$/);
  show(at ? +at[1] - 1 : 0, true, true);
  if (bc) bc.postMessage({ type: "hello" });
  window.__exhibition = { show, hall: () => current };
  Promise.all([presenter(), document.fonts ? document.fonts.ready : null]).then(() => { root.dataset.ready = "1"; });
})();
