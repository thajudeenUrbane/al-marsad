import json, re, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
src = open('sky-base.html').read()
# strip the service's wrapper: the page itself starts at the second doctype
src = src[src.index('<!doctype html>\n<html'):]
src = src[:src.rindex('</html>') + len('</html>')] + '\n'

def rep(old, new, count=1):
    global src
    k = src.count(old)
    if k != count:
        sys.exit(f'expected {count} of {old[:80]!r}, found {k}')
    src = src.replace(old, new)

# ---------- head
rep('<title>Sky – al-Marṣad</title>', '<title>Sky Atlas – al-Marṣad</title>')
rep('<meta name="description" content="The whole graph of the Seerah as a sky you can turn:',
    '<meta name="description" content="Sky Atlas: the Sky with guided journeys, chain-distance light, star groups at scale, a globe, who was there and who was not, and an Arabic interface. The whole graph of the Seerah as a sky you can turn:')
rep('</style>\n</head>', open('add.css').read() + '</style>\n</head>')

# ---------- body
b0 = src.index('<body>\n<a class="skip"')
b1 = src.index('</footer>\n', b0) + len('</footer>\n')
src = src[:b0] + open('body.html').read() + src[b1:]

# ---------- data: strings, Arabic, coastlines
en_new = json.load(open('new_en.json')); ar = json.load(open('ar.json')); ar.update(json.load(open('new_ar.json')))
m = re.search(r'(<script type="application/json" id="obs-i18n">)(.*?)(</script>)', src, re.S)
en = json.loads(m.group(2)); en.update(en_new)
esc = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
extra = ('\n<script type="application/json" id="obs-i18n-ar">' + esc(ar) + '</script>'
         '\n<script type="application/json" id="sky-land">' + open('land_rings.json').read() + '</script>')
src = src[:m.start()] + m.group(1) + esc(en) + m.group(3) + extra + src[m.end():]

# ---------- renderer
rep('    syncFrameControls, syncScrub, updateHere, writeHash, announce, t } = api;',
    '    syncFrameControls, syncScrub, updateHere, writeHash, announce, t } = api;\n  // Sky Atlas: chain light, groups, test load, GPU drawing and the globe are added below')
rep('const opt = { generation: true, names: true, scenery: true, orbit: false };',
    'const opt = { generation: true, names: true, scenery: true, orbit: false, chain: false, cluster: false, gpu: false };')
rep('''  function starLight(i) {
    if (!opt.generation) return [RGB.genOff, 1, 0.38];''', '''  function starLight(i) {
    if (opt.chain) { // brightness by place in a recorded narration chain, when switched on
      const d = CHAIN_D[i];
      if (!d) return [RGB.genNone, 0.55, 0];
      const f = CHAIN_MAX > 1 ? (d - 1) / (CHAIN_MAX - 1) : 0;
      return [mix(RGB.gen0, RGB.gen2, f), 1 - 0.4 * f, 0.55 - 0.4 * f];
    }
    if (!opt.generation) return [RGB.genOff, 1, 0.38];''')
rep('''  function animateTo(weights, camMode) {
    if (camMode) S.camMode = camMode;''', '''  function animateTo(weights, camMode) {
    if (globeOn) { requestDraw(); return; }
    if (camMode) S.camMode = camMode;''')
rep('''    ctx.drawImage(backdrop, 0, 0);
    if (!opt.scenery) return;''', '''    if (opt.gpu) { ctx.clearRect(0, 0, canvas.width, canvas.height); return; } // the GPU layer underneath draws the sky
    ctx.drawImage(backdrop, 0, 0);
    if (!opt.scenery) return;''')
