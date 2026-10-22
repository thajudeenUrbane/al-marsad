/* Sky Atlas, part 10 of 10 — captions, the "you are here" line, Back and Home, the view
   state in the address, language, depth, reading and teaching modes, and start-up. */
function caption() {
  let s = t("caption." + S.view);
  if (S.view === "map" || S.view === "globe") s += " " + t("caption.map_count", { n: fmt(META.counts.located), total: fmt(META.counts.places) });
  if (S.view === "lineage" && S.lineageOf >= 0) s = t("caption.lineage_of", { name: nameOf(S.lineageOf) }) + " " + s;
  if (S.view === "chains") s += " " + t("caption.chains_count", { n: fmt(D.chains.length), k: fmt(CHAIN_D.filter((x) => x > 0).length) });
  $("caption").textContent = s;
}
function here() {
  let s = S.blend !== null && Math.abs(S.blend - Math.round(S.blend)) > 0.02
    ? t("here.blend", { a: t("view." + BLEND[Math.floor(S.blend)]), b: t("view." + BLEND[Math.min(BLEND.length - 1, Math.floor(S.blend) + 1)]), pct: Math.round((S.blend % 1) * 100) })
    : t("view." + S.view);
  if (S.guide) s += " · " + t("guide.progress", { k: fmt(S.guide.k + 1), n: fmt(S.guide.T.stops.length) });
  else if (S.trace.path) s += " · " + t("here.trace");
  else if (S.preset) s += " · " + t("here.vantage", { name: t("preset." + S.preset) });
  else if (S.focus >= 0) s += " · " + nameOf(S.focus);
  else s += " · " + t("here.all", { n: fmt(n) });
  if (S.period) s += " · " + t("here.period", { a: fmt(S.period[0]), b: fmt(S.period[1]) });
  if (S.play) s += " · " + t("play.year", { y: fmt(S.play.y) });
  $("here").textContent = s;
  writeHash();
}
function insets() { // tell the renderer which part of the sky the plates cover
  if (!R) return;
  const st = $("stage").getBoundingClientRect(), x = { l: 0, r: 0, t: 0, b: 0 };
  const phone = st.width < 761;
  for (const id of ["record", "guide", "drawer"]) {
    const el = $(id);
    if (el.hidden) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0) continue;
    if (phone || id === "guide") x.b = Math.max(x.b, st.bottom - r.top);
    else if (r.left + r.width / 2 > st.left + st.width / 2) x.r = Math.max(x.r, st.right - r.left);
    else x.l = Math.max(x.l, r.right - st.left);
  }
  const tb = document.querySelector(".toolbars").getBoundingClientRect();
  x.t = Math.max(44, tb.bottom - st.top + 4);
  document.documentElement.style.setProperty("--caption-top", (tb.bottom - st.top + 8) + "px");
  x.b = Math.min(x.b, st.height * 0.7);
  R.setInset(x);
}
function stageTop() { document.documentElement.style.setProperty("--stage-top", ($("stage").offsetTop + 8) + "px"); insets(); }

// ------------------------------------------------------------------ Back and Home
function snapshot() {
  return { view: S.view, focus: S.focus, lineageOf: S.lineageOf, preset: S.preset, cam: R.camera(),
    trace: S.trace.threads ? [S.trace.from, S.trace.to, S.trace.k] : null };
}
function pushHistory() {
  if (!R || restoring) return;
  S.history.push(snapshot());
  if (S.history.length > 60) S.history.shift();
  $("back").disabled = false;
}
let restoring = false;
function back() {
  const s = S.history.pop();
  $("back").disabled = !S.history.length;
  if (!s) return;
  restoring = true;
  if (S.guide) { stopPlay(); S.guide = null; S.markers = []; $("guide").hidden = true; $("app").classList.remove("has-guide"); }
  S.lineageOf = s.lineageOf;
  if (s.view !== S.view || s.view === "lineage") setView(s.view, { camera: false, record: false });
  if (s.trace) trace(s.trace[0], s.trace[1], s.trace[2]);
  else if (s.preset) applyPreset(s.preset);
  else if (s.focus >= 0) focus(s.focus, { record: false, fly: false });
  else { S.focus = -1; S.trace.path = null; S.preset = null; S.lineClasses = null; emphasise(null); closeRecord(); }
  R.flyTo(s.cam, 800);
  restoring = false;
  here(); insets();
}
function home() {
  pushHistory();
  if (S.guide) endTour();
  if (S.play) playHistory(false);
  S.compare = -1; S.preset = null; S.lineClasses = null; S.trace.path = null; S.trace.threads = null;
  closeDrawer();
  S.focus = -1; S.lit = null; S.litLines = null;
  closeRecord();
  setView("sky", { record: false });
}

