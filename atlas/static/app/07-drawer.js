/* Sky Atlas, part 7 of 8 — the Atlas drawer: Guide, Show, Index, Logbook, Text view and
   Key, and the logbook's milestones. */
let TAB = "guide";
function openDrawer(tab) {
  if (tab) TAB = tab;
  $("drawer").hidden = false; $("open-atlas").setAttribute("aria-expanded", "true");
  renderDrawer();
  insets();
}
function closeDrawer() { $("drawer").hidden = true; $("open-atlas").setAttribute("aria-expanded", "false"); insets(); }
function renderDrawer() {
  document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === TAB)));
  const body = $("drawer-body");
  body.replaceChildren(...({ guide: drawerGuide, show: drawerShow, index: drawerIndex, log: drawerLog, text: drawerText, key: drawerKey })[TAB]().filter(Boolean));
  body.scrollTop = 0;
}
const title = (s) => h("p", { class: "section-title" }, s);

function tourCard(T) {
  const seen = LOG.tours[T.key] || 0;
  return h("div", { class: "tour" }, h("h3", null, tourTitle(T)), h("p", null, tourLead(T)),
    h("p", { class: "muted" }, t("tour.stops", { n: fmt(T.stops.length) }) + (seen ? " · " + t("tour.reached", { k: fmt(seen) }) : "")),
    h("div", { class: "row" }, h("button", { type: "button", class: "chip primary small", onclick: () => startTour(T, 0) }, t("tour.start")),
      seen > 1 && seen < T.stops.length ? h("button", { type: "button", class: "chip small", onclick: () => startTour(T, seen - 1) }, t("tour.resume", { k: fmt(seen) })) : null));
}
function drawerGuide() {
  const out = [title(t("guide.tours")), h("p", { class: "muted" }, t("guide.tours_note"))];
  for (const T of TOURS) out.push(tourCard(T));
  const mine = myTour();
  out.push(title(t("tour.mine.title")));
  out.push(mine && mine.stops.length > 1 ? tourCard(mine) : h("p", { class: "muted" }, t("tour.mine.empty")));
  out.push(title(t("presets.title")), h("p", { class: "muted" }, t("presets.note")));
  for (const p of META.presets) out.push(h("div", { class: "tour" }, h("h3", null, t("preset." + p.key)), h("p", null, t("preset." + p.key + ".about")),
    h("div", { class: "row" }, h("button", { type: "button", class: "chip small", "aria-pressed": String(S.preset === p.key), onclick: () => applyPreset(p.key) }, t("presets.go")))));
  // trace a thread: from, to, swap, find
  out.push(title(t("guide.trace")), h("p", { class: "muted" }, t("trace.intro")));
  let a = S.trace.from, b = S.trace.to;
  const box = h("div", { class: "index-tools" },
    namePicker("trace-from", t("trace.from"), (i) => { a = i; S.trace.from = i; }, a),
    namePicker("trace-to", t("trace.to"), (i) => { b = i; S.trace.to = i; }, b),
    h("div", { class: "row" },
      h("button", { type: "button", class: "chip primary small", id: "trace-find", onclick: () => trace(S.trace.from, S.trace.to) }, t("trace.find")),
      h("button", { type: "button", class: "chip small", onclick: () => { const x = S.trace.from; S.trace.from = S.trace.to; S.trace.to = x; renderDrawer(); } }, t("trace.swap")),
      h("label", { class: "toggle inline" }, h("input", { type: "checkbox", id: "trace-lineage-d", checked: S.trace.lineage ? true : null, onchange: (e) => { S.trace.lineage = e.target.checked; } }), h("span", null, t("trace.lineage_short")))));
  out.push(box);
  out.push(title(t("guide.from_here")), h("p", { class: "muted" }, t("guide.from_here_note")));
  out.push(title(t("guide.stories")), h("p", { class: "note" }, t("trace.stories")));
  return out;
}
function toggleRow(id, get, label, note, fn, disabled) {
  const inp = h("input", { type: "checkbox", id, checked: get() ? true : null, disabled: disabled ? true : null, onchange: (e) => fn(e.target.checked) });
  return h("label", { class: "toggle", for: id }, inp, h("span", null, label, note ? h("small", null, note) : null));
}
function radioRow(name, value, get, label, note, fn) {
  const inp = h("input", { type: "radio", name, id: name + "-" + value, value, checked: get() === value ? true : null, onchange: () => fn(value) });
  return h("label", { class: "toggle", for: name + "-" + value }, inp, h("span", null, label, note ? h("small", null, note) : null));
}
function drawerShow() {
  const c = META.counts;
  const out = [title(t("show.light"))];
  const setLight = (v) => { S.show.light = v; restyle(); announce(t("light.announce." + v)); };
  out.push(radioRow("light", "generation", () => S.show.light, t("light.generation"), t("light.generation_note"), setLight));
  out.push(radioRow("light", "chain", () => S.show.light, t("light.chain"), t("light.chain_note", { n: fmt(CHAIN_D.filter((x) => x > 0).length), max: fmt(CHAIN_MAX) }), setLight));
  out.push(radioRow("light", "none", () => S.show.light, t("light.none"), t("light.none_note"), setLight));
  out.push(title(t("show.marks")));
  out.push(toggleRow("show-lines", () => S.show.lines, t("show.lines"), t("show.lines_note"), (v) => { S.show.lines = v; restyle(); }));
  out.push(toggleRow("show-names", () => S.show.names, t("show.names"), null, (v) => { S.show.names = v; restyle(); announce(t(v ? "names.on" : "names.off")); }));
  out.push(toggleRow("show-background", () => S.show.background, t("show.background"), t("show.background_note", { n: fmt(c.background) }), (v) => { S.show.background = v; restyle(); }));
  out.push(toggleRow("show-turning", () => S.show.turning, t("show.turning"), t("show.turning_note", { n: fmt(c.opponents), k: fmt(c.turned) }), (v) => { S.show.turning = v; restyle(); if (S.focus >= 0) renderRecord(S.focus); }));
  out.push(toggleRow("show-hollow", () => S.show.hollow, t("show.hollow"), t("show.hollow_note"), (v) => { S.show.hollow = v; restyle(); }));
  out.push(toggleRow("show-scenery", () => S.show.scenery, t("show.scenery"), t("show.scenery_note"), (v) => { S.show.scenery = v; R.setScenery(v); announce(t(v ? "scenery.on" : "scenery.off")); }));
  out.push(toggleRow("show-cluster", () => S.show.cluster, t("show.cluster"), t("show.cluster_note"), (v) => { S.show.cluster = v; R.requestDraw(); announce(t(v ? "cluster.on" : "cluster.off")); }));
  out.push(toggleRow("show-orbit", () => S.show.orbit, t("show.orbit"), reduced ? t("show.orbit_reduced") : t("show.orbit_note"), (v) => { S.show.orbit = v && !reduced; R.requestDraw(); }, reduced));
  // the period
  out.push(title(t("scrub.legend")));
  const on = h("input", { type: "checkbox", id: "scrub-on", checked: S.period ? true : null });
  const mk = (id, val) => h("input", { type: "range", id, min: YEARS[0], max: YEARS[1], step: 1, value: val });
  const from = mk("scrub-from", S.period ? S.period[0] : YEARS[0]), to = mk("scrub-to", S.period ? S.period[1] : YEARS[1]);
  const fo = h("output", { for: "scrub-from" }), tout = h("output", { for: "scrub-to" });
  const sync = () => {
    let a = +from.value, b = +to.value; if (a > b) [a, b] = [b, a];
    fo.textContent = t("scrub.year", { y: fmt(+from.value) }); tout.textContent = t("scrub.year", { y: fmt(+to.value) });
    setPeriod(on.checked ? [a, b] : null);
  };
  on.addEventListener("change", sync); from.addEventListener("input", () => { on.checked = true; sync(); }); to.addEventListener("input", () => { on.checked = true; sync(); });
  fo.textContent = t("scrub.year", { y: fmt(+from.value) }); tout.textContent = t("scrub.year", { y: fmt(+to.value) });
  out.push(h("label", { class: "toggle", for: "scrub-on" }, on, h("span", null, t("scrub.on"))),
    h("div", { class: "scrub-row" }, h("label", { for: "scrub-from" }, t("scrub.from")), from, fo),
    h("div", { class: "scrub-row" }, h("label", { for: "scrub-to" }, t("scrub.to")), to, tout),
    h("p", { class: "muted small" }, t("scrub.note")));
  out.push(h("div", { class: "row" }, h("button", { type: "button", class: "chip small", onclick: () => { closeDrawer(); $("play").click(); } }, t("play.start")), h("span", { class: "muted small" }, t("play.note"))));
  // kinds
  out.push(title(t("show.kinds")));
  for (const k of KINDS) out.push(toggleRow("kind-" + k, () => S.show.kinds[k], t("kind.plural." + k) + " · " + fmt(c.kinds[k]), null, (v) => { S.show.kinds[k] = v; restyle(); refreshText(); }));
  // reading and teaching
  out.push(title(t("show.reading")));
  out.push(toggleRow("show-big", () => S.show.big, t("show.big"), t("show.big_note"), (v) => setBig(v)));
  out.push(toggleRow("show-speak", () => S.speak, t("speak.guide"), t("speak.note"), (v) => setSpeak(v)));
  out.push(toggleRow("show-classroom", () => S.classroom, t("classroom.title"), t("classroom.note"), (v) => setClassroom(v)));
  // many stars, and how they are drawn
  out.push(title(t("scale.legend")));
  const sel = h("select", { class: "field", id: "scale-pick", "aria-label": t("scale.label") }, [0, 2000, 10000, 50000].map((v) => h("option", { value: v, selected: R.testCount() === v ? true : null }, v ? fmt(v) : t("scale.none"))));
  sel.addEventListener("change", () => { R.setTestLoad(+sel.value); $("perf").hidden = !(+sel.value) && R.mode() === "gl" && S.depth !== "research"; announce(+sel.value ? t("scale.announce", { n: fmt(+sel.value) }) : t("scale.announce_off")); });
  out.push(h("label", { for: "scale-pick", class: "muted" }, t("scale.label")), sel, h("p", { class: "muted small" }, t("scale.note")));
  out.push(toggleRow("show-gpu", () => R.mode() === "gl", t("gpu.title"), R.hasGL() ? t("gpu.note") : t("gpu.none"), (v) => { R.setMode(v ? "gl" : "2d"); $("perf").hidden = false; announce(t(v ? "gpu.on" : "gpu.off")); }, !R.hasGL()));
  out.push(toggleRow("show-perf", () => !$("perf").hidden, t("perf.title"), null, (v) => { $("perf").hidden = !v; R.requestDraw(); }));
  return out;
}