rep('          ctx.fillText(d.s, p[0], p[1] + (d.dy || 0) * k);', '          ctx.fillText(api.decoText ? api.decoText(d.s) : d.s, p[0], p[1] + (d.dy || 0) * k);')
rep('''  let order = [];
  function drawMarks(now) {
    order = [];
    for (let i = 0; i < n; i++) if (nodeA[i] && SS[i]) order.push(i);
    order.sort((a, b) => SD[b] - SD[a]); // far first: near stars pass in front
    for (const i of order) {''', open('r_add.js').read() + '''  let order = [];
  function prepMarks() {
    order = [];
    for (let i = 0; i < n; i++) if (nodeA[i] && SS[i]) order.push(i);
    order.sort((a, b) => SD[b] - SD[a]); // far first: near stars pass in front
    absentSet = api.absent();
    projectTests();
    buildClusters();
  }
  function drawMarks(now) {
    for (const i of order) {
      if (clustered[i]) continue;''')
rep('''      drawMark(i, x, y, r, a, nodeHollow[i]);
      if (nodeLvl[i] === 2''', '''      drawMark(i, x, y, r, a, nodeHollow[i]);
      if (absentSet && absentSet.has(i)) drawAbsent(i, x, y, r);
      if (nodeLvl[i] === 2''')
rep('''    const push = (i, pri) => { if (i >= 0 && nodeA[i] > 0.5 && SS[i]) out.push([pri, i, 1]); };
    const pushStructural = (i, pri) => { if (i >= 0 && nodeA[i] > 0 && SS[i]) out.push([pri, i, nodeA[i] > 0.5 ? 1 : 0.6]); };''',
'''    const push = (i, pri) => { if (i >= 0 && nodeA[i] > 0.5 && SS[i] && !clustered[i]) out.push([pri, i, 1]); };
    const pushStructural = (i, pri) => { if (i >= 0 && nodeA[i] > 0 && SS[i] && !clustered[i]) out.push([pri, i, nodeA[i] > 0.5 ? 1 : 0.6]); };
    if (opt.chain) for (let i = 0; i < n; i++) if (CHAIN_D[i]) push(i, 6.2);''')
rep('''  function draw(now) {
    project();
    drawBackdrop();
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.globalAlpha = 1;
    drawRing();
    drawDeco();
    drawTimeMarks();
    drawLinks();
    drawMarks(now || performance.now());
    drawLabels();
  }''', '''  function draw(now) {
    const t0 = performance.now();
    project();
    drawBackdrop();
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.globalAlpha = 1;
    if (globeOn) {
      absentSet = api.absent(); clustered.fill(0); clusters = []; buckets = null; TA.fill(0);
      drawGlobe();
    } else {
      drawRing();
      drawDeco();
      drawTimeMarks();
      drawLinks();
      prepMarks();
      if (!opt.gpu) drawTests2D();
      drawMarks(now || t0);
      drawClusters();
      drawTrail();
      drawLabels();
    }
    if (opt.gpu) drawGL();
    notePerf(performance.now() - t0, now || t0);
  }''')
rep('''  function nodeAt(x, y, touch) {
    let best = -1, bd = Infinity;
    const lim = touch ? 22 : 12;
    for (let i = 0; i < n; i++) {
      if (!nodeA[i] || !SS[i]) continue;''', '''  function nodeAt(x, y, touch) {
    let best = -1, bd = Infinity;
    const lim = touch ? 22 : 12;
    if (globeOn) {
      for (const [hx, hy, i, r] of globeHits) { const d = Math.hypot(hx - x, hy - y) - r; if (d < Math.min(lim, 10) && d < bd) { bd = d; best = i; } }
      return best;
    }
    for (let i = 0; i < n; i++) {
      if (!nodeA[i] || !SS[i] || clustered[i]) continue;''')
rep('''  function linkAt(x, y) {
    let best = -1, bd = 36;''', '''  function linkAt(x, y) {
    let best = -1, bd = 36;
    if (globeOn) return -1;''')
rep('''        anim = null; flight = null;
        cam.yaw += dx * 0.0065; cam.pitch = clampPitch(cam.pitch + dy * 0.0065);
        spin.yaw = dx * 0.0065; spin.pitch = dy * 0.0065; lastMove = performance.now();''', '''        anim = null; flight = null;
        const k = globeOn ? 1 / globeParams().R : 0.0065; // on the globe, the land follows the finger
        cam.yaw += dx * k; cam.pitch = clampPitch(cam.pitch + dy * k);
        spin.yaw = dx * k; spin.pitch = dy * k; lastMove = performance.now();''')
