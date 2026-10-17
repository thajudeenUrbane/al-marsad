/* Sky Atlas, part 5 of 8 — guided tours, vantage points, why each stop was chosen,
   recall, reading aloud, and quests. A tour's order always comes from the record. */
let TOURS = [];
function buildTours() {
  const ecl = META.ecliptic.map(([i]) => i);
  const dated = [];
  for (let i = 0; i < n; i++) if (KIND[i] === "event" && nf("d", i) && nf("d", i)[0][0] !== null) dated.push(i);
  dated.sort((a, b) => nf("d", a)[0][0] - nf("d", b)[0][0] || nf("d", a)[0][1] - nf("d", b)[0][1] || (ND.n[a] < ND.n[b] ? -1 : 1));
  const stories = [];
  for (let i = 0; i < n; i++) if (KIND[i] === "story") stories.push(i);
  stories.sort((a, b) => (nf("no", a) || 0) - (nf("no", b) || 0));
  const opp = [];
  for (let i = 0; i < n; i++) if (isOpp(i)) opp.push(i);
  TOURS = [
    { key: "ecliptic", stops: ecl, kind: "events" },
    { key: "dated", stops: dated, kind: "events" },
    ...META.journeys.map((j) => {
      const keep = j.steps.map((i, k) => [i, (j.why || [])[k] || []]).filter(([i]) => !isBack(i));
      return { key: "j_" + j.key, stops: keep.map((x) => x[0]), why: keep.map((x) => x[1]), kind: j.type, journey: j };
    }),
    { key: "ten", stops: META.lists.find((l) => l.key === "ten").m.slice(), kind: "people" },
    { key: "stories", stops: stories, kind: "stories" },
    { key: "opposition", stops: byText(opp), kind: "people" },
  ].filter((x) => x.stops.length);
}
function myTour() {
  const stops = STARS.map(byId).filter((i) => i >= 0);
  return stops.length ? { key: "mine", stops, kind: "mixed" } : null;
}
function tourTitle(T) {
  if (T.dynamic) return t("tour.dyn." + T.dynamic, { name: nameOf(T.of) });
  if (T.journey) return LANG === "ar" ? t("tour." + T.key + ".title") : T.journey.title;
  return t("tour." + T.key + ".title");
}
function tourLead(T) {
  if (T.dynamic) return t("tour.dyn." + T.dynamic + ".lead", { name: nameOf(T.of) });
  if (T.journey) return LANG === "ar" ? t("tour." + T.key + ".lead") : T.journey.lead;
  return t("tour." + T.key + ".lead");
}
function dynamicTour(i) {
  const k = KIND[i];
  if (k === "person") {
    const stops = [i, ...eventsOf(i)];
    const fam = kin(i);
    for (const key of ["parents", "spouses", "children"]) for (const [x] of fam[key]) if (!isBack(x) || key !== "parents") stops.push(x);
    return { key: "life", dynamic: "life", of: i, stops: [...new Set(stops)].slice(0, 60), kind: "mixed" };
  }
  if (k === "place") return { key: "place", dynamic: "place", of: i, stops: [i, ...byText(othersBy(i).filter((j) => KIND[j] === "event")), ...sortPeople(othersBy(i).filter((j) => KIND[j] === "person")).slice(0, 30)], kind: "mixed" };
  return { key: "around", dynamic: "around", of: i, stops: [i, ...sortPeople(othersBy(i).filter((j) => (KIND[j] === "person" || k !== "event") && !isBack(j))).slice(0, 40)], kind: "mixed" };
}
let playTimer = 0;
function startTour(T, k) {
  if (!T || !T.stops.length) { toast(t("tour.empty")); return; }
  pushHistory();
  stopPlay();
  S.guide = { T, k: Math.max(0, Math.min(k || 0, T.stops.length - 1)) };
  S.preset = null; S.lineClasses = null;
  closeDrawer();
  $("guide").hidden = false; $("guide").classList.remove("folded"); $("guide-min").setAttribute("aria-expanded", "true"); $("guide-min").textContent = t("guide.fold");
  $("app").classList.add("has-guide");
  $("welcome").hidden = true;
  closeRecord();
  insets();
  goStop(S.guide.k);
}
function endTour() {
  stopPlay();
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  S.guide = null; S.markers = [];
  $("guide").hidden = true; $("app").classList.remove("has-guide");
  clearFocus();
  insets();
}
function goStop(k) {
  const G = S.guide; if (!G) return;
  G.k = Math.max(0, Math.min(k, G.T.stops.length - 1));
  const i = G.T.stops[G.k];
  if (S.view === "lineage" || (S.visible && !S.visible[i])) setView("sky", { camera: false, record: false });
  S.focus = i;
  if (i !== LIGHT) markSeen(i);
  const set = new Set([i, ...neighbours(i)]);
  for (const j of G.T.stops.slice(Math.max(0, G.k - 1), G.k + 2)) set.add(j);
  S.markers = [];
  const prev = G.T.stops[G.k - 1], next = G.T.stops[G.k + 1];
  if (prev !== undefined) S.markers.push({ i: prev, label: fmt(G.k) });
  S.markers.push({ i, label: fmt(G.k + 1), now: true });
  if (next !== undefined) S.markers.push({ i: next, label: fmt(G.k + 2) });
  emphasise(set);
  if (i !== LIGHT) R.flyToNode(i, spread(i, set), reduced ? 0 : 1300);
  const tk = G.T.key + (G.T.of !== undefined ? ":" + ND.id[G.T.of] : "");
  LOG.tours[tk] = Math.max(LOG.tours[tk] || 0, G.k + 1);
  if (G.k === G.T.stops.length - 1) LOG.done["tour:" + G.T.key] = 1;
  saveLog(); checkMilestones(); checkQuests();
  renderStop();
  here(); refreshText();
  announce(t("announce.stop", { k: fmt(G.k + 1), n: fmt(G.T.stops.length), name: nameOf(i) }));
  if (S.speak) speak(spokenStop(i));
}
function whyStop(T, k, i) { // why this stop is in the tour, from the tour's own rule or record
  const name = (j) => (j >= 0 ? nameOf(j) : "—");
  if (T.why) {
    const rs = T.why[k] || [];
    if (!rs.length) return t("why.rule");
    return rs.map(([kind, o, w]) => {
      if (kind === "named") return t("why.named", { word: w });
      if (kind === "record") return t("why.record", { other: name(o), pred: w });
      if (kind === "part") return t("why.part_doc", { word: w });
      if (kind === "part_of") return t("why.part_of", { other: name(o) });
      if (kind === "has_part") return t("why.has_part", { other: name(o) });
      if (kind === "event_claim") return t("why.event_claim", { other: name(o), pred: w });
      return t("why.date", { other: name(o) });
    }).join(" ");
  }
  if (T.key === "ecliptic") { const mt = nf("mt", i); return mt !== undefined && msCite.get(mt) ? t("why.ecliptic", { where: msCite.get(mt) }) : t("why.ecliptic_date"); }
  if (T.key === "dated") return t("why.dated", { date: nf("d", i)[0][2] });
  if (T.key === "ten") return t("why.ten");
  if (T.key === "stories") return t("why.story", { n: fmt(nf("no", i) || 0) });
  if (T.key === "opposition") return t("why.opposition");
  if (T.key === "mine") return t("why.mine");
  if (T.dynamic === "life") return i === T.of ? t("why.life_self") : KIND[i] === "event" ? t("why.life_event", { name: nameOf(T.of) }) : t("why.life_kin", { name: nameOf(T.of) });
  if (T.dynamic === "place") return i === T.of ? t("why.place_self") : t("why.place", { name: nameOf(T.of) });
  if (T.dynamic === "around") {
    if (i === T.of) return t("why.place_self");
    const c = [...claimsOf(i)].find((x) => other(x, i) === T.of);
    return c !== undefined ? t("why.around", { name: nameOf(T.of), pred: predText(c) }) : "";
  }
  return "";
}
function renderStop() {
  const G = S.guide; if (!G) return;
  const T = G.T, i = T.stops[G.k], k = KIND[i];
  $("guide-tour").textContent = tourTitle(T);
  $("guide-progress").textContent = t("guide.progress", { k: fmt(G.k + 1), n: fmt(T.stops.length) });
  $("guide-meter").style.width = ((G.k + 1) / T.stops.length * 100).toFixed(1) + "%";
  $("guide-prev").disabled = G.k === 0;
  $("guide-next").disabled = G.k === T.stops.length - 1;
  const left = h("div", null);
  left.append(h("p", { class: "kind" }, glyph(i), i === LIGHT ? t("light.kind") : kindText(i)));
  left.append(h("h2", { class: "stop-name" }, nameOf(i)));
  const alt = i === LIGHT ? null : altNames(i);
  if (alt && alt.ar) left.append(h("p", { class: "alt" }, h("span", { class: "ar", lang: "ar", dir: "rtl" }, alt.ar)));
  if (G.k === 0) left.append(h("p", { class: "muted" }, tourLead(T)));
  const why = whyStop(T, G.k, i);
  if (why) left.append(h("p", { class: "why" }, h("b", null, t("why.title")), " ", why));
  const facts = h("ul", { class: "plain claims" });
  if (k === "event") {
    const d = nf("d", i); if (d) facts.append(h("li", null, h("b", null, t("stop.when")), " ", d[0][2]));
    const pl = placesOf(i); if (pl.length) facts.append(h("li", null, h("b", null, t("stop.where")), " ", ...pl.slice(0, 3).flatMap((p, q) => [q ? ", " : "", nameBtn(p)])));
    const g = peopleAt(i);
    const counts = ["led", "part", "died", "absent"].filter((x) => g[x].size).map((x) => t("who." + x, { n: fmt(g[x].size) }));
    if (counts.length) facts.append(h("li", null, counts.join(" · ")));
    [...claimsOf(i)].filter((c) => pk(c) === "led").slice(0, S.depth === "discover" ? 2 : 4).forEach((c) => facts.append(claimRow(c, i)));
  } else {
    const cs = [...claimsOf(i)].filter((c) => pclass(c) !== "kinship" || S.depth !== "discover");
    cs.sort((a, b) => CLASS_ORDER.indexOf(pclass(a)) - CLASS_ORDER.indexOf(pclass(b)) || (cf("ms", a) ?? 1e9) - (cf("ms", b) ?? 1e9));
    cs.slice(0, S.depth === "discover" ? 3 : 6).forEach((c) => facts.append(claimRow(c, i)));
    if (k === "story" && nf("no", i)) facts.prepend(h("li", null, t("story.no", { n: fmt(nf("no", i)) }), nf("partl", i) ? " · " + nf("partl", i) : ""));
  }
  const fm = firstMention(i);
  if (fm) facts.append(h("li", { class: "cite" }, fm));
  if (facts.childNodes.length) left.append(h("section", { class: "facet" }, h("h3", null, t("stop.record")), facts));
  if (S.depth !== "discover") left.append(recall(i));

  const right = h("div", null);
  let people = [];
  if (k === "event") { const g = peopleAt(i); people = sortPeople([...g.led, ...g.part, ...g.died, ...g.other]); }
  else people = sortPeople([...neighbours(i)].filter((j) => KIND[j] === "person" && !isBack(j)));
  if (people.length) right.append(h("section", { class: "facet", style: "margin-top:0;border-top:0;padding-top:0" }, h("h3", null, k === "event" ? t("stop.who") : t("stop.people")), chips(people, S.depth === "discover" ? 10 : 18)));
  if (k === "event") { const abs = sortPeople([...peopleAt(i).absent]); if (abs.length) right.append(h("p", { class: "muted small" }, t("who.absent", { n: fmt(abs.length) })), chips(abs, 8)); }
  right.append(h("section", { class: "facet" }, h("h3", null, t("stop.next")), directions(i)));
  if (T.journey && T.journey.status !== "approved") right.append(h("p", { class: "note" }, t("tour.draft")));
  if (T.key === "opposition") right.append(h("p", { class: "note warn" }, t("tour.opposition.note")));
  if (T.key === "ten") right.append(h("p", { class: "note" }, t("list.proposed")));
  $("guide-body").replaceChildren(h("div", { class: "stop-grid" }, left, right));
  $("guide-body").scrollTop = 0;
  insets();
}
function directions(i) {
  const box = h("div", { class: "dirs" });
  const dir = (label, name, fn) => box.append(h("button", { type: "button", class: "dir", onclick: fn }, h("small", null, label), h("span", null, name)));
  const k = KIND[i];
  if (k === "event") {
    const ecl = META.ecliptic.map(([x]) => x), at = ecl.indexOf(i);
    if (at > 0) dir(t("dir.before"), nameOf(ecl[at - 1]), () => jumpTo(ecl[at - 1]));
    if (at >= 0 && at < ecl.length - 1) dir(t("dir.after"), nameOf(ecl[at + 1]), () => jumpTo(ecl[at + 1]));
    for (const [e, cnt] of sharedEvents(i).slice(0, 2)) dir(t("dir.shared", { n: fmt(cnt) }), nameOf(e), () => jumpTo(e));
    const pl = placesOf(i)[0];
    if (pl !== undefined) dir(t("dir.stand"), nameOf(pl), () => startTour(dynamicTour(pl)));
    const g = peopleAt(i), lead = sortPeople([...g.led, ...g.part])[0];
    if (lead !== undefined && lead !== LIGHT) dir(t("dir.life"), nameOf(lead), () => startTour(dynamicTour(lead)));
  } else if (k === "person") {
    if (i !== LIGHT) dir(t("dir.life"), nameOf(i), () => startTour(dynamicTour(i)));
    if (kin(i).parents.length || kin(i).children.length) dir(t("dir.lineage"), nameOf(i), () => setView("lineage", { of: i }));
    const ev = eventsOf(i)[0];
    if (ev !== undefined) dir(t("dir.around"), nameOf(ev), () => startTour(dynamicTour(ev)));
  } else if (k === "place") {
    const ev = byText(othersBy(i).filter((j) => KIND[j] === "event"))[0];
    if (ev !== undefined) dir(t("dir.around"), nameOf(ev), () => startTour(dynamicTour(ev)));
    if (nf("geo", i)) dir(t("dir.globe"), nameOf(i), () => { setView("globe"); focus(i, { record: false }); });
  } else {
    const p = sortPeople(othersBy(i).filter((j) => KIND[j] === "person"))[0];
    if (p !== undefined && p !== LIGHT) dir(t("dir.life"), nameOf(p), () => startTour(dynamicTour(p)));
  }
  dir(t("dir.record"), nameOf(i), () => openRecord(i));
  return box;
}
function jumpTo(i) { // inside the current tour if it is a stop, otherwise a tour around it
  const G = S.guide;
  if (G) { const at = G.T.stops.indexOf(i); if (at >= 0) { goStop(at); return; } }
  startTour(dynamicTour(i));
}
function sharedEvents(ev) { // other events with people recorded at both: a count of shared records
  const people = othersBy(ev).filter((j) => KIND[j] === "person" && j !== LIGHT);
  const cnt = new Map();
  for (const p of people) for (const e of othersBy(p)) if (KIND[e] === "event" && e !== ev) cnt.set(e, (cnt.get(e) || 0) + 1);
  return [...cnt.entries()].filter(([, c]) => c >= 2).sort((a, b) => b[1] - a[1] || (ND.n[a[0]] < ND.n[b[0]] ? -1 : 1));
}
function recall(i) { // a question about the stop, answered from the record; nothing is marked wrong
  const k = KIND[i];
  let q = null, ans = null;
  if (k === "event") {
    const led = othersBy(i, ["led"]).filter((j) => KIND[j] === "person");
    const pl = placesOf(i), d = nf("d", i);
    if (led.length) { q = t("recall.led", { name: nameOf(i) }); ans = () => chips(sortPeople(led)); }
    else if (pl.length) { q = t("recall.where", { name: nameOf(i) }); ans = () => chips(pl); }
    else if (d) { q = t("recall.when", { name: nameOf(i) }); ans = () => h("p", null, d[0][2]); }
  } else if (k === "person" && i !== LIGHT) {
    const ev = eventsOf(i), par = kin(i).parents.map((x) => x[0]);
    if (ev.length) { q = t("recall.events", { name: nameOf(i) }); ans = () => chips(ev, 12); }
    else if (par.length) { q = t("recall.parents", { name: nameOf(i) }); ans = () => chips(par); }
  }
  if (!q) return h("span");
  const box = h("div", { class: "recall" }, h("p", null, h("b", null, t("recall.title")), " ", q));
  const btn = h("button", { type: "button", class: "chip small", onclick: () => {
    btn.replaceWith(ans(), h("p", { class: "muted", style: "margin-top:6px" }, t("recall.note")),
      h("button", { type: "button", class: "chip small", onclick: (e) => { LOG.recalls++; saveLog(); checkMilestones(); e.target.disabled = true; e.target.textContent = t("recall.kept"); } }, t("recall.remembered")));
  } }, t("recall.reveal"));
  box.append(btn);
  return box;
}
function stopPlay() { clearInterval(playTimer); playTimer = 0; $("guide-play").setAttribute("aria-pressed", "false"); $("guide-play").textContent = t("guide.play"); }
function togglePlay(force) {
  if (playTimer && force !== true) { stopPlay(); return; }
  stopPlay();
  $("guide-play").setAttribute("aria-pressed", "true"); $("guide-play").textContent = t("guide.pause");
  const every = S.classroom ? 11000 : S.depth === "discover" ? 6500 : 9000;
  playTimer = setInterval(() => {
    const G = S.guide;
    if (!G || G.k >= G.T.stops.length - 1) { stopPlay(); return; }
    if (S.speak && window.speechSynthesis && window.speechSynthesis.speaking) return; // let the guide finish the sentence
    goStop(G.k + 1);
  }, every);
}

