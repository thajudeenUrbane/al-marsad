  // ------------------------------------------------------------------ Sky Atlas additions (interface side)
  function journeyWhy(st) {
    const w = st.why;
    if (w.k === "part") return t("x.journey.why.part", { whole: N[w.w].n });
    if (w.k === "story") return t("x.journey.why.story", { no: w.no || "—" });
    if (w.k === "present") return t("x.journey.why.present", { event: N[w.w].n, pred: predText(C[w.ci]) });
    if (w.k === "absent") return t("x.journey.why.absent", { event: N[w.w].n });
    return t("x.journey.why.named");
  }
  const jbar = byId("journey-bar");
  let journeyTimer = 0;
  function syncJourneyBar() {
    const J = S.journey;
    jbar.hidden = !J;
    if (!J) return;
    byId("jb-title").textContent = t("x.journey.bar", { title: t("x.journey." + J.key + ".title") });
    byId("jb-stop").textContent = t("x.journey.stop", { k: J.k + 1, n: J.stops.length }) + t("sep.dot") + N[J.stops[J.k].i].n;
    byId("jb-prev").disabled = J.k === 0;
    byId("jb-next").disabled = J.k >= J.stops.length - 1;
    const pb = byId("jb-play");
    pb.textContent = t(J.playing ? "x.journey.pause" : "x.journey.play");
    pb.setAttribute("aria-pressed", J.playing ? "true" : "false");
    jbar.setAttribute("aria-label", t("x.journey.bar", { title: t("x.journey." + J.key + ".title") }));
  }
  function gotoStop(k) {
    const J = S.journey;
    if (!J) return;
    J.k = Math.max(0, Math.min(J.stops.length - 1, k));
    const i = J.stops[J.k].i;
    S.hl = J.lit.slice(); S.hlClass = null; S.focus = i; S.links = null; S.nodeLadder = false; S.panel = "focus";
    S.camMode = "free";
    update(false);
    R.flyToNode(i, J.zoom);
    if (panel.dataset.open !== "true") openSheet();
    syncJourneyBar();
    announce(t("x.journey.announce", { title: t("x.journey." + J.key + ".title"), k: J.k + 1, n: J.stops.length, name: N[i].n }));
  }
  function startJourney(key) {
    const J = buildJourney(key);
    if (!J.stops.length) { announce(t("x.journey.empty")); return; }
    stopJourneyQuiet();
    R.setGlobe(false);
    pushHistory();
    S.preset = null; byId("obs-preset").value = "";
    S.trace = { a: -1, b: -1, paths: [], total: 0, sel: 0, open: false }; S.picking = false;
    S.scrub.on = false; syncScrub();
    if (S.weights[0] < 0.985) { R.stopAnim(); S.weights = [1, 0, 0, 0, 0]; R.blend(); R.rebase(); syncFrameControls(); }
    S.journey = J;
    const r = canvas.getBoundingClientRect();
    if (r.top < -r.height / 2 || r.top > window.innerHeight / 2) bringStageUp();
    gotoStop(0);
  }
  function playJourney(on) {
    const J = S.journey;
    if (!J) return;
    clearInterval(journeyTimer);
    J.playing = on;
    if (on) journeyTimer = setInterval(() => {
      if (!S.journey) { clearInterval(journeyTimer); return; }
      if (S.journey.k >= S.journey.stops.length - 1) { playJourney(false); return; }
      gotoStop(S.journey.k + 1);
    }, 4500);
    syncJourneyBar();
  }
  function stopJourneyQuiet() {
    clearInterval(journeyTimer);
    if (!S.journey) return false;
    S.journey = null; absentCache.e = -2;
    syncJourneyBar();
    return true;
  }
  function endJourney() {
    if (stopJourneyQuiet()) { clearFocus(); announce(t("x.journey.done")); }
  }
  byId("jb-prev").addEventListener("click", () => { playJourney(false); gotoStop(S.journey.k - 1); });
  byId("jb-next").addEventListener("click", () => { playJourney(false); gotoStop(S.journey.k + 1); });
  byId("jb-play").addEventListener("click", () => {
    const J = S.journey;
    if (!J) return;
    if (!J.playing && J.k >= J.stops.length - 1) gotoStop(0);
    playJourney(!J.playing);
  });
  byId("jb-end").addEventListener("click", endJourney);
  function fillJourneyPick() {
    const sel = byId("journey-pick"), v = sel.value;
    sel.replaceChildren(...JOURNEYS.map((k) => h("option", { value: k }, t("x.journey." + k + ".title"))));
    if (v) sel.value = v;
  }
  byId("journey-start").addEventListener("click", () => startJourney(byId("journey-pick").value));

  function journeyNote() {
    const J = S.journey;
    if (!J || S.focus !== J.stops[J.k].i) return null;
    return h("div", { class: "note journey-note" },
      h("strong", null, t("x.journey.active", { title: t("x.journey." + J.key + ".title"), k: J.k + 1, n: J.stops.length })),
      h("div", { class: "muted" }, t("x.journey." + J.key + ".lead")),
      h("div", null, journeyWhy(J.stops[J.k])));
  }
  function presenceFacet(e) {
    const p = presenceOf(e);
    const sortN = (a, b) => (a === LIGHT_I ? -1 : b === LIGHT_I ? 1 : N[a].n.localeCompare(N[b].n));
    const pres = h("ul", { class: "rows" });
    for (const s of [...p.present.keys()].sort(sortN)) {
      const cis = p.present.get(s);
      const lis = [...new Set(cis.map((ci) => L.findIndex((l) => l.cl.includes(ci))))].filter((x) => x >= 0);
      pres.append(h("li", { class: "row" }, h("div", { class: "row-main" }, nodeBtn(s, "inline"), h("span", { class: "pred" }, [...new Set(cis.map((ci) => predText(C[ci])))].join(t("sep.list")))),
        h("div", { class: "row-sub" }, [...new Set(cis.map((ci) => C[ci].st || ""))].map((st) => statusChip(st || null)), " ", howBtn(() => interrogateLinks(lis)))));
    }
    const abs = h("ul", { class: "rows" });
    for (const s of [...p.absent.keys()].sort(sortN)) {
      const ci = p.absent.get(s)[0], c = C[ci];
      const li = L.findIndex((l) => l.cl.includes(ci));
      abs.append(h("li", { class: "row absent-row" }, h("div", { class: "row-main" }, nodeBtn(s, "inline"), h("span", { class: "st absent-chip" }, predText(c))),
        c.b !== undefined ? h("q", null, STR[c.b]) : null,
        h("div", { class: "row-sub" }, statusChip(c.st), " ", li >= 0 ? howBtn(() => interrogateLinks([li])) : null)));
    }
    return h("section", { class: "facet presence", "aria-labelledby": "fh-presence" },
      h("h3", { id: "fh-presence" }, t("x.presence.title")),
      h("p", { class: "muted" }, t("x.presence.note")),
      h("h4", null, t("x.presence.present"), h("span", { class: "count" }, fmt(p.present.size))),
      p.present.size ? pres : h("p", { class: "muted" }, t("x.presence.none_present")),
      h("h4", null, t("x.presence.absent"), h("span", { class: "count" }, fmt(p.absent.size))),
      p.absent.size ? abs : h("p", { class: "muted" }, t("x.presence.none_absent")));
  }
  function chainLine(i) {
    const ci = chainInfo.get(i);
    if (!ci) return null;
    const label = CHAINS[ci.ci].label || "—";
    return h("p", null, t(ci.col ? "x.chain.collector" : "x.chain.place", { d: ci.d, label }));
  }

  // test load and faster drawing
  byId("scale-pick").addEventListener("change", (e) => {
    const v = +e.target.value;
    R.setTestLoad(v);
    announce(v ? t("x.scale.announce", { n: fmt(v) }) : t("x.scale.announce_off"));
  });
  byId("sky-gpu").addEventListener("click", () => {
    if (R.setGPU(!R.gpuOn())) announce(t(R.gpuOn() ? "x.sky.announce.gpu.on" : "x.sky.announce.gpu.off"));
  });
  byId("frame-globe").addEventListener("click", () => {
    const r = canvas.getBoundingClientRect();
    if (r.top < -r.height / 2 || r.top > window.innerHeight / 2) bringStageUp();
    stopJourneyQuiet();
    R.setGlobe(!R.globeOn());
  });

  // the interface language: English or Arabic, right to left
  function buildOptions() {
    optionLabel.length = 0; byOption.clear();
    N.forEach((nd, i) => {
      let lab = I18N["search.option"].replace("{name}", nd.n).replace("{kind}", I18N["kind." + nd.k]);
      if (byOption.has(lab)) {
        const nth = (k) => I18N["search.option_nth"].replace("{label}", lab).replace("{k}", k);
        let k = 2; while (byOption.has(nth(k))) k++; lab = nth(k);
      }
      optionLabel[i] = lab;
      byOption.set(lab, i);
    });
    const dl = byId("obs-names");
    dl.replaceChildren(...N.map((nd, i) => h("option", { value: optionLabel[i] })));
  }
  function setLang(l, quiet) {
    S.lang = l === "ar" ? "ar" : "en";
    I18N = S.lang === "ar" ? Object.assign({}, EN, AR) : EN;
    const root = document.documentElement;
    root.lang = S.lang; root.dir = S.lang === "ar" ? "rtl" : "ltr";
    document.title = t("x.page.title");
    N.forEach((nd) => { nd.n = S.lang === "ar" && nd.ar && nd.ar.length ? nd.ar[0] : nd.nEn; });
    const lb = byId("lang-switch");
    lb.setAttribute("lang", S.lang === "ar" ? "en" : "ar");
    byId("lang-note").hidden = S.lang !== "ar";
    buildOptions();
    const preset = byId("obs-preset"), pv = preset.value;
    preset.replaceChildren(h("option", { value: "", "data-i18n": "presets.none" }, t("presets.none")), ...PRESETS.map((p) => h("option", { value: p.key }, t("preset." + p.key))));
    preset.value = pv;
    byId("legend-types").replaceChildren(); byId("legend-lines").replaceChildren(); buildLegend(); syncLegend();
    byId("legend-chain-note").textContent = t("x.legend.chain.note", { n: fmt(CHAINS.length) });
    fillJourneyPick();
    relabelStatic(); R.relabel(); syncScrub(); syncJourneyBar(); syncFrameControls();
    try { localStorage.setItem("marsad-sky-lang", S.lang); } catch (e) { /* storage blocked: the switch still works for this visit */ }
    if (!quiet) { update(false); announce(t("x.announce.lang")); }
  }
  byId("lang-switch").addEventListener("click", () => setLang(S.lang === "ar" ? "en" : "ar"));