rep('''    const i = nodeAt(e.offsetX, e.offsetY, false);
    if (i >= 0) flyTo(''', '''    if (globeOn) return;
    const i = nodeAt(e.offsetX, e.offsetY, false);
    if (i >= 0) flyTo(''')
rep('''  function tap(x, y, touch) {
    const i = nodeAt(x, y, touch);''', '''  function tap(x, y, touch) {
    if (!globeOn && opt.cluster) {
      const c = clusterAt(x, y, touch);
      if (c) { flyTo({ x: c.X, y: c.Y, z: c.Z, dist: clampDist(cam.dist * 0.4) }, 800); announce(t("x.cluster.open", { n: c.n })); return; }
    }
    const i = nodeAt(x, y, touch);''')
rep('''        case "0": S.camMode = S.focus >= 0 ? "focus" : "fit"; animateTo(null); break;''',
    '''        case "0": if (globeOn) { Object.assign(cam, { yaw: 0, pitch: 0, dist: 1800 }); break; } S.camMode = S.focus >= 0 ? "focus" : "fit"; animateTo(null); break;''')
rep('''      opt[key] = !opt[key]; press(id, opt[key]);''', '''      opt[key] = !opt[key]; press(id, opt[key]);
      if (key === "generation" && opt.generation && opt.chain) { opt.chain = false; press("sky-chain", false); }
      if (key === "chain" && opt.chain && opt.generation) { opt.generation = false; press("sky-generation", false); }''')
rep('''  toggle("sky-orbit", "orbit", "sky.announce.orbit");''', '''  toggle("sky-orbit", "orbit", "sky.announce.orbit");
  toggle("sky-chain", "chain", "x.sky.announce.chain");
  toggle("sky-cluster", "cluster", "x.sky.announce.cluster");''')
rep('''      const [yaw, pitch] = VIEWS[b.dataset.skyView];''', '''      if (globeOn) setGlobe(false);
      const [yaw, pitch] = VIEWS[b.dataset.skyView];''')
rep('''    refit() {
      inset = stageInset();
      if (anim || S.camMode === "free") { requestDraw(); return; }''', '''    refit() {
      inset = stageInset();
      if (anim || globeOn || S.camMode === "free") { requestDraw(); return; }''')
rep('''    clearCaches() {},
  };''', '''    clearCaches() {},
    // Sky Atlas
    flyToNode(i, k) {
      if (globeOn || i < 0) { requestDraw(); return; }
      flyTo({ x: P[3 * i], y: P[3 * i + 1], z: P[3 * i + 2], dist: clampDist((S.baseDist || cam.dist) / (k || 3)) }, 1200);
    },
    setTestLoad,
    testCount: () => T,
    setGPU,
    gpuOn: () => opt.gpu,
    setGlobe,
    globeOn: () => globeOn,
    relabel() { syncPlay(); requestDraw(); },
  };''')

# ---------- app
rep('''  const I18N = JSON.parse(byId("obs-i18n").textContent);''', '''  const EN = JSON.parse(byId("obs-i18n").textContent);
  const AR = (() => { try { return JSON.parse(byId("obs-i18n-ar").textContent); } catch (e) { return {}; } })();
  let I18N = EN;''')
rep('''  const n = N.length;
  const mq =''', '''  const n = N.length;
  N.forEach((nd) => { nd.nEn = nd.n; });
  const mq =''')
rep('''    allOpen: false,
  };''', '''    allOpen: false,
    lang: "en", journey: null,
  };''')
rep('''  // ------------------------------------------------------------------ renderer
  // Everything the renderer reads''', open('app_pre.js').read() + '''
  // ------------------------------------------------------------------ renderer
  // Everything the renderer reads''')
rep('''    syncScrub, updateHere, updateTextAlt, writeHash, announce,
  });''', '''    syncScrub, updateHere, updateTextAlt, writeHash, announce,
    chainDist, chainMax, absent: absentSet, trail: () => (S.journey ? { stops: S.journey.idx, k: S.journey.k, line: S.journey.line } : null),
    land: LAND, globeMoves: () => MOVES, placeCounts: () => PLACE_COUNTS, decoText,
  });''')