// ------------------------------------------------------------------ vantage points
function applyPreset(key) {
  const p = META.presets.find((x) => x.key === key);
  if (!p) return;
  pushHistory();
  if (S.guide) endTour();
  S.preset = key;
  S.lineClasses = p.cls || null;
  if (S.view !== p.view) setView(p.view, { camera: false, record: false });
  const hl = new Set(p.hl);
  if (p.focus !== null && p.focus !== undefined) {
    S.focus = p.focus;
    emphasise(hl);
    R.flyToNode(p.focus, spread(p.focus, hl));
    openRecord(p.focus);
  } else {
    S.focus = -1;
    emphasise(hl);
    R.flyTo(viewCamera(p.view), 900);
    closeRecord();
  }
  if (key === "chain") D.chains.forEach((_, c) => { LOG.chainSet[c] = 1; });
  saveLog(); checkQuests();
  here(); refreshText();
  announce(t("preset.announce", { name: t("preset." + key) }));
}

// ------------------------------------------------------------------ reading aloud
let VOICES = [];
function loadVoices() { try { VOICES = window.speechSynthesis ? window.speechSynthesis.getVoices() : []; } catch (e) { VOICES = []; } }
function speak(text) {
  if (!("speechSynthesis" in window)) { toast(t("speak.none")); return; }
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = LANG === "ar" ? "ar" : "en-GB";
    const v = VOICES.find((x) => x.lang && x.lang.toLowerCase().startsWith(LANG));
    if (v) u.voice = v;
    u.rate = S.classroom ? 0.92 : 1;
    window.speechSynthesis.speak(u);
    LOG.spoken++; saveLog();
  } catch (e) { toast(t("speak.none")); }
}
function spokenStop(i) {
  const parts = [nameOf(i) + "."];
  const d = nf("d", i); if (d) parts.push(t("stop.when") + " " + d[0][2] + ".");
  const pl = placesOf(i); if (pl.length) parts.push(t("stop.where") + " " + pl.slice(0, 2).map(nameOf).join(", ") + ".");
  const cs = [...claimsOf(i)].filter((c) => pclass(c) !== "kinship").slice(0, 3);
  for (const c of cs) parts.push(sentence(c) + ".");
  parts.push(t("speak.status"));
  return parts.join(" ");
}
function spokenRecord(i) {
  const cs = groupClaims(i).slice(0, 4).map(([, c]) => sentence(c[0]) + ".");
  return [nameOf(i) + ".", kindText(i) + ".", t("records.count", { n: deg[i] }) + ".", ...cs, t("speak.status")].join(" ");
}

