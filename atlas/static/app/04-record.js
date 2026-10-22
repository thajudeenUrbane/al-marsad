/* Sky Atlas, part 4 of 10 — focus and the Record card: every record with its source and
   status, the evidence ladder for an item and for a line, who was there and who was not,
   entries with the same written name, comparing two records, and copying a citation. */
function focus(i, opts) {
  opts = opts || {};
  if (opts.record !== false && S.focus !== i) pushHistory();
  S.focus = i; S.preset = null; S.lineClasses = null; // opening a record leaves any vantage point
  if (i !== LIGHT) markSeen(i);
  const set = new Set([i, ...neighbours(i)]);
  if (S.compare >= 0 && S.compare !== i) set.add(S.compare);
  emphasise(set);
  if (opts.fly !== false && i !== LIGHT && S.visible && S.visible[i]) R.flyToNode(i, spread(i, set));
  openRecord(i);
  here(); refreshText();
  announce(t("announce.focus", { name: nameOf(i) }));
  if (S.speak && !S.guide) speak(spokenRecord(i));
}
function spread(i, set) { // how far to stand back to see an item with everything it touches
  const p = R.targetPos(i);
  const ds = [];
  for (const j of set) {
    if (j === LIGHT || !visibleNow(j)) continue;
    const q = R.targetPos(j);
    ds.push(Math.hypot(q[0] - p[0], q[1] - p[1], q[2] - p[2]));
  }
  ds.sort((a, b) => a - b);
  const r = ds.length ? ds[Math.floor(ds.length * 0.85)] : 60;
  return Math.max(240, Math.min(3800, r * 2.8 + 120));
}
function clearFocus() {
  S.focus = -1; S.trace.path = null; S.preset = null; S.lineClasses = null;
  emphasise(null);
  closeRecord();
  here(); refreshText();
}
function openRecord(i) {
  $("record").hidden = false;
  $("app").classList.add("has-record");
  renderRecord(i);
  $("record-body").scrollTop = 0;
  insets();
}
function closeRecord() { $("record").hidden = true; $("app").classList.remove("has-record"); insets(); }
function showPanel(nodes) { // the Record card with other content (a trace, a pair, a comparison)
  $("record").hidden = false; $("app").classList.add("has-record");
  $("record-body").replaceChildren(...nodes);
  $("record-body").scrollTop = 0;
  insets();
}