# Home and clear end a journey and leave the globe
rep('''  function clearFocus() {
    pushHistory();''', '''  function clearFocus() {
    stopJourneyQuiet();
    pushHistory();''')
rep('''  function home() {
    pushHistory();''', '''  function home() {
    stopJourneyQuiet(); R.setGlobe(false);
    pushHistory();''')
rep('''    if (record !== false) pushHistory();
    S.preset = p.key;''', '''    if (record !== false) pushHistory();
    stopJourneyQuiet(); R.setGlobe(false);
    S.preset = p.key;''')
# predicates in the interface language
rep('''    return h("span", { class: "claim" }, nameOrBtn(c.s, focus), " ", h("span", { class: "pred" }, c.p), " ", nameOrBtn(c.o, focus),''',
    '''    return h("span", { class: "claim" }, nameOrBtn(c.s, focus), " ", h("span", { class: "pred" }, predText(c)), " ", nameOrBtn(c.o, focus),''')
rep('''t("textalt.claim", { s: N[C[r.ci].s].n, p: C[r.ci].p, o: N[C[r.ci].o].n,''', '''t("textalt.claim", { s: N[C[r.ci].s].n, p: predText(C[r.ci]), o: N[C[r.ci].o].n,''')
rep('''t("textalt.claim", { s: N[c.s].n, p: c.p, o: N[c.o].n,''', '''t("textalt.claim", { s: N[c.s].n, p: predText(c), o: N[c.o].n,''')
# chain place in the generation facet
rep('''      if (nd.tb) body.append(h("p", null, t("panel.generation", { value: nd.tb })));''', '''      if (nd.tb) body.append(h("p", null, t("panel.generation", { value: nd.tb })));
      const cl = chainLine(i); if (cl) body.append(cl);''')
# who was there: first for an event; recorded absences for a person
rep('''    const order = S.lens === "discover" ? ["stories", "rel", "events", "places", "time", "evidence"] : ["evidence", "rel", "events", "places", "stories", "time"];
    return h("div", null, head, order.map((k) => facets[k]()));''', '''    const order = S.lens === "discover" ? ["stories", "rel", "events", "places", "time", "evidence"] : ["evidence", "rel", "events", "places", "stories", "time"];
    const abs = nd.k === "person" ? absentFrom(i) : [];
    return h("div", null, head,
      abs.length ? h("p", { class: "note" }, t("x.presence.person", { list: abs.map((e) => N[e].n).join(t("sep.list")) })) : null,
      nd.k === "event" ? presenceFacet(i) : null,
      order.map((k) => facets[k]()));''')
# intro: journeys
rep('''      h("section", { class: "facet" }, h("h3", null, t("reality.title")),''', '''      h("section", { class: "facet" }, h("h3", null, t("x.journeys.legend")),
        h("p", { class: "muted" }, t("x.journeys.note")),
        h("ul", { class: "plain journey-list" }, JOURNEYS.map((k) => h("li", null,
          h("button", { type: "button", class: "btn", onclick: () => startJourney(k) }, t("x.journey." + k + ".title")),
          h("div", { class: "muted" }, t("x.journey." + k + ".lead")))))),
      h("section", { class: "facet" }, h("h3", null, t("reality.title")),''')
rep('''    panelBody.append(view);
    if (S.lens === "research")''', '''    const jn = journeyNote();
    if (jn) panelBody.append(jn);
    panelBody.append(view);
    if (S.lens === "research")''')
# where you are, and the text view
rep('''    const parts = [t("here.lens", { lens: t("lens." + S.lens) }), t("here.frame", { frame: frameName() })];''',
    '''    const parts = [t("here.lens", { lens: t("lens." + S.lens) }), t("here.frame", { frame: R.globeOn() ? t("x.globe.here") : frameName() })];
    if (S.journey) parts.push(t("x.journey.stop", { k: S.journey.k + 1, n: S.journey.stops.length }) + " · " + t("x.journey." + S.journey.key + ".title"));''')