// ------------------------------------------------------------------ quests: the learner's own exploring, never a person's rank
let QUESTS = [];
function buildQuests() {
  const badr = META.presets.find((p) => p.key === "badr");
  const badrPeople = badr ? badr.hl.filter((i) => KIND[i] === "person" && i !== LIGHT) : [];
  const located = []; for (let i = 0; i < n; i++) if (KIND[i] === "place" && nf("geo", i)) located.push(i);
  const dated = (TOURS.find((x) => x.key === "dated") || { stops: [] }).stops;
  const hij = TOURS.find((x) => x.key === "j_hijrah-step-by-step");
  const seenOf = (arr, book) => arr.filter((i) => book[ND.id[i]]).length;
  QUESTS = [
    { key: "four", goal: 4, val: () => seenOf(META.lists.find((l) => l.key === "rashidun").m, LOG.seen), go: () => startTour({ key: "ten", stops: META.lists.find((l) => l.key === "rashidun").m, kind: "people" }) },
    { key: "ten", goal: 10, val: () => seenOf(META.lists.find((l) => l.key === "ten").m, LOG.seen), go: () => startTour(TOURS.find((x) => x.key === "ten")) },
    { key: "badr", goal: Math.min(25, badrPeople.length) || 1, val: () => seenOf(badrPeople, LOG.seen), go: () => applyPreset("badr") },
    { key: "hijrah", goal: hij ? hij.stops.length : 1, val: () => (hij ? LOG.tours[hij.key] || 0 : 0), go: () => hij && startTour(hij) },
    { key: "views", goal: VIEWS.length, val: () => VIEWS.filter((v) => LOG.views[v]).length, go: () => { const v = VIEWS.find((x) => !LOG.views[x] && x !== "lineage"); if (v) setView(v); else toast(t("lineage.need")); } },
    { key: "evidence", goal: 10, val: () => LOG.ladders, go: () => setDepth("study") },
    { key: "chains", goal: D.chains.length || 1, val: () => Object.keys(LOG.chainSet).length, go: () => applyPreset("chain") },
    { key: "places", goal: located.length || 1, val: () => seenOf(located, LOG.places), go: () => setView("globe") },
    { key: "dated", goal: dated.length || 1, val: () => seenOf(dated, LOG.events), go: () => startTour(TOURS.find((x) => x.key === "dated")) },
  ];
}
function checkQuests() {
  for (const q of QUESTS) if (!LOG.done["quest:" + q.key] && q.val() >= q.goal) {
    LOG.done["quest:" + q.key] = new Date().toISOString().slice(0, 10);
    saveLog();
    toast(t("quest.done", { name: t("quest." + q.key) }));
  }
}