function nameBtn(i, self) {
  if (i === self) return h("b", { class: i === LIGHT ? "link light" : "" }, nameOf(i));
  return h("button", { type: "button", class: "link" + (i === LIGHT ? " light" : ""), onclick: () => focus(i) }, nameOf(i));
}
function chip(i) {
  return h("button", { type: "button", class: "person-chip" + (isOpp(i) && !isTurned(i) ? " dark" : ""), onclick: () => focus(i), title: kindText(i) }, glyph(i), nameOf(i));
}
function chips(list, limit) {
  const box = h("div", { class: "people" });
  const lim = limit || 24;
  const draw = (k) => { box.replaceChildren(...list.slice(0, k).map(chip)); if (list.length > k) box.append(h("button", { type: "button", class: "chip small", onclick: () => draw(list.length) }, t("more.all", { n: fmt(list.length) }))); };
  draw(lim);
  return box;
}
function sourceTag(c) {
  const s = CL.src[c];
  if (s < 0) return null;
  const src = META.sources[s];
  return h("span", { class: "tag" + (src.ai ? " ai" : ""), title: src.label }, src.ai ? t("source.ai", { label: src.label }) : src.label);
}
function statusTag(c) {
  const st = CL.st[c];
  return h("span", { class: "tag prop" }, st === 1 ? t("status.proposed") : st === 0 ? t("status.record") : t("status.other"));
}
function claimRow(c, self) {
  const row = h("li", null, h("span", { class: "sent" }, nameBtn(CL.s[c], self), " ", h("span", { class: "pred" }, predText(c)), " ", nameBtn(CL.o[c], self)));
  if (S.depth === "discover") return row;
  const meta = h("div", { class: "meta" }, statusTag(c), sourceTag(c));
  const role = cf("r", c); if (role) meta.append(h("span", null, t("claim.role", { role })));
  for (const q of cf("q", c) || []) { const key = "qual." + META.quals[q].replace(/\W+/g, "_"); meta.append(h("span", { class: "tag" }, STR[key] || EN[key] || META.quals[q])); }
  const sty = cf("sty", c); if (sty !== undefined) meta.append(h("span", null, t("claim.story"), " ", nameBtn(sty)));
  const mode = cf("mode", c); if (mode) meta.append(h("span", null, t("ladder.mode", { mode })));
  row.append(meta);
  const cit = citation(c, S.depth === "research");
  if (cit) row.append(h("div", { class: "cite" }, cit));
  const b = cf("b", c); if (b !== undefined) row.append(h("div", { class: "cite" }, t("claim.basis", { text: META.strings[b] })));
  if (S.depth === "research") {
    const g = cf("g", c); if (g) row.append(h("div", { class: "gloss" }, t("claim.gloss"), " ", g));
    const id = cf("id", c); if (id) row.append(h("div", { class: "cite" }, t("claim.id", { id })));
  }
  const rep = cf("rep", c), ch = cf("chain", c);
  if (rep !== undefined || ch !== undefined) row.append(ladder(c, rep, ch));
  else if (S.depth === "research") row.append(h("div", { class: "cite" }, cit ? t("ladder.no_report") : t("ladder.no_passage")));
  return row;
}
function ladder(c, rep, ch) {
  const d = h("details", { class: "how" }, h("summary", null, t("ladder.how")));
  if (S.depth === "research") d.open = true;
  d.addEventListener("toggle", () => { if (d.open) { LOG.ladders++; if (ch !== undefined) { LOG.chains++; LOG.chainSet[ch] = 1; } saveLog(); checkMilestones(); checkQuests(); } }, { once: true });
  const box = h("div", { class: "ladder" });
  if (rep !== undefined) {
    const r = D.reports[rep];
    box.append(h("p", null, h("b", null, t("ladder.report")), " ", r.label || "—"));
    if (r.genre || r.asc) box.append(h("p", { class: "muted" }, [r.genre && t("ladder.genre", { v: r.genre }), r.asc && t("ladder.asc", { v: r.asc })].filter(Boolean).join(" · ")));
    if (r.cit) box.append(h("p", { class: "cite" }, t("ladder.located", { v: r.cit })));
    if (r.rec !== undefined && META.sources[r.rec]) box.append(h("p", { class: "muted" }, t("ladder.recorded_by", { v: META.sources[r.rec].label }) + (r.cov ? " · " + t("coverage", { v: r.cov }) : "")));
    if (r.grades && r.grades.length) for (const g of r.grades) box.append(h("p", null, t("ladder.grade", { grade: g.grade || "—", by: g.by || "—", scheme: g.scheme || g.tradition || "—" }), g.why ? h("span", { class: "muted" }, " · " + t("ladder.why", { v: g.why })) : null));
    else box.append(h("p", { class: "muted" }, t("ladder.nograde")));
  }
  if (ch !== undefined) {
    const C = D.chains[ch];
    box.append(h("p", null, h("b", null, t("ladder.chain")), " ", C.label || ""));
    const ol = h("ol", { class: "plain path" });
    for (const [a, b, ord, mode, chk, chkb] of C.links) ol.append(h("li", null, nameBtn(a), " → ", nameBtn(b),
      mode ? h("span", { class: "muted" }, " · " + t("ladder.mode", { mode })) : null,
      chk ? h("span", { class: "muted" }, " · " + t("ladder.check", { v: chk + (chkb ? " (" + chkb + ")" : "") })) : null));
    if (C.collector !== undefined) ol.append(h("li", null, nameBtn(C.collector), h("span", { class: "muted" }, " · " + t("chains.collector"))));
    box.append(ol);
  }
  box.append(h("p", { class: "muted small" }, t("ladder.not_yet")));
  d.append(box);
  return d;
}