let INDEX = { kind: "person", sort: "e3", q: "", lim: 80, dupes: false };
function drawerIndex() {
  const kinds = h("div", { class: "kinds", role: "group", "aria-label": t("index.kinds") }, KINDS.map((k) => h("button", { type: "button", class: "chip small", "aria-pressed": String(INDEX.kind === k), onclick: () => { INDEX.kind = k; INDEX.lim = 80; renderDrawer(); } }, t("kind.plural." + k) + " · " + fmt(META.counts.kinds[k]))));
  const sort = h("select", { class: "field", id: "index-sort", "aria-label": t("index.sort") }, ["e3", "az", "links", "text"].map((s) => h("option", { value: s, selected: INDEX.sort === s ? true : null }, t("sort." + s))));
  sort.addEventListener("change", () => { INDEX.sort = sort.value; renderDrawer(); });
  const q = h("input", { class: "field", id: "index-q", type: "search", value: INDEX.q, placeholder: t("index.filter"), "aria-label": t("index.filter") });
  const dupes = toggleRow("index-dupes", () => INDEX.dupes, t("index.dupes"), t("index.dupes_note", { g: fmt(DUPES.stats.groups), e: fmt(DUPES.stats.entries) }), (v) => { INDEX.dupes = v; INDEX.lim = 80; fill(); });
  const list = h("ul", { class: "plain index-list" });
  let items = [];
  const fill = () => {
    const s = norm(INDEX.q);
    items = [];
    for (let i = 0; i < n; i++) if (KIND[i] === INDEX.kind && (!s || SEARCH[i].some((f) => f.includes(s))) && (!INDEX.dupes || DUPES.has(i))) items.push(i);
    if (INDEX.dupes) items.sort((a, b) => (baseName(a) < baseName(b) ? -1 : baseName(a) > baseName(b) ? 1 : a - b));
    else items = INDEX.kind === "person" ? sortPeople(items, INDEX.sort) : items.sort((a, b) => INDEX.sort === "links" ? deg[b] - deg[a] : INDEX.sort === "text" ? textOrder(a) - textOrder(b) : nameOf(a).localeCompare(nameOf(b), LANG));
    list.replaceChildren(...items.slice(0, INDEX.lim).map((i) => h("li", null, glyph(i), nameBtn(i), h("span", { class: "count" }, S.depth === "discover" ? "" : t("records.count", { n: fmt(deg[i]) })))));
    if (items.length > INDEX.lim) list.append(h("li", null, h("button", { type: "button", class: "chip small", onclick: () => { INDEX.lim += 200; fill(); } }, t("more.next", { n: fmt(Math.min(200, items.length - INDEX.lim)), total: fmt(items.length) }))));
    if (!items.length) list.append(h("li", { class: "muted" }, t("search.none")));
  };
  q.addEventListener("input", () => { INDEX.q = q.value; INDEX.lim = 80; fill(); });
  fill();
  const copy = h("button", { type: "button", class: "chip small", onclick: () => copyText(items.map((i) => nameOf(i) + "\t" + kindText(i) + "\t" + deg[i]).join("\n"), $("drawer-body")) }, t("index.copy"));
  return [title(t("index.title")), h("p", { class: "muted" }, t("index.note")),
    h("div", { class: "index-tools" }, kinds, sort, q, dupes, copy), INDEX.sort === "links" || INDEX.sort === "e3" ? h("p", { class: "note" }, t("sort.links_note")) : null, list];
}