rep('''    const rc = regionCounts(d);''', '''    if (R.globeOn()) {
      const located = N.filter((x) => x.k === "place" && x.geo).map((x) => x.n);
      const moves = MOVES.map((m) => `${N[m.a].n}${t("sep.arrow")}${N[m.b].n} (${Math.floor(m.y)})`);
      box.append(h("p", null, t("x.globe.textalt", { list: located.join(t("sep.list")), moves: moves.join(t("sep.list")) || t("x.globe.no_moves") })));
      box.append(h("p", null, t("x.globe.waiting", { list: N.filter((x) => x.k === "place" && !x.geo).map((x) => x.n).join(t("sep.list")) })));
    }
    if (S.journey) {
      const J = S.journey;
      box.append(h("p", null, t("x.textalt.journey", { title: t("x.journey." + J.key + ".title"), k: J.k + 1, n: J.stops.length, name: N[J.stops[J.k].i].n })));
    }
    if (S.focus >= 0 && N[S.focus].k === "event") {
      const p = presenceOf(S.focus);
      const names = (m) => [...m.keys()].map((s) => N[s].n).join(t("sep.list")) || "—";
      box.append(h("p", null, t("x.textalt.presence", { event: N[S.focus].n, present: names(p.present), absent: names(p.absent) })));
    }
    const rc = regionCounts(d);''')
# frame buttons and the morph slider leave the globe
rep('''    byId("frame-" + f).addEventListener("click", () => {
      const w = [0, 0, 0, 0, 0]; w[k] = 1;''', '''    byId("frame-" + f).addEventListener("click", () => {
      R.setGlobe(false);
      const w = [0, 0, 0, 0, 0]; w[k] = 1;''')
rep('''  byId("obs-morph").addEventListener("input", (e) => {
    R.stopAnim();''', '''  byId("obs-morph").addEventListener("input", (e) => {
    R.setGlobe(false);
    R.stopAnim();''')
# search also finds the English name in Arabic mode
rep('''      const hit = N.findIndex((nd) => nd.n.toLowerCase().includes(q));''', '''      const hit = N.findIndex((nd) => nd.n.toLowerCase().includes(q) || nd.nEn.toLowerCase().includes(q));''')
# static strings: text, placeholders, aria labels and titles
rep('''    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });''', '''    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("[data-i18n-ph]").forEach((el) => { el.setAttribute("placeholder", t(el.dataset.i18nPh)); });
    document.querySelectorAll("[data-i18n-aria]").forEach((el) => { el.setAttribute("aria-label", t(el.dataset.i18nAria)); });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => { el.setAttribute("title", t(el.dataset.i18nTitle)); });''')
rep('''  // ------------------------------------------------------------------ start
  function start() {''', open('app_post.js').read() + '''
  // ------------------------------------------------------------------ start
  function start() {''')
rep('''    const preset = byId("obs-preset");
    for (const p of PRESETS) preset.append(h("option", { value: p.key }, t("preset." + p.key)));
    const dl = byId("obs-names");
    N.forEach((nd, i) => dl.append(h("option", { value: optionLabel[i] })));
    buildLegend();''', '''    const preset = byId("obs-preset");
    for (const p of PRESETS) preset.append(h("option", { value: p.key }, t("preset." + p.key)));
    const dl = byId("obs-names");
    N.forEach((nd, i) => dl.append(h("option", { value: optionLabel[i] })));
    buildLegend();
    fillJourneyPick();
    byId("legend-chain-note").textContent = t("x.legend.chain.note", { n: fmt(CHAINS.length) });
    let lang = /[#&]lang=ar/.test(location.hash) ? "ar" : "en";
    try { if (!/[#&]lang=/.test(location.hash) && localStorage.getItem("marsad-sky-lang") === "ar") lang = "ar"; } catch (e) { /* no storage here */ }
    if (lang === "ar") setLang("ar", true);''')
open('../index.html', 'w').write(src)
print('wrote sky-atlas/index.html,', len(src), 'bytes')