function groupClaims(i, list) {
  const groups = new Map();
  for (const c of list || claimsOf(i)) {
    const key = pk(c) + (CL.s[c] === i ? ">" : "<");
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(c);
  }
  const arr = [...groups.entries()];
  arr.sort((a, b) => CLASS_ORDER.indexOf(pclass(a[1][0])) - CLASS_ORDER.indexOf(pclass(b[1][0])) || b[1].length - a[1].length);
  for (const [, cs] of arr) cs.sort((a, b) => (cf("ms", a) ?? 1e9) - (cf("ms", b) ?? 1e9));
  return arr;
}
function othersBy(i, preds, dir) { // the other ends of i's claims with these predicates
  const out = new Set();
  for (const c of claimsOf(i)) {
    if (preds && !preds.includes(pk(c))) continue;
    if (dir === ">" && CL.s[c] !== i) continue;
    if (dir === "<" && CL.o[c] !== i) continue;
    out.add(other(c, i));
  }
  out.delete(i);
  return [...out];
}
function firstMention(i) {
  const ms = firstMs(i);
  if (ms === undefined) return null;
  const where = msCite.get(ms);
  return where ? t("first.mention", { where }) + (S.depth === "research" ? " · " + t("first.ms", { ms }) : "") : null;
}
const PLACE_PREDS = ["took_place_at", "occurred_at", "migrated_to", "died_at", "born_at", "resided_in", "visited", "buried_at", "travelled_via", "sheltered_at", "migrated_from"];
function placesOf(i) { return othersBy(i, PLACE_PREDS).filter((j) => KIND[j] === "place"); }
function eventsOf(i) { return byText(othersBy(i).filter((j) => KIND[j] === "event")); }
const PRESENT_PK = new Set(["participated_in", "took_part", "present_at", "witnessed"]);
function peopleAt(ev) {
  const groups = { led: new Set(), part: new Set(), died: new Set(), killed: new Set(), absent: new Set(), other: new Set() };
  for (const c of claimsOf(ev)) {
    const o = other(c, ev);
    if (KIND[o] !== "person" || o === ev) continue;
    const p = pk(c);
    if (p === "led") groups.led.add(o);
    else if (PRESENT_PK.has(p)) groups.part.add(o);
    else if (p === "died_during") groups.died.add(o);
    else if (p === "absent_from") groups.absent.add(o);
    else groups.other.add(o);
  }
  for (const k of ["part", "died", "other"]) for (const x of groups.led) groups[k].delete(x);
  for (const x of groups.died) groups.part.delete(x);
  return groups;
}
function absentFrom(i) { return [...claimsOf(i)].filter((c) => pk(c) === "absent_from" && CL.s[c] === i).map((c) => CL.o[c]); }
function contextLine(i) {
  const k = KIND[i];
  if (k === "event") { const d = nf("d", i); return d ? d[0][2] : (firstMs(i) !== undefined ? msCite.get(firstMs(i)) || "" : ""); }
  if (k === "person") {
    if (isBack(i)) return t("ctx.lineage");
    const ev = eventsOf(i); return ev.length ? nameOf(ev[0]) : "";
  }
  if (k === "story") return t("ctx.story", { n: fmt(nf("no", i) || 0) });
  if (k === "place") { const ar = nf("ar", i); return LANG === "en" && ar ? ar : ""; }
  return "";
}
const facet = (title, ...kids) => h("section", { class: "facet" }, h("h3", null, title), ...kids);