// ------------------------------------------------------------------ the logbook
function markSeen(i) {
  const id = ND.id[i], k = KIND[i];
  if (k === "person") LOG.seen[id] = 1;
  if (k === "event") LOG.events[id] = 1;
  if (k === "place") LOG.places[id] = 1;
  saveLog(); checkMilestones(); checkQuests();
}
const MILESTONES = [
  ["first_light", () => Object.keys(LOG.seen).length + Object.keys(LOG.events).length + Object.keys(LOG.places).length, 1],
  ["ten_stars", () => Object.keys(LOG.seen).length, 10],
  ["hundred_stars", () => Object.keys(LOG.seen).length, 100],
  ["five_events", () => Object.keys(LOG.events).length, 5],
  ["forty_events", () => Object.keys(LOG.events).length, 40],
  ["five_places", () => Object.keys(LOG.places).length, 5],
  ["how_we_know", () => LOG.ladders, 1],
  ["chain", () => LOG.chains, 1],
  ["lineage", () => LOG.lineages, 1],
  ["trace", () => LOG.traces, 1],
  ["compare", () => LOG.compares, 1],
  ["recall", () => LOG.recalls, 5],
  ["tour_done", () => Object.keys(LOG.done).filter((k) => k.startsWith("tour:")).length, 1],
  ["ecliptic", () => LOG.tours.ecliptic || 0, () => META.ecliptic.length],
  ["both_tongues", () => LOG.arabic, 1],
];
function checkMilestones() {
  for (const [key, val, goal] of MILESTONES) {
    const g = typeof goal === "function" ? goal() : goal;
    if (!LOG.done[key] && val() >= g) {
      LOG.done[key] = new Date().toISOString().slice(0, 10);
      saveLog();
      toast(t("ms.unlocked", { name: t("ms." + key) }));
    }
  }
}
function meterRow(cls, name, how, v, g, done, action) {
  return h("div", { class: "milestone" + (done ? " done" : "") }, h("span", { class: "seal", "aria-hidden": "true" }, done ? "✓" : ""),
    h("div", null, h("b", null, name), h("small", null, how), done ? h("small", null, t("log.done_on", { date: done })) : h("div", { class: "bar-meter", role: "progressbar", "aria-valuenow": v, "aria-valuemax": g }, h("span", { style: `width:${(Math.min(v, g) / g * 100).toFixed(0)}%` })),
      !done ? h("small", null, t("quest.progress", { v: fmt(Math.min(v, g)), g: fmt(g) })) : null, action || null));
}
function drawerLog() {
  const seen = Object.keys(LOG.seen).length, ev = Object.keys(LOG.events).length, pl = Object.keys(LOG.places).length;
  const out = [title(t("log.title")), h("p", { class: "muted" }, t("log.note")),
    h("div", { class: "stats" }, h("div", null, h("b", null, fmt(seen)), h("span", null, t("log.people", { n: fmt(META.counts.kinds.person) }))),
      h("div", null, h("b", null, fmt(ev)), h("span", null, t("log.events", { n: fmt(META.counts.kinds.event) }))),
      h("div", null, h("b", null, fmt(pl)), h("span", null, t("log.places", { n: fmt(META.counts.kinds.place) }))))];
  // the star chart
  out.push(title(t("star.title")), h("p", { class: "muted" }, t("star.note")));
  const stars = STARS.map(byId).filter((i) => i >= 0);
  if (stars.length) {
    out.push(h("ul", { class: "plain index-list" }, stars.map((i) => h("li", null, glyph(i), nameBtn(i), h("button", { type: "button", class: "chip small", "aria-label": t("star.remove"), onclick: () => { toggleStar(i); renderDrawer(); } }, "×")))));
    out.push(h("div", { class: "row" }, stars.length > 1 ? h("button", { type: "button", class: "chip primary small", onclick: () => startTour(myTour()) }, t("star.tour")) : null,
      h("button", { type: "button", class: "chip small", onclick: () => copyText(stars.map((i) => citeRecord(i)).join("\n\n"), $("drawer-body")) }, t("star.copy"))));
  } else out.push(h("p", { class: "muted" }, t("star.empty")));
  out.push(title(t("quest.title")), h("p", { class: "muted" }, t("quest.note")));
  for (const q of QUESTS) out.push(meterRow("quest", t("quest." + q.key), t("quest." + q.key + ".how"), q.val(), q.goal, LOG.done["quest:" + q.key],
    !LOG.done["quest:" + q.key] ? h("button", { type: "button", class: "chip small", onclick: q.go }, t("quest.go")) : null));
  out.push(title(t("log.milestones")));
  for (const [key, val, goal] of MILESTONES) { const g = typeof goal === "function" ? goal() : goal; out.push(meterRow("ms", t("ms." + key), t("ms." + key + ".how"), val(), g, LOG.done[key])); }
  const clearBox = h("div", { class: "row", style: "margin-top:14px" });
  const ask = () => clearBox.replaceChildren(h("span", { class: "muted" }, t("log.clear_ask")),
    h("button", { type: "button", class: "chip small", onclick: () => { LOG = LOG_DEFAULT(); saveLog(); renderDrawer(); } }, t("log.clear_yes")),
    h("button", { type: "button", class: "chip small", onclick: () => renderDrawer() }, t("log.clear_no")));
  clearBox.append(h("button", { type: "button", class: "chip small", onclick: ask }, t("log.clear")));
  out.push(clearBox);
  return out;
}