// ------------------------------------------------------------------ the view state: a short code in the address
function viewState() {
  const c = R.camera();
  const st = { v: S.view, d: S.depth, l: LANG, c: [+c.yaw.toFixed(2), +c.pitch.toFixed(2), Math.round(c.dist), ...c.target.map(Math.round)] };
  if (S.focus >= 0) st.f = ND.id[S.focus];
  if (S.view === "lineage" && S.lineageOf >= 0) st.lin = ND.id[S.lineageOf];
  if (S.preset) st.p = S.preset;
  if (S.period) st.per = S.period;
  if (S.trace.threads) st.tr = [ND.id[S.trace.from], ND.id[S.trace.to], S.trace.k];
  if (S.guide) st.tour = [S.guide.T.dynamic ? S.guide.T.dynamic + "-" + ND.id[S.guide.T.of] : S.guide.T.key, S.guide.k];
  if (S.blend !== null) st.b = +S.blend.toFixed(2);
  st.fp = META.fingerprint;
  return st;
}
function viewToken() { // letters, digits, dot, dash, underscore and tilde only: what an Artifact link carries
  const s = viewState(), parts = ["v." + s.v, "d." + s.d, "c." + [Math.round(s.c[0] * 100), Math.round(s.c[1] * 100), ...s.c.slice(2)].join(".")];
  if (s.l === "ar") parts.push("l.ar");
  if (s.f) parts.push("f." + s.f);
  if (s.lin) parts.push("lin." + s.lin);
  if (s.p) parts.push("p." + s.p);
  if (s.per) parts.push("per." + s.per.join("."));
  if (s.tr) parts.push("tr." + s.tr.join("."));
  if (s.tour) parts.push("tour." + s.tour.join("."));
  if (s.b !== undefined) parts.push("b." + Math.round(s.b * 100));
  return parts.join("~");
}
function parseToken(tok) {
  const st = {};
  for (const part of tok.replace(/^#/, "").split("~")) {
    const [k, ...v] = part.split(".");
    if (k === "c") { const c = v.map(Number); st.c = [c[0] / 100, c[1] / 100, c[2], c[3], c[4], c[5]]; }
    else if (k === "per") st.per = v.map(Number);
    else if (k === "tr") st.tr = [v[0], v[1], +v[2]];
    else if (k === "tour") st.tour = [v[0], +v[1]];
    else if (k === "b") st.b = +v[0] / 100;
    else st[k] = v.join(".");
  }
  return st;
}
function applyViewState(input) {
  let st;
  try { st = input.trim().startsWith("{") ? JSON.parse(input) : parseToken(input.trim()); } catch (e) { return false; }
  if (!st || !st.v || !VIEWS.includes(st.v)) return false;
  restoring = true;
  if (st.l && st.l !== LANG) setLang(st.l, true);
  if (st.d && st.d !== S.depth) setDepth(st.d);
  if (st.per && st.per.length === 2) setPeriod(st.per);
  if (st.lin) S.lineageOf = byId(st.lin);
  if (st.b !== undefined && st.b !== null) { $("blend").value = String(st.b); setBlend(st.b); }
  else setView(st.v, { camera: false, record: false, instant: true });
  if (st.tour) {
    const [key, k] = st.tour;
    let T = TOURS.find((x) => x.key === key);
    const m = /^(life|place|around)-(.+)$/.exec(key || "");
    if (!T && m && byId(m[2]) >= 0) T = dynamicTour(byId(m[2]));
    if (!T && key === "mine") T = myTour();
    if (T) startTour(T, k);
  } else if (st.tr) trace(byId(st.tr[0]), byId(st.tr[1]), st.tr[2]);
  else if (st.p) applyPreset(st.p);
  else if (st.f && byId(st.f) >= 0) focus(byId(st.f), { record: false, fly: false });
  if (st.c) R.flyTo({ yaw: st.c[0], pitch: st.c[1], dist: st.c[2], target: st.c.slice(3, 6) }, 0);
  restoring = false;
  here();
  return true;
}
let hashTimer = 0, lastHash = "";
function writeHash() {
  if (!R || restoring) return;
  clearTimeout(hashTimer);
  hashTimer = setTimeout(() => {
    const tok = "#" + viewToken();
    if (tok === lastHash) return;
    lastHash = tok;
    try { history.replaceState(null, "", tok); } catch (e) { /* the address cannot change here */ }
  }, 600);
}

// ------------------------------------------------------------------ language, depth, reading and teaching
function applyStatic() {
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => el.setAttribute("placeholder", t(el.dataset.i18nPh)));
  document.querySelectorAll("[data-i18n-aria]").forEach((el) => el.setAttribute("aria-label", t(el.dataset.i18nAria)));
  document.title = t("page.title");
}
function setLang(l, quiet) {
  LANG = l; STR = l === "ar" ? AR : EN;
  document.documentElement.lang = l; document.documentElement.dir = l === "ar" ? "rtl" : "ltr";
  $("lang").setAttribute("lang", l === "ar" ? "en" : "ar");
  applyStatic();
  $("lang-note").hidden = l !== "ar";
  store.set("marsad-atlas-lang", l);
  if (l === "ar") { LOG.arabic++; saveLog(); if (!quiet) checkMilestones(); }
  if (SEARCH) { buildSearch(); for (const k of Object.keys(VCACHE)) delete VCACHE[k]; if (R) { CUR = S.blend === null ? viewData(S.view) : CUR; } rerender(); }
  if (!quiet) announce(t("lang.announce"));
  stageTop();
}
function setDepth(d) {
  S.depth = d; document.documentElement.dataset.depth = d;
  document.querySelectorAll(".depth button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.depth === d)));
  store.set("marsad-atlas-depth", d);
  if (d === "research") $("perf").hidden = false;
  rerender();
}
function setBig(v) {
  S.show.big = v; document.documentElement.classList.toggle("big", v);
  store.set("marsad-atlas-big", v ? 1 : 0);
  buildLabels(); R.requestDraw(); stageTop();
}
function setSpeak(v) {
  S.speak = v;
  $("guide-speak").setAttribute("aria-pressed", String(v));
  if (!v && window.speechSynthesis) window.speechSynthesis.cancel();
  if (v && S.guide) speak(spokenStop(S.guide.T.stops[S.guide.k]));
}
function setClassroom(v) { // large type, the guide playing on its own, the whole screen where allowed
  S.classroom = v;
  document.documentElement.classList.toggle("classroom", v);
  setBig(v || !!store.get("marsad-atlas-big", 0));
  if (v) {
    try { const p = document.documentElement.requestFullscreen && document.documentElement.requestFullscreen(); if (p && p.catch) p.catch(() => {}); } catch (e) { /* not allowed here */ }
    closeDrawer();
    if (!S.guide) startTour(TOURS[0], LOG.tours.ecliptic ? Math.min(LOG.tours.ecliptic - 1, TOURS[0].stops.length - 1) : 0);
    togglePlay(true);
    toast(t("classroom.on"));
  } else {
    stopPlay();
    try { if (document.fullscreenElement && document.exitFullscreen) document.exitFullscreen().catch(() => {}); } catch (e) { /* nothing to leave */ }
  }
}
function rerender() {
  buildLabels(); R.requestDraw();
  caption(); here();
  if (!$("record").hidden && S.focus >= 0 && !S.trace.path) renderRecord(S.focus);
  if (S.guide) renderStop();
  if (!$("drawer").hidden) renderDrawer();
  if (!$("welcome").hidden) welcomeCounts();
  refreshText();
}
function welcomeCounts() {
  const c = META.counts;
  $("welcome-counts").textContent = t("welcome.counts", { people: fmt(c.kinds.person), events: fmt(c.kinds.event), places: fmt(c.kinds.place), claims: fmt(c.assertions) });
}

// ------------------------------------------------------------------ Play history: start, pause, resume, leave
function playButton() {
  if (playTimerH) { clearInterval(playTimerH); playTimerH = 0; $("play").setAttribute("aria-pressed", "false"); $("play").textContent = t("play.resume"); return; }
  if (S.play && S.play.y < YEARS[1]) {
    $("play").setAttribute("aria-pressed", "true"); $("play").textContent = t("play.pause");
    playTimerH = setInterval(() => {
      S.play.y++;
      const items = [];
      for (let i = 0; i < n; i++) { const sp = yearSpan(i); if (sp && Math.floor(sp[0]) === S.play.y && visibleNow(i)) items.push(i); }
      S.flash = { t0: performance.now(), items: reduced ? [] : items.slice(0, 400) };
      $("play-year").textContent = t("play.year", { y: fmt(S.play.y) });
      if (S.view === "globe") R.setExtra(globeLines());
      restyle(); here();
      if (S.play.y >= YEARS[1]) { clearInterval(playTimerH); playTimerH = 0; $("play").setAttribute("aria-pressed", "false"); $("play").textContent = t("play.again"); announce(t("play.end")); }
    }, reduced ? 1400 : 800);
    return;
  }
  playHistory(true);
}

// ------------------------------------------------------------------ start
async function start() {
  let data;
  try { data = await unpack(); }
  catch (e) { $("loading").replaceChildren(h("p", null, t("error.unpack"))); return; }
  model(data);
  buildMsCite();
  const hash = location.hash || "";
  const lang = /^#ar$/.test(hash) || /(^#|~)l\.ar(~|$)/.test(hash) ? "ar" : store.get("marsad-atlas-lang", "en");
  if (lang === "ar") setLang("ar", true);
  const depth = store.get("marsad-atlas-depth", "discover");
  S.depth = ["discover", "study", "research"].includes(depth) ? depth : "discover";
  document.documentElement.dataset.depth = S.depth;
  document.querySelectorAll(".depth button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.depth === S.depth)));
  if (store.get("marsad-atlas-big", 0)) { S.show.big = true; document.documentElement.classList.add("big"); }
  api.lightIndex = LIGHT;
  try {
    R = window.AtlasSky({ glCanvas: $("gl"), ovCanvas: $("ov"), cvCanvas: $("cv"), n, api });
  } catch (e) {
    $("loading").replaceChildren(h("p", null, t("error.webgl")));
    return;
  }
  if (!R.hasGL()) toast(t("gpu.none"));
  if (META.ask) $("ask-slot").replaceWith(h("a", { class: "chip", href: META.ask, target: "_blank", rel: "noopener" }, t("nav.ask")));
  loadVoices();
  if (window.speechSynthesis) window.speechSynthesis.onvoiceschanged = loadVoices;
  buildSearch();
  buildTours();
  buildQuests();
  CUR = viewData("sky");
  S.visible = CUR.vis;
  R.setPositions(CUR.pos);
  R.flyTo(viewCamera("sky"), 0);
  restyle();
  caption(); stageTop();
  window.addEventListener("resize", stageTop);
  $("loading").hidden = true;
  wireSearch();
  // the play-history year carries a way out of history mode
  $("play-year").after(h("button", { type: "button", class: "mini", id: "play-clear", hidden: true, "aria-label": t("play.clear"), onclick: () => playHistory(false) }, "×"));
  new MutationObserver(() => { $("play-clear").hidden = !S.play; }).observe($("play-year"), { childList: true, characterData: true, subtree: true });
  document.querySelectorAll(".views button").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));
  document.querySelectorAll(".depth button").forEach((b) => b.addEventListener("click", () => setDepth(b.dataset.depth)));
  document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => { TAB = b.dataset.tab; renderDrawer(); }));
  document.querySelectorAll("[data-viewpoint]").forEach((b) => b.addEventListener("click", () => {
    const [yaw, pitch] = VIEWPOINTS[b.dataset.viewpoint];
    R.flyTo({ yaw, pitch }, 900); announce(t("viewpoint.announce", { name: t("viewpoint." + b.dataset.viewpoint) }));
  }));
  $("blend").addEventListener("input", (e) => setBlend(+e.target.value));
  $("play").addEventListener("click", playButton);
  $("lang").addEventListener("click", () => setLang(LANG === "ar" ? "en" : "ar"));
  $("back").addEventListener("click", back);
  $("home").addEventListener("click", home);
  $("open-atlas").addEventListener("click", () => ($("drawer").hidden ? openDrawer() : closeDrawer()));
  $("close-atlas").addEventListener("click", closeDrawer);
  $("close-record").addEventListener("click", () => { closeRecord(); if (!S.guide) clearFocus(); });
  $("zoom-in").addEventListener("click", () => R.zoom(0.7));
  $("zoom-out").addEventListener("click", () => R.zoom(1.4));
  $("zoom-fit").addEventListener("click", () => R.flyTo(viewCamera(S.view), 800));
  $("guide-prev").addEventListener("click", () => goStop(S.guide.k - 1));
  $("guide-next").addEventListener("click", () => goStop(S.guide.k + 1));
  $("guide-play").addEventListener("click", () => togglePlay());
  $("guide-speak").addEventListener("click", () => setSpeak(!S.speak));
  $("guide-end").addEventListener("click", () => { if (S.classroom) setClassroom(false); endTour(); });
  $("guide-min").addEventListener("click", () => {
    const g = $("guide"), folded = g.classList.toggle("folded");
    $("guide-min").setAttribute("aria-expanded", String(!folded));
    $("guide-min").textContent = folded ? t("guide.unfold") : t("guide.fold");
    insets();
  });
  $("welcome-guide").addEventListener("click", () => { store.set("marsad-atlas-welcomed", 1); startTour(TOURS[0], 0); });
  $("welcome-explore").addEventListener("click", () => { store.set("marsad-atlas-welcomed", 1); $("welcome").hidden = true; });
  document.addEventListener("keydown", (e) => {
    const inField = /input|select|textarea/i.test(document.activeElement.tagName);
    if (e.key === "/" && !inField) { e.preventDefault(); $("search").focus(); }
    if (e.key === "Escape" && !inField) {
      if (!$("drawer").hidden) closeDrawer();
      else if (S.classroom) setClassroom(false);
      else if (S.guide) endTour();
      else if (S.focus >= 0 || S.trace.path || S.preset) clearFocus();
      else back();
    }
  });
  document.addEventListener("fullscreenchange", () => { if (!document.fullscreenElement && S.classroom) setClassroom(false); stageTop(); });
  window.addEventListener("hashchange", () => { if (location.hash && location.hash !== lastHash && location.hash !== "#ar") applyViewState(location.hash); });
  if (hash && hash !== "#ar" && hash.length > 4 && applyViewState(hash)) { /* opened at a shared view */ }
  else if (!store.get("marsad-atlas-welcomed", 0)) { welcomeCounts(); $("welcome").hidden = false; }
  if (lang === "ar") checkMilestones();
  refreshText();
  shareStart();
  window.__atlas = { S, t, focus, startTour, setView, setLang, setDepth, trace, search, TOURS: () => TOURS, n: () => n, openDrawer, renderDrawer,
    R: () => R, endTour, goStop, applyPreset, compare, back, home, setBlend, viewToken, applyViewState, openPair, playHistory, setPeriod, QUESTS: () => QUESTS, toggleStar, byId, ask, SHARE, decide, addNote, mergesCsv };
  document.documentElement.dataset.ready = "1";
}
if (!("DecompressionStream" in window)) { $("loading").replaceChildren(h("p", null, t("error.unpack"))); }
else start();