function renderRecord(i) {
  const body = $("record-body");
  const k = KIND[i];
  const out = [];
  // ← back to the record before
  const prev = [...S.history].reverse().find((s) => s.focus >= 0 && s.focus !== i);
  if (prev) out.push(h("button", { type: "button", class: "chip small back-to", onclick: () => back() }, t("panel.back_to", { name: nameOf(prev.focus) })));
  const alt = i === LIGHT ? { names: [], ar: null, other: [] } : altNames(i);
  out.push(h("p", { class: "kind" }, glyph(i), i === LIGHT ? t("light.kind") : kindText(i)));
  out.push(h("h2", { class: "name" }, nameOf(i)));
  if (alt.names.length || alt.ar) out.push(h("p", { class: "alt" }, alt.names.join(" · "), alt.ar ? h("span", { class: "ar", lang: "ar", dir: "rtl" }, (alt.names.length ? " · " : "") + alt.ar) : null));
  if (alt.other.length && S.depth !== "discover") out.push(h("p", { class: "alt" }, t("panel.other_names", { list: alt.other.join(" · ") })));
  // marks the sky draws, and why
  const tags = h("p", { class: "status-line" });
  if (i === LIGHT) tags.append(h("span", { class: "tag list" }, t("light.tag")));
  if (LIST.rashidun.has(i)) tags.append(h("span", { class: "tag list", title: t("list.proposed") }, t("list.rashidun")));
  if (LIST.ten.has(i)) tags.append(h("span", { class: "tag list", title: t("list.proposed") }, t("list.ten")));
  const tb = nf("tb", i);
  if (tb !== undefined) tags.append(h("span", { class: "tag" }, t("gen." + META.tb[tb])));
  if (CHAIN_D[i]) tags.append(h("span", { class: "tag" }, t("chain.place", { n: fmt(CHAIN_D[i]) })));
  if (isOpp(i)) tags.append(h("span", { class: "tag dark" }, isTurned(i) ? t("mark.turned") : t("mark.opponent")));
  if (isBack(i)) tags.append(h("span", { class: "tag" }, t("mark.background")));
  tags.append(h("span", { class: "tag" }, t("records.count", { n: fmt(deg[i]) })));
  if (STARS.includes(ND.id[i])) tags.append(h("span", { class: "tag list" }, t("star.saved")));
  out.push(tags);
  const fm = firstMention(i);
  if (fm) out.push(h("p", { class: "cite" }, fm));

  // what you can do from here
  const acts = h("div", { class: "row actions" });
  const act = (label, fn, o) => acts.append(h("button", Object.assign({ type: "button", class: "chip small", onclick: fn }, o || {}), label));
  if (i !== LIGHT) acts.append(h("button", { type: "button", class: "chip primary small", onclick: () => startTour(dynamicTour(i)) }, t("act.guide")));
  if (k === "person" && (kin(i).parents.length || kin(i).children.length)) act(t("act.lineage"), () => setView("lineage", { of: i }));
  if (S.trace.from >= 0 && S.trace.from !== i) act(t("act.trace_to", { name: nameOf(S.trace.from) }), () => trace(S.trace.from, i));
  act(t("act.trace_from"), () => { S.trace.from = i; toast(t("trace.start_set", { name: nameOf(i) })); renderRecord(i); }, { "aria-pressed": String(S.trace.from === i) });
  if (S.compare >= 0 && S.compare !== i) act(t("act.compare_with", { name: nameOf(S.compare) }), () => compare(S.compare, i));
  act(t("act.compare"), () => { S.compare = i; toast(t("compare.set", { name: nameOf(i) })); buildLabels(); R.requestDraw(); renderRecord(i); }, { "aria-pressed": String(S.compare === i) });
  if (i !== LIGHT) act(STARS.includes(ND.id[i]) ? t("star.remove") : t("star.add"), () => { toggleStar(i); renderRecord(i); }, { "aria-pressed": String(STARS.includes(ND.id[i])) });
  act(t("act.copy"), () => copyText(citeRecord(i)));
  act(t("speak.record"), () => speak(spokenRecord(i)));
  if (META.reader && ND.u) acts.append(h("a", { class: "chip small", href: META.reader + ND.u[i], target: "_blank", rel: "noopener" }, t("act.reader")));
  out.push(acts);

  if (i === LIGHT) out.push(h("p", { class: "note" }, t("light.note")));
  if (isOpp(i)) out.push(oppNote(i));
  if (k === "person") {
    const abs = absentFrom(i);
    if (abs.length) out.push(h("p", { class: "note" }, t("presence.person"), " ", ...abs.flatMap((e, q) => [q ? ", " : "", nameBtn(e)])));
  }

  // facets by kind
  if (k === "event") {
    const d = nf("d", i);
    if (d) out.push(facet(t("facet.when"), ...d.map((x) => h("p", null, x[2], x[3] && x[3].length && S.depth !== "discover" ? h("span", { class: "muted" }, " · " + x[3].join(" · ")) : null))));
    const pl = placesOf(i);
    if (pl.length) out.push(facet(t("facet.where"), chips(pl)));
    out.push(presenceFacet(i));
    const disp = nf("disp", i);
    if (disp) out.push(facet(t("facet.disputes"), ...disp.map((x) => h("div", { class: "note" }, h("p", null, x.q || ""), h("ul", null, (x.pos || []).map((p) => h("li", null, p)))))));
    const ev = byText(othersBy(i).filter((j) => KIND[j] === "event"));
    if (ev.length) out.push(facet(t("facet.events_linked"), chips(ev)));
  } else if (k === "person") {
    const ev = eventsOf(i);
    if (ev.length) out.push(facet(t("facet.events"), h("p", { class: "muted" }, t("facet.events_note")), chips(ev, S.depth === "discover" ? 14 : 40)));
    const K = kin(i), fam = [];
    for (const key of ["parents", "children", "spouses", "siblings"]) {
      if (!K[key].length) continue;
      fam.push(h("p", { class: "muted" }, t("kin." + key, { n: fmt(K[key].length) })), chips(sortPeople(K[key].map((x) => x[0]), "e3"), 16));
    }
    if (fam.length) out.push(facet(t("facet.family"), ...fam));
    const pl = placesOf(i);
    if (pl.length) out.push(facet(t("facet.places"), chips(pl)));
    const tr = othersBy(i, ["narrated_from", "transmitted_to"]);
    if (tr.length) out.push(facet(t("facet.transmission"), chips(sortPeople(tr), 16)));
    const st = othersBy(i).filter((j) => KIND[j] === "story");
    if (st.length) out.push(facet(t("facet.stories"), h("p", { class: "muted" }, t("facet.stories_note")), chips(st.sort((a, b) => (nf("no", a) || 0) - (nf("no", b) || 0)))));
    const death = nf("death", i);
    if (death) out.push(facet(t("facet.death"), ...death.map((x) => h("p", null, x[2]))));
  } else if (k === "place") {
    const g = nf("geo", i);
    out.push(facet(t("facet.location"), h("p", null, g ? t("place.located", { lon: g[0], lat: g[1], conf: g[2] || "" }) : t("place.unlocated"))));
    const ev = byText(othersBy(i).filter((j) => KIND[j] === "event"));
    if (ev.length) out.push(facet(t("facet.events_here"), chips(ev)));
    const pp = sortPeople(othersBy(i).filter((j) => KIND[j] === "person"));
    if (pp.length) out.push(facet(t("facet.people_here"), chips(pp, 20)));
  } else if (k === "story") {
    const parts = [];
    if (nf("no", i)) parts.push(t("story.no", { n: fmt(nf("no", i)) }));
    if (nf("partl", i)) parts.push(nf("partl", i));
    out.push(facet(t("facet.story"), h("p", null, parts.join(" · ")), nf("work", i) !== undefined ? h("p", { class: "cite" }, META.sources[nf("work", i)].label) : null, h("p", { class: "note warn" }, t("story.note"))));
    const pp = sortPeople(othersBy(i).filter((j) => KIND[j] === "person"));
    if (pp.length) out.push(facet(t("facet.people_named"), chips(pp, 30)));
  } else if (k === "group") {
    const pp = sortPeople(othersBy(i).filter((j) => KIND[j] === "person"));
    if (pp.length) out.push(facet(t("facet.members"), chips(pp, 30)));
  }
  const gaps = nf("gaps", i);
  if (gaps && S.depth !== "discover") out.push(facet(t("facet.gaps"), ...gaps.map((g) => h("p", { class: "note" }, g))));
  const dup = DUPES.get(i);
  if (dup && S.depth !== "discover") out.push(facet(t("facet.dupes", { n: fmt(dup.length - 1) }), h("p", { class: "muted" }, t("dupes.note")), chips(dup.filter((j) => j !== i), 12)));
  if (S.depth !== "discover") out.push(evidenceSummary(i), nodeLadder(i));
  out.push(...[mergeFacet(i), notesFacet(i)].filter(Boolean)); // part 9: merge proposals, class notes

  // every record
  if (S.depth === "discover") {
    out.push(h("section", { class: "facet" }, h("p", { class: "muted" }, t("discover.more", { n: fmt(deg[i]) })),
      h("button", { type: "button", class: "chip small", onclick: () => setDepth("study") }, t("discover.study"))));
  } else {
    const groups = groupClaims(i);
    const box = h("section", { class: "facet" }, h("h3", null, t("facet.records", { n: fmt(deg[i]) })));
    const lim = i === LIGHT ? 6 : 12;
    for (const [, cs] of groups) {
      const ul = h("ul", { class: "plain claims" });
      const draw = (m) => { ul.replaceChildren(...cs.slice(0, m).map((c) => claimRow(c, i))); if (cs.length > m) ul.append(h("li", null, h("button", { type: "button", class: "chip small", onclick: () => draw(cs.length) }, t("more.all", { n: fmt(cs.length) })))); };
      draw(lim);
      box.append(h("p", { class: "muted", style: "margin:10px 0 0" }, h("span", { class: "pred" }, predText(cs[0])), " · ", fmt(cs.length)), ul);
    }
    out.push(box);
  }
  body.replaceChildren(...out);
}
function presenceFacet(e) { // who was there, and who wasn't: only what a record states
  const g = peopleAt(e);
  const box = facet(t("presence.title"));
  for (const key of ["led", "part", "died", "other"]) {
    const arr = sortPeople([...g[key]]);
    if (!arr.length) continue;
    box.append(h("p", { class: "muted" }, t("who." + key, { n: fmt(arr.length) })), chips(arr, S.depth === "discover" ? 18 : 40));
  }
  if (!g.led.size && !g.part.size && !g.died.size && !g.other.size) box.append(h("p", { class: "muted" }, t("presence.none_present")));
  const abs = sortPeople([...g.absent]);
  if (abs.length) {
    box.append(h("p", { class: "muted" }, t("who.absent", { n: fmt(abs.length) })));
    if (S.depth === "discover") box.append(chips(abs, 18));
    else box.append(h("ul", { class: "plain claims" }, [...claimsOf(e)].filter((c) => pk(c) === "absent_from" && CL.o[c] === e).map((c) => claimRow(c, e))));
  } else box.append(h("p", { class: "muted small" }, t("presence.none_absent")));
  box.append(h("p", { class: "muted small" }, t("presence.note")));
  return box;
}
function evidenceSummary(i) { // claims by status, by who recorded them, by source text
  const st = new Map(), by = new Map(), work = new Map();
  const inc = (m, k) => m.set(k, (m.get(k) || 0) + 1);
  for (const c of claimsOf(i)) {
    inc(st, CL.st[c] === 1 ? t("status.proposed") : CL.st[c] === 0 ? t("status.record") : t("status.other"));
    inc(by, CL.src[c] >= 0 ? META.sources[CL.src[c]].label : "—");
    const w = cf("w", c);
    inc(work, w !== undefined ? META.sources[w].label : cf("cs", c) ? t("evidence.cited") : t("evidence.none"));
  }
  const table = (title, m) => h("div", null, h("p", { class: "muted", style: "margin:6px 0 2px" }, title),
    h("ul", { class: "plain counts" }, [...m.entries()].sort((a, b) => b[1] - a[1]).map(([k, v]) => h("li", null, h("span", null, k), h("span", { class: "count" }, fmt(v))))));
  return facet(t("evidence.title"), table(t("evidence.by_status"), st), table(t("evidence.by_recorder"), by), table(t("evidence.by_work"), work));
}
function nodeLadder(i) { // How do we know about this item?
  const d = h("details", { class: "how" }, h("summary", null, t("ladder.node", { name: nameOf(i) })));
  if (S.depth === "research") d.open = true;
  const box = h("div", { class: "ladder" });
  const sch = nf("sch", i);
  if (sch) box.append(h("p", null, h("b", null, t("ladder.scholarly")), " ", sch));
  const rec = nf("rec", i) || [0];
  box.append(h("p", null, h("b", null, t("ladder.recorded_by_h")), " ", rec.map((r) => META.sources[r] ? META.sources[r].label : "—").join(" · ")));
  box.append(h("p", null, h("b", null, t("ladder.record_h")), " ", t("coverage", { v: META.cov[ND.cv[i]] || "—" })));
  const dates = [...(nf("d", i) || []), ...(nf("death", i) || [])];
  box.append(h("p", null, h("b", null, t("ladder.dates")), " ", dates.length ? dates.map((x) => x[2] + (x[3] && x[3].length ? " (" + x[3].join("; ") + ")" : "")).join(" · ") : t("panel.no_date")));
  if (KIND[i] === "place") { const g = nf("geo", i); box.append(h("p", null, h("b", null, t("ladder.location")), " ", g ? t("place.located", { lon: g[0], lat: g[1], conf: g[2] || "" }) : t("place.unlocated"))); }
  const gaps = nf("gaps", i);
  if (gaps) box.append(h("p", null, h("b", null, t("ladder.gaps")), " ", gaps.join(" · ")));
  box.append(h("p", { class: "muted small" }, t("ladder.claims_count", { n: fmt(deg[i]) })));
  if (S.depth === "research") box.append(h("p", { class: "cite" }, t("panel.id", { id: ND.id[i] })));
  d.append(box);
  return d;
}
function oppNote(i) {
  const basis = [];
  for (const c of claimsOf(i)) {
    const p = pk(c);
    if ((p === "fought_against" && (CL.s[c] === LIGHT || CL.o[c] === LIGHT)) || (p === "opposed" && CL.o[c] === LIGHT && CL.s[c] === i)) basis.push(c);
    if ((cf("q", c) || []).some((q) => META.quals[q] === "accepted Islam later")) basis.push(c);
  }
  return h("div", { class: "note warn" }, h("p", null, isTurned(i) ? t("mark.turned_note") : t("mark.opponent_note")),
    h("ul", { class: "plain claims" }, [...new Set(basis)].map((c) => claimRow(c, i))));
}