// ------------------------------------------------------------------ the text view: the picture in words
function regionCounts() {
  const v = S.view, vis = S.visible || new Uint8Array(n).fill(1), r = [];
  const count = (f) => { let k = 0; for (let i = 0; i < n; i++) if (i !== LIGHT && vis[i] && S.show.kinds[KIND[i]] && f(i)) k++; return k; };
  if (v === "sky") {
    r.push([t("region.light"), 1]);
    r.push([t("region.spiral"), META.ecliptic.length], [t("region.ring"), count((i) => KIND[i] === "story")]);
    r.push([t("region.linked"), count((i) => deg[i] > 0 && !isBack(i) && KIND[i] !== "story")], [t("region.background"), count((i) => isBack(i))], [t("region.unlinked"), count((i) => deg[i] === 0)]);
  } else if (v === "time") { r.push([t("region.axis"), count((i) => !!yearSpan(i))], [t("region.band"), count((i) => !yearSpan(i) && nf("tb", i) !== undefined)], [t("region.no_date"), count((i) => !yearSpan(i) && nf("tb", i) === undefined)]); }
  else if (v === "map" || v === "globe") { const on = count((i) => nf("geo", i) || (nf("pl", i) !== undefined && nf("geo", nf("pl", i)))); r.push([t("region.on_map"), on], [t("region.no_place"), count(() => true) - on]); }
  else if (v === "stories") { const on = count((i) => KIND[i] === "story" || [...neighbours(i)].some((j) => KIND[j] === "story")); r.push([t("region.dial"), on], [t("region.no_story"), count(() => true) - on]); }
  else if (v === "chains") { const on = count((i) => !!CHAIN_D[i]); r.push([t("region.chain"), on], [t("region.no_chain"), count(() => true) - on]); }
  else if (v === "book") { const on = count((i) => firstMs(i) !== undefined); r.push([t("region.in_text"), on], [t("region.not_text"), count(() => true) - on]); }
  else if (v === "lineage") r.push([t("region.tree"), count(() => true)]);
  return r;
}
let textLim = 120;
function describe() { // one paragraph a screen reader can hear at once
  const kinds = KINDS.map((k) => { let c = 0; for (let i = 0; i < n; i++) if (KIND[i] === k && visibleNow(i)) c++; return c ? t("textalt.kind_count", { n: fmt(c), kind: t("kind.plural." + k) }) : null; }).filter(Boolean).join(t("sep.list"));
  const parts = [t("textalt.summary", { view: t("view." + S.view), depth: t("depth." + S.depth), shown: fmt(shownCount), total: fmt(n), kinds, links: fmt(linesCount) })];
  if (S.focus >= 0) parts.push(t("textalt.focus", { name: nameOf(S.focus), kind: S.focus === LIGHT ? t("light.kind") : kindText(S.focus) }));
  if (S.period) parts.push(t("textalt.period", { a: fmt(S.period[0]), b: fmt(S.period[1]) }));
  if (S.play) parts.push(t("textalt.play", { y: fmt(S.play.y) }));
  if (S.guide) parts.push(t("textalt.tour", { title: tourTitle(S.guide.T), k: fmt(S.guide.k + 1), n: fmt(S.guide.T.stops.length), name: nameOf(S.guide.T.stops[S.guide.k]) }));
  if (S.preset) parts.push(t("here.vantage", { name: t("preset." + S.preset) }));
  return parts.join(" ");
}
let liveTimer = 0;
function refreshText() {
  clearTimeout(liveTimer);
  liveTimer = setTimeout(() => { if (D) $("live-summary").textContent = describe(); }, 400);
  if (!$("drawer").hidden && TAB === "text") renderDrawer();
}
function drawerText() {
  const out = [title(t("textalt.title")), h("p", null, describe())];
  out.push(h("p", { class: "note warn" }, t("textalt.status", { n: fmt(META.counts.assertions) })));
  const hidden = KINDS.filter((k) => !S.show.kinds[k]).map((k) => t("kind.plural." + k));
  out.push(h("p", { class: "muted" }, hidden.length ? t("textalt.hidden", { list: hidden.join(t("sep.list")) }) : t("textalt.nothing_hidden")));
  out.push(h("ul", { class: "plain counts" }, regionCounts().map(([k, v]) => h("li", null, h("span", null, k), h("span", { class: "count" }, fmt(v))))));
  if (S.focus >= 0 && KIND[S.focus] === "event") {
    const g = peopleAt(S.focus);
    out.push(h("p", null, t("textalt.presence", { event: nameOf(S.focus), present: [...g.led, ...g.part].map(nameOf).join(t("sep.list")) || "—", absent: [...g.absent].map(nameOf).join(t("sep.list")) || "—" })));
  }
  if (S.view === "globe" || S.view === "map") {
    const ms = moves().map((m) => `${nameOf(m.a)} → ${nameOf(m.b)} (${Math.floor(m.y)})`);
    out.push(h("p", null, t("textalt.moves", { list: ms.join(t("sep.list")) || "—" })));
  }
  if (S.trace.path) out.push(h("p", null, t("textalt.thread", { a: nameOf(S.trace.from), b: nameOf(S.trace.to), steps: fmt(S.trace.path.length - 1) })));
  // every item in this view, as a list of buttons
  const items = [];
  for (let i = 0; i < n; i++) if (visibleNow(i) && (!S.lit || S.lit.has(i))) items.push(i);
  const sorted = sortPeople(items);
  out.push(title(t("textalt.all_items", { n: fmt(items.length) })));
  const ul = h("ul", { class: "plain index-list" }, sorted.slice(0, textLim).map((i) => h("li", null, glyph(i), nameBtn(i), h("span", { class: "count" }, kindText(i)))));
  if (sorted.length > textLim) ul.append(h("li", null, h("button", { type: "button", class: "chip small", onclick: () => { textLim += 400; renderDrawer(); } }, t("more.next", { n: fmt(Math.min(400, sorted.length - textLim)), total: fmt(sorted.length) }))));
  out.push(ul);
  if (S.depth === "research") out.push(...researchPanel());
  return out;
}
function researchPanel() { // the view as data: counts, sources, the view state, the corpus fingerprint
  const c = META.counts, src = new Map();
  for (let k = 0; k < nc; k++) { const s = CL.src[k]; src.set(s, (src.get(s) || 0) + 1); }
  const state = viewState();
  const ta = h("textarea", { class: "copy-box", id: "viewstate-json", rows: 6, readonly: true }); ta.value = JSON.stringify(state, null, 1);
  const open = h("input", { class: "field", id: "viewstate-open", placeholder: t("state.open_ph"), "aria-label": t("state.open") });
  return [title(t("research.title")),
    h("p", null, t("research.counts", { nodes: fmt(c.nodes), claims: fmt(c.assertions), records: fmt(c.records), links: fmt(linesCount) })),
    h("p", null, t("research.status", { list: Object.entries(c.status).map(([k, v]) => `${k}: ${fmt(v)}`).join(t("sep.list")) })),
    h("p", { class: "muted" }, t("research.sources")),
    h("ul", { class: "plain counts" }, [...src.entries()].sort((a, b) => b[1] - a[1]).map(([s, v]) => h("li", null, h("span", null, s >= 0 ? META.sources[s].label : "—"), h("span", { class: "count" }, fmt(v))))),
    h("p", null, t("research.version", { v: META.fingerprint || "—" })),
    S.blend !== null ? h("p", null, t("research.blend", { v: S.blend.toFixed(2) })) : null,
    h("p", { class: "muted" }, t("state.note")), ta,
    h("div", { class: "row" },
      h("button", { type: "button", class: "chip small", onclick: () => copyText(JSON.stringify(viewState()), $("drawer-body")) }, t("state.copy")),
      h("button", { type: "button", class: "chip small", onclick: () => copyText(location.href.split("#")[0] + "#" + viewToken(), $("drawer-body")) }, t("state.copy_link"))),
    h("div", { class: "row" }, open, h("button", { type: "button", class: "chip small", onclick: () => { if (!applyViewState(open.value)) toast(t("state.bad")); } }, t("state.open")))];
}

// ------------------------------------------------------------------ the key
function keyGlyph(kind, style) { const cv = h("canvas", { width: 28, height: 28, "aria-hidden": "true" }); drawGlyph(cv.getContext("2d"), kind, style); return cv; }
function drawerKey() {
  const row = (g, ttl, text) => h("div", { class: "key-row" }, g, h("p", null, h("b", null, ttl), " ", text));
  const c = META.counts;
  const out = [title(t("key.marks"))];
  out.push(row(keyGlyph("light"), t("key.light"), t("key.light_text")));
  out.push(row(keyGlyph("person", [COL.person[0], 0, 1]), t("key.person"), t("key.person_text")));
  out.push(row(keyGlyph("event", [COL.event, 1, 0]), t("kind.plural.event") + ".", t("key.event_text")));
  out.push(row(keyGlyph("place", [COL.place, 2, 0]), t("kind.plural.place") + ".", t("key.place_text")));
  out.push(row(keyGlyph("story", [COL.story, 3, 0]), t("kind.plural.story") + ".", t("key.story_text")));
  out.push(row(keyGlyph("group", [COL.group, 4, 0]), t("kind.plural.group") + ".", t("key.group_text")));
  out.push(row(keyGlyph("person", [COL.dark, 5, 0]), t("key.dark"), t("key.dark_text")));
  out.push(row(keyGlyph("hollow", [COL.person[0], 0, 0]), t("key.hollow"), t("key.hollow_text")));
  out.push(row(keyGlyph("absent"), t("key.absent"), t("key.absent_text")));
  out.push(row(keyGlyph("cluster"), t("key.cluster"), t("key.cluster_text")));
  out.push(row(keyGlyph("test"), t("key.test"), t("key.test_text")));
  out.push(title(t("key.brightness")));
  ["sahabi", "tabii", "tabi_al_tabiin"].forEach((g, k) => out.push(row(keyGlyph("person", [COL.person[k], 0, 1]), t("gen." + g), "")));
  out.push(row(keyGlyph("person", [COL.person[3], 0, 0]), t("gen.none"), t("key.gen_note")));
  out.push(h("p", { class: "muted small" }, t("key.chain_light", { n: fmt(CHAIN_D.filter((x) => x > 0).length) })));
  out.push(title(t("key.lines")));
  for (const cls of CLASS_ORDER) out.push(h("div", { class: "key-row" }, h("span", { class: "sw", style: `display:block;height:2px;margin-top:12px;background:rgb(${LINE[cls].map((x) => Math.round(x * 255)).join(",")})` }), h("p", null, t("class." + cls))));
  out.push(h("p", { class: "muted small" }, t("key.trail")));
  out.push(title(t("key.positions")));
  for (const v of VIEWS) out.push(h("p", null, h("b", null, t("view." + v)), " · ", t("caption." + v)));
  out.push(h("p", { class: "muted small" }, t("key.motion")));
  out.push(title(t("key.data")));
  out.push(h("p", null, t("key.data_text", { nodes: fmt(c.nodes), claims: fmt(c.assertions), records: fmt(c.records), text: fmt(c.in_text), dated: fmt(c.dated_events), events: fmt(c.events), located: fmt(c.located), places: fmt(c.places) })));
  out.push(h("p", null, t("key.data_more", { tabaqa: fmt(c.tabaqa), chains: fmt(c.chains), links: fmt(c.chain_links), dupes: fmt(DUPES.stats.groups), dupe_entries: fmt(DUPES.stats.entries) })));
  out.push(h("p", { class: "note warn" }, t("key.status_text", { reviewed: fmt(c.reviewed) })));
  out.push(h("p", { class: "note" }, t("key.duplicates")));
  out.push(h("p", { class: "muted small" }, t("key.never")));
  out.push(title(t("key.sources")));
  out.push(h("ul", { class: "plain claims" }, META.sources.map((s) => h("li", null, s.label, " ", s.ai ? h("span", { class: "tag ai" }, t("source.ai_short")) : h("span", { class: "tag" }, t("source.person"))))));
  out.push(title(t("key.lists")));
  for (const L of META.lists) out.push(h("div", { class: "note" }, h("p", null, h("b", null, t("list." + L.key)), " · ", t("list.proposed")), h("p", { class: "cite" }, L.src)));
  if (!META.reader) out.push(h("p", { class: "muted small" }, t("key.reader_none")));
  out.push(title(t("key.rules")));
  for (const r of ["provenance", "depiction", "ai", "rank", "outlive"]) out.push(h("p", null, t("rule." + r)));
  out.push(title(t("key.licence")));
  out.push(h("p", { class: "muted" }, t("key.licence_text")));
  return out;
}