// a line tapped: How do we know? A — B
function openPair(a, b) {
  const cs = [...claimsOf(a)].filter((c) => other(c, a) === b);
  if (!cs.length) return;
  pushHistory();
  S.focus = -1;
  emphasise(new Set([a, b]), new Set([Math.min(a, b) * 100000 + Math.max(a, b)]));
  LOG.ladders++; saveLog(); checkMilestones();
  const depth = S.depth;
  if (S.depth === "discover") S.depth = "study"; // the evidence needs its sources
  showPanel([
    h("p", { class: "kind" }, t("ladder.pair_kind")),
    h("h2", { class: "name" }, t("ladder.pair", { a: nameOf(a), b: nameOf(b) })),
    h("p", { class: "muted" }, t("ladder.pair_intro", { n: fmt(cs.length) })),
    h("div", { class: "row actions" }, h("button", { type: "button", class: "chip small", onclick: () => focus(a) }, nameOf(a)), h("button", { type: "button", class: "chip small", onclick: () => focus(b) }, nameOf(b))),
    h("ul", { class: "plain claims" }, cs.map((c) => claimRow(c, -1))),
  ]);
  S.depth = depth;
  here();
}

// two records side by side: what they share, as the records state it
function compare(a, b) {
  pushHistory();
  LOG.compares++; saveLog(); checkMilestones();
  S.focus = b;
  const evA = new Set(eventsOf(a)), evB = new Set(eventsOf(b));
  const nbA = neighbours(a), nbB = neighbours(b);
  const sharedEv = byText([...evA].filter((x) => evB.has(x)));
  const sharedPeople = sortPeople([...nbA].filter((x) => nbB.has(x) && KIND[x] === "person" && x !== a && x !== b));
  const sharedPlaces = [...nbA].filter((x) => nbB.has(x) && KIND[x] === "place");
  const direct = [...claimsOf(a)].filter((c) => other(c, a) === b);
  const lit = new Set([a, b, ...sharedEv, ...sharedPeople, ...sharedPlaces]);
  emphasise(lit);
  const pa = R.targetPos(a), pb = R.targetPos(b);
  R.flyTo({ target: [(pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2, (pa[2] + pb[2]) / 2], dist: Math.max(400, Math.min(4000, Math.hypot(pa[0] - pb[0], pa[1] - pb[1], pa[2] - pb[2]) * 2.2 + 300)) });
  const col = (i) => h("div", { class: "compare-col" }, h("h3", null, nameOf(i)), h("p", { class: "muted" }, t("records.count", { n: fmt(deg[i]) })),
    eventsOf(i).length ? h("div", null, h("p", { class: "muted" }, t("facet.events")), chips(eventsOf(i), 10)) : null,
    (() => { const K = kin(i); const fam = [...K.parents, ...K.spouses, ...K.children].map((x) => x[0]); return fam.length ? h("div", null, h("p", { class: "muted" }, t("facet.family")), chips(sortPeople(fam), 10)) : null; })());
  showPanel([
    h("p", { class: "kind" }, t("compare.kind")),
    h("h2", { class: "name" }, nameOf(a), " · ", nameOf(b)),
    h("p", { class: "muted" }, t("compare.note")),
    facet(t("compare.direct", { n: fmt(direct.length) }), direct.length ? h("ul", { class: "plain claims" }, direct.map((c) => claimRow(c, -1))) : h("p", { class: "muted" }, t("compare.none"))),
    facet(t("compare.events", { n: fmt(sharedEv.length) }), sharedEv.length ? chips(sharedEv) : h("p", { class: "muted" }, t("compare.none"))),
    facet(t("compare.people", { n: fmt(sharedPeople.length) }), sharedPeople.length ? chips(sharedPeople, 18) : h("p", { class: "muted" }, t("compare.none"))),
    sharedPlaces.length ? facet(t("compare.places", { n: fmt(sharedPlaces.length) }), chips(sharedPlaces)) : null,
    h("div", { class: "compare-grid" }, col(a), col(b)),
  ].filter(Boolean));
  S.compare = -1;
  here();
}

// a citation of the record, to paste into notes
function citeRecord(i) {
  const fm = firstMention(i);
  return [
    `${nameOf(i)}${nf("sch", i) && LANG === "en" ? " (" + nf("sch", i) + ")" : ""}.`,
    t("cite.line", { n: fmt(deg[i]), kind: kindText(i) }),
    fm ? fm + "." : null,
    t("cite.status"),
    t("cite.source", { date: new Date().toISOString().slice(0, 10), fp: META.fingerprint || "—", id: ND.id[i] }),
  ].filter(Boolean).join(" ");
}

// the learner's own star chart
function toggleStar(i) {
  const id = ND.id[i], at = STARS.indexOf(id);
  if (at >= 0) STARS.splice(at, 1); else STARS.push(id);
  store.set(STAR_KEY, STARS);
  toast(at >= 0 ? t("star.removed", { name: nameOf(i) }) : t("star.added", { name: nameOf(i) }));
}
let ID_INDEX = null;
function byId(id) { if (!ID_INDEX) { ID_INDEX = new Map(); ND.id.forEach((x, i) => ID_INDEX.set(x, i)); } return ID_INDEX.has(id) ? ID_INDEX.get(id) : -1; }
