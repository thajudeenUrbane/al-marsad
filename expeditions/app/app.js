/* al-Marṣad Expeditions: the app. One view at a time, chosen by the address's #token:
   (none) home · x-<slug>[-<step>] an expedition · review · desk[-<slug>] · halaqa-<slug>[-<step>] · follow · about
   Every fact shown comes from data/*.json, which the compiler built from the graph. The guide only asks. */
"use strict";
(function () {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const M = window.Memory;
  const view = $("#view");
  const VOICE = { ishq: "Ibn Isḥāq's list", hish: "in Ibn Hishām's voice", none: "voice not tagged by the extraction" };
  const CAND = { before: "the lunation before", tabular: "the tabular lunation", after: "the lunation after" };
  const cache = {};
  let INDEX = null, STARS = null, world = null, lensOn = false, bc = null;

  const load = name => cache[name] || (cache[name] = fetch(`data/${name}.json`).then(r => { if (!r.ok) throw new Error(`data/${name}.json: ${r.status}`); return r.json(); }));
  const prov = (cls, inner, tag = "span", extra = "") => `<${tag} data-prov="${cls}" ${extra}>${inner}</${tag}>`;
  const chip = cls => `<span class="chip" style="--pc: var(--p-${cls})">${cls}</span>`;
  const guide = html => `<div class="guide">${html}</div>`;
  const localTime = (ut, off) => { const [h, m] = ut.split(":").map(Number); const t = ((h * 60 + m + off) % 1440 + 1440) % 1440; return String(Math.floor(t / 60)).padStart(2, "0") + ":" + String(t % 60).padStart(2, "0"); };
  const fmtDue = t => { if (!t) return "nothing scheduled"; const d = Math.round((t - Date.now()) / 864e5); return d <= 0 ? "due now" : d === 1 ? "due tomorrow" : `due in ${d} days`; };

  /* ---------------- the lens ---------------- */
  $("#lens").addEventListener("click", e => {
    lensOn = e.currentTarget.getAttribute("aria-pressed") !== "true";
    e.currentTarget.setAttribute("aria-pressed", lensOn);
    document.body.classList.toggle("lens", lensOn);
    if (world) world.lens(lensOn);
    $$("canvas[data-redraw]").forEach(c => c.dispatchEvent(new Event("redraw")));
  });

  /* ---------------- routing ---------------- */
  function parse() {
    const h = location.hash.replace(/^#/, "");
    let m;
    if ((m = h.match(/^x-([a-z]+)(?:-(\d+))?$/))) return { v: "x", slug: m[1], step: +(m[2] || 0) };
    if ((m = h.match(/^halaqa-([a-z]+)(?:-(\d+))?$/))) return { v: "halaqa", slug: m[1], step: +(m[2] || 0) };
    if ((m = h.match(/^desk(?:-([a-z]+))?$/))) return { v: "desk", slug: m[1] };
    if (h === "review" || h === "about" || h === "follow") return { v: h };
    return { v: "home" };
  }
  async function route() {
    if (world) { world.destroy(); world = null; }
    const r = parse();
    document.body.classList.toggle("halaqa", r.v === "halaqa");
    $$(".nav a").forEach(a => a.setAttribute("aria-current", a.dataset.v === r.v ? "page" : "false"));
    try {
      INDEX = INDEX || await load("index");
      if (r.v === "x" || r.v === "halaqa") await expedition(r.slug, r.step, r.v === "halaqa");
      else if (r.v === "review") await review();
      else if (r.v === "desk") await desk(r.slug);
      else if (r.v === "about") about();
      else if (r.v === "follow") follow();
      else await home();
    } catch (err) {
      view.innerHTML = `<div class="wrap"><h1>Something did not load</h1><p class="muted">${esc(err.message)}. The plain version works without any of this: <a href="text/index.html">all expeditions as text</a>.</p></div>`;
    }
    if (r.v !== "halaqa") window.scrollTo(0, 0);
  }
  window.addEventListener("hashchange", route);

  /* ---------------- home ---------------- */
  function progress(x) {
    const done = (M.state.steps[x.slug] || []).length, steps = (x.steps || 0);
    return done ? `<span class="status"><b>${done}</b> steps visited</span>` : `<span class="status">Not started</span>`;
  }
  async function home() {
    const due = M.due().length, seen = Object.keys(M.state.seen).length;
    view.innerHTML = `<div class="wrap">
      <section class="hero">
        <div>
          <p class="kicker">al-Marṣad · expeditions into evidence</p>
          <h1>Stand in the place. Then ask how we know.</h1>
          <p class="lead">Five moments from Ibn Isḥāq's account of the Prophet's life ﷺ, as Ibn Hishām edited it. Each opens on the real ground under the sky astronomy computes, then hands you a real question in the text to investigate. No one is ever drawn: only places, ground, sky and names.</p>
          <p class="notice"><b>A working preview.</b> Nothing here is scholar-reviewed. Names and links are claims an AI pass proposed from the text. Press <b>Provenance lens</b> at the top to see where everything comes from.</p>
        </div>
        <div><canvas id="skyline" aria-label="The five expeditions in the order the text tells them, and a light for every name you have opened"></canvas>
          <p class="quiet" style="font-size:.82rem;margin-top:6px">Each bright point is an expedition, in the text's order. Small lights are names you have opened (${seen}). This sky ranks no one.</p></div>
      </section>
      <section class="block"><h2>Expeditions</h2>
        <div class="cards">${INDEX.expeditions.map(x => `
          <article class="card">
            <p class="kicker">${esc(x.era)} · ${esc(x.anchor)}</p>
            <h3>${esc(x.title)}</h3>
            <p class="meta">${x.dated ? "Dated in the text: one sky per candidate lunation." : "No date in the text: the ground only."} ${x.people} names in the text's account.</p>
            ${progress(x)}
            <div class="go"><a class="btn primary" href="#x-${x.slug}">Enter</a><a class="btn" href="text/${x.slug}.html">Plain version</a></div>
          </article>`).join("")}</div>
      </section>
      <section class="block"><h2>Other ways in</h2>
        <div class="doors">
          <div class="door"><h3>Remember</h3><p>${due ? `${due} question${due > 1 ? "s" : ""} due now.` : `Nothing due. Next: ${fmtDue(M.nextDue())}.`} Spaced review, kept on this device.</p><a class="btn" href="#review">Review</a></div>
          <div class="door"><h3>Teach a halaqa</h3><p>One big screen for a room: arrow keys step through an expedition while you talk.</p><a class="btn" href="#halaqa-badr">Start with Badr</a></div>
          <div class="door"><h3>Review desk</h3><p>For scholars: each expedition's claims as one batch, flags first, decisions exported in the review importer's format.</p><a class="btn" href="#desk">Open the desk</a></div>
          <div class="door"><h3>Text and channels</h3><p>Every expedition as a plain page for any phone or printer, and as seven WhatsApp messages for a teacher to send.</p><a class="btn" href="text/index.html">Plain versions</a> <a class="btn" href="#about">Channel packs</a></div>
        </div>
      </section>
    </div>`;
    const cv = $("#skyline");
    const drawSkyline = () => {
      const dpr = Math.min(2, window.devicePixelRatio || 1), w = cv.clientWidth, h = cv.clientHeight;
      cv.width = w * dpr; cv.height = h * dpr; const x = cv.getContext("2d"); x.setTransform(dpr, 0, 0, dpr, 0, 0);
      for (const name of Object.keys(M.state.seen)) {
        let s = 2166136261; for (const ch of name) { s ^= ch.codePointAt(0); s = Math.imul(s, 16777619) >>> 0; }
        const px = (s % 1000) / 1000 * (w - 12) + 6, py = ((s >>> 10) % 1000) / 1000 * (h - 60) + 8;
        x.fillStyle = "rgba(255,244,220,0.75)"; x.beginPath(); x.arc(px, py, 1.4, 0, 7); x.fill();
      }
      const n = INDEX.expeditions.length;
      INDEX.expeditions.forEach((e, i) => {
        const t = (i + 0.5) / n, px = 24 + t * (w - 48), py = h - 40 - Math.sin(t * Math.PI) * (h * 0.45);
        const g = x.createRadialGradient(px, py, 0, px, py, 16); g.addColorStop(0, "rgba(255,240,205,1)"); g.addColorStop(1, "rgba(255,240,205,0)");
        x.fillStyle = g; x.beginPath(); x.arc(px, py, 16, 0, 7); x.fill();
        x.fillStyle = "#e8edf5"; x.font = "12px system-ui, sans-serif"; const tw = x.measureText(e.short).width;
        x.fillText(e.short, Math.min(w - tw - 6, Math.max(6, px - tw / 2)), py + 28);
      });
    };
    drawSkyline(); window.addEventListener("resize", drawSkyline, { once: true });
  }

  /* ---------------- an expedition ---------------- */
  function stepsOf(X) {
    return [{ id: "enter", label: "Enter" }, ...X.cases.map((c, i) => ({ id: "case" + i, label: c.title, c })),
      { id: "people", label: "Who was there" }, { id: "explain", label: "Explain" }, { id: "remember", label: "Remember" }, { id: "connect", label: "Connect" }];
  }
  async function expedition(slug, step, halaqa) {
    const X = await load(slug);
    STARS = STARS || (await load("stars")).stars;
    const steps = stepsOf(X);
    step = Math.min(Math.max(0, step), steps.length - 1);
    M.step(slug, step);
    const base = halaqa ? `halaqa-${slug}` : `x-${slug}`;
    const visited = M.state.steps[slug] || [];
    view.innerHTML = `${halaqa ? `<div class="halaqa-bar"><b>${esc(X.title)}</b><span class="muted">· ${step + 1} of ${steps.length}: ${esc(steps[step].label)}</span>
        <span class="row" style="margin-inline-start:auto"><button id="h-prev">← Back</button><button id="h-next" class="primary">Next →</button><a class="btn" href="#x-${slug}-${step}">Leave the room view</a></span></div>` : ""}
      <div class="wrap">
      ${halaqa ? "" : `<div class="xhead"><div><p class="kicker">${esc(X.era)} · ${esc(X.world.anchor.name)}</p><h1>${esc(X.title)}</h1></div>
        <div class="row"><a class="btn" href="text/${slug}.html">Plain version</a><a class="btn" href="#halaqa-${slug}-${step}">Room view</a><a class="btn" href="#desk-${slug}">Review batch (${X.review.count})</a></div></div>
      <ol class="steps">${steps.map((s, i) => `<li><a href="#${base}-${i}" ${i === step ? 'aria-current="step"' : ""} class="${visited.includes(i) && i !== step ? "done" : ""}">${esc(s.label)}</a></li>`).join("")}</ol>`}
      <div id="stepbody"></div>
      <div class="pager">${step > 0 ? `<a class="btn" href="#${base}-${step - 1}">← ${esc(steps[step - 1].label)}</a>` : "<span></span>"}
        ${step < steps.length - 1 ? `<a class="btn primary" href="#${base}-${step + 1}">${esc(steps[step + 1].label)} →</a>` : `<a class="btn primary" href="#">All expeditions</a>`}</div>
      </div>`;
    const body = $("#stepbody"), s = steps[step];
    if (s.id === "enter") enter(X, body);
    else if (s.c) ({ count: caseCount, date: caseDate, moment: caseMoment, route: caseRoute })[s.c.type](X, s.c, body, step);
    else if (s.id === "people") people(X, body);
    else if (s.id === "explain") explain(X, body);
    else if (s.id === "remember") remember(X, body);
    else if (s.id === "connect") connect(X, body);
    if (halaqa) {
      const go = d => { const i = Math.min(steps.length - 1, Math.max(0, step + d)); if (i !== step) location.hash = `${base}-${i}`; };
      $("#h-prev").onclick = () => go(-1); $("#h-next").onclick = () => go(1);
      document.onkeydown = e => { if (e.target.closest("input, textarea, canvas")) return; if (e.key === "ArrowRight" || e.key === "PageDown") go(1); if (e.key === "ArrowLeft" || e.key === "PageUp") go(-1); };
      try { bc = bc || new BroadcastChannel("marsad-halaqa"); bc.postMessage({ slug, step }); } catch (e) { /* no BroadcastChannel: one screen only */ }
    } else document.onkeydown = null;
  }

  function enter(X, body) {
    const sky = X.sky, dated = !!sky.candidates;
    const dateCase = X.cases.find(c => c.type === "date"), moment = X.cases.find(c => c.type === "moment");
    const notice = X.notice || [];
    body.innerHTML = `<div class="xgrid"><div id="worldhost"></div><div class="side">
      <div class="panel"><h3 style="margin-top:0">What the source says</h3>
        ${dated ? (dateCase ? dateCase.claims.map(k => prov("attested", `${esc(k.gloss)}<small>Claim ${esc(k.id)} · ${esc(X.source.work)}, section ${k.section}, ${esc(k.page)}</small>`, "div", 'class="fact"')).join("")
          : prov("attested", `“${esc(sky.text_en)}” <span lang="ar" dir="rtl">(${esc(sky.text_ar)})</span><small>${esc(X.source.work)}, ${esc(sky.page)}. In the passage, not yet a dated claim. English: AI draft.</small>`, "div", 'class="fact"'))
          : prov("schematic", esc(sky.none), "div", 'class="fact"')}
        ${prov("located", `${esc(X.world.anchor.name)}<small>${esc(X.world.anchor.source)}. Proposed.</small>`, "div", 'class="fact"')}
      </div>
      ${guide(`${esc(notice[0] || "What do you expect to see here?")}<label class="sr-only" for="guess">Your guess</label><textarea id="guess" placeholder="Your guess, before you look">${esc(M.note(X.slug + ":guess"))}</textarea><div class="row" style="margin-top:6px"><button id="reveal" class="primary">See what is computed</button></div>`)}
      <div class="panel" id="computed" hidden><h3 style="margin-top:0">What is computed</h3><div id="comp"></div></div>
      ${notice[1] ? guide(esc(notice[1])) : ""}
    </div></div>`;
    world = World($("#worldhost"), X, STARS, { onCandidate: () => fill() });
    if (lensOn) world.lens(true);
    const jump = M.pick(X.slug + ":jump"); if (jump != null && dated) { world.setCandidate(jump.c); world.jumpTo(jump.ut); M.pick(X.slug + ":jump", null); }
    function fill() {
      const L = X.world.labels.filter(l => !l.anchor);
      let html = "";
      if (dated) {
        const c = sky.candidates[world ? world.candidate : 1];
        html += prov("computed", `If the month was ${CAND[c.key]}, the day was <b>${esc(c.day)}</b> (Julian). The moon was <b>${c.moon_illuminated_pct.toFixed(0)}% lit</b>${c.moonrise_minutes_after_sunset != null && sky.scene !== "forenoon" ? `, rising ${c.moonrise_minutes_after_sunset >= 0 ? `about ${(c.moonrise_minutes_after_sunset / 60).toFixed(1)} hours after sunset` : "before sunset"}` : ""}.<small>${esc(sky.rule)}</small>`, "div", 'class="fact"');
        if (sky.scene === "forenoon" && c.sun_near_height_ut) html += prov("computed", `The sun stood at nine-tenths of its noon height (${c.sun_noon_altitude.toFixed(0)}°) by about <b>${localTime(c.sun_near_height_ut, c.local_offset_minutes)}</b> local solar time.<small>One way to read “the sun had nearly reached its height”. A reading, not a measurement in the text.</small>`, "div", 'class="fact"');
        if (moment) { const k = moment.candidates.find(m => m.key === c.key); html += prov("computed", `A third of the night had passed at about <b>${localTime(k.moment_ut, k.local_offset_minutes)}</b>. The moon then stood <b>${k.moon_alt.toFixed(0)}°</b> up.`, "div", 'class="fact"'); }
        if (dateCase) { const hit = dateCase.candidates.filter(k => k.match); html += prov("computed", hit.length ? `One candidate falls on a ${esc(dateCase.weekday_text)}: ${esc(hit[0].day)}.` : `No candidate falls on a ${esc(dateCase.weekday_text)}, the weekday the text gives.`, "div", 'class="fact"'); }
      }
      html += L.map(l => prov("computed", `${esc(l.name)}: ${Math.round(l.km)} km to the ${esc(l.compass)} (bearing ${Math.round(l.deg)}°).<small>Straight line between gazetteer points; not a route.</small>`, "div", 'class="fact"')).join("");
      html += prov("computed", `Ground: present-day elevation, ${X.world.terrain.size_km.toFixed(0)} km square, heights exaggerated 2.5 times. Modern roads and buildings are not drawn.`, "div", 'class="fact"');
      $("#comp").innerHTML = html;
    }
    fill();
    if (M.note(X.slug + ":guess")) $("#computed").hidden = false;
    $("#reveal").onclick = () => { M.note(X.slug + ":guess", $("#guess").value); $("#computed").hidden = false; $("#computed").scrollIntoView({ behavior: "smooth", block: "nearest" }); };
  }

  function dotsField(X, L, groups) {
    const blocks = groups ? groups.concat(["After the last clan total"]) : [null];
    return `<div class="vlegend"><span><i style="background:var(--v-ishq)"></i>${VOICE.ishq}</span><span><i style="background:var(--v-hish)"></i>${VOICE.hish}</span><span><i style="background:var(--v-none)"></i>${VOICE.none}</span><span><i style="background:transparent;box-shadow:0 0 0 1.5px #fff"></i>counted without being present</span>${groups ? `<span><i style="background:var(--muted);border-radius:2px"></i>in two clan lists</span>` : ""}</div>
      <div class="row" style="margin-block:10px" role="group" aria-label="Filter names">${["all", "ishq", "hish", "none"].map(f => `<button class="flt" data-f="${f}" aria-pressed="${f === "all"}">${{ all: "All names", ishq: "Ibn Isḥāq's voice only", hish: "Ibn Hishām's additions", none: "Untagged" }[f]}</button>`).join("")}</div>
      <div class="field" data-prov="attested">${blocks.map(g => {
        const rows = L.people.map((r, i) => [r, i]).filter(([r]) => !groups || (g === "After the last clan total" ? !r.groups.length : r.groups[0] === g));
        if (!rows.length) return "";
        return `<div class="block"><h4><span>${esc(g || L.what)}</span><span class="count" data-g="${esc(g || "")}"></span></h4><div class="dots">${rows.map(([r, i]) =>
          `<button class="dot${M.state.seen[r.name] ? " seen" : ""}" data-v="${r.voice}" data-s="${r.share ? 1 : 0}" ${r.groups && r.groups.length > 1 ? "data-twice" : ""} data-i="${i}" data-g="${esc(g || "")}" aria-label="${esc(r.name)}: ${VOICE[r.voice]}" title="${esc(r.name)}"></button>`).join("")}</div></div>`;
      }).join("")}</div>
      <div class="panel" id="person" aria-live="polite"><span class="muted">Open a dot to read its claim.</span></div>`;
  }
  function wireDots(X, L, root, onFilter) {
    const filter = f => {
      $$(".flt", root).forEach(b => b.setAttribute("aria-pressed", b.dataset.f === f));
      $$(".dot", root).forEach(d => d.classList.toggle("off", f !== "all" && d.dataset.v !== f));
      $$(".count", root).forEach(c => { const n = $$(`.dot[data-g="${CSS.escape(c.dataset.g)}"]`, root).filter(d => !d.classList.contains("off")).length; c.textContent = `${n} shown`; });
      onFilter && onFilter(f);
    };
    $$(".flt", root).forEach(b => b.onclick = () => filter(b.dataset.f));
    $$(".dot", root).forEach(b => b.onclick = () => {
      const r = L.people[+b.dataset.i]; M.see(r.name, X.slug); b.classList.add("seen");
      $("#person", root).innerHTML = prov("attested", `<b>${esc(r.name)}</b>${r.groups ? ` · ${esc(r.groups.join(" and ") || "after the last clan total")}` : ""} · ${VOICE[r.voice]}${r.share ? " · <b>counted without being present</b>" : ""}
        <small>${r.gloss ? esc(r.gloss) + " " : ""}Claim ${esc(r.claim)} · ${esc(X.source.work)}, section ${r.section}, ${esc(r.page)}. Proposed, not reviewed.</small>`, "div", 'class="fact"');
    });
    filter("all");
  }

  function caseCount(X, c, body, step) {
    const key = `${X.slug}:case${step}`, L = c.lists[c.lists.length - 1], groups = c.groups;
    const allMatch = c.lists.every(l => l.found === l.stated);
    const listsText = c.lists.map(l => `${esc(l.what)}: <b>${l.stated}</b> <span class="muted">(${esc(l.total_page)})</span>`).join("<br>");
    body.innerHTML = `<div class="stack">
      ${groups ? `<div class="panel"><h3 style="margin-top:0">1 · Do the totals agree with each other?</h3>
        <p data-prov="attested">${c.lists.slice(0, -1).map(l => `<b>${l.stated}</b> ${esc(groups[c.lists.indexOf(l)])}`).join(", ")}. Then a grand total: <b>${L.stated}</b>.</p>
        ${guide("Before anything else: add them. Does the author's own arithmetic hold?")}
        <div class="row"><label for="sum">${c.lists.slice(0, -1).map(l => l.stated).join(" + ")} =</label><input id="sum" type="number" inputmode="numeric"><button id="sum-go" class="primary">Check</button></div>
        <div class="reveal" id="sum-r" hidden></div></div>` : ""}
      <div class="panel" id="p-pred" ${groups ? "hidden" : ""}><h3 style="margin-top:0">${groups ? "2 · " : ""}Predict before you look</h3>
        <p data-prov="attested">The text states: <br>${listsText}</p>
        ${guide(`When a machine reads the names in ${c.lists.length > 1 ? "these lists" : "this list"} one by one, will it find more names, fewer, or exactly ${c.lists.length > 1 ? "the stated totals" : L.stated}?`)}
        <div class="choices" id="pred">${["More names than stated", "Fewer names than stated", "Exactly the stated number"].map((o, i) => `<label><input type="radio" name="pred" value="${i}"> ${o}</label>`).join("")}</div>
        <button id="pred-go" class="primary">Lock in my prediction</button></div>
      <div class="panel" id="p-look" hidden><h3 style="margin-top:0">${groups ? "3 · " : ""}Look at every name</h3>
        <div class="tablewrap"><table data-prov="computed"><thead><tr><th>List</th><th class="n">Text says</th><th class="n">Names found</th><th class="n">Ibn Isḥāq's voice</th><th class="n">+ untagged</th><th class="n">Ibn Hishām's</th></tr></thead><tbody>
        ${c.lists.map(l => { const ok = (n) => n === l.stated ? "ok" : "bad"; return `<tr><td>${esc(l.what)}</td><td class="n">${l.stated}</td><td class="n ${ok(l.found)}">${l.found}</td><td class="n ${ok(l.voices.ishq)}">${l.voices.ishq}</td><td class="n ${ok(l.voices.ishq + l.voices.none)}">${l.voices.ishq + l.voices.none}</td><td class="n">${l.voices.hish}</td></tr>`; }).join("")}
        </tbody></table></div>
        ${c.lists.filter(l => l.people.length).map(l => dotsField(X, l, groups)).join("")}
        ${groups ? `<p class="muted" data-prov="computed">Two more things the reading found: <b>${c.twice.length}</b> names sit in two clan lists at once (${c.twice.map(esc).join(", ")}), and <b>${c.after_totals.length}</b> come after the last clan total, so belong to no clan's count.</p>` : ""}
      </div>
      <div class="panel" id="p-mean" hidden><h3 style="margin-top:0">${groups ? "4 · " : ""}What does it mean?</h3>
        ${allMatch ? guide("Every list agrees with its total. Does that prove the list is right?") : guide("The list and its total disagree. Which layer could the difference live in?")}
        <div class="choices" id="layers">${(allMatch
          ? ["Yes: agreement settles it", "It is strong evidence, but every name still needs its reading checked", "No: agreement means nothing"]
          : ["The event itself: we cannot know who was there", "The text: an editor, a copyist, or the printed edition", "Our reading of the text: the extraction missed or mis-tagged names", "Possibly the text and our reading, and only a reviewer with the passage can tell"]).map((o, i) => `<label><input type="radio" name="layer" value="${i}"> ${o}</label>`).join("")}</div>
        <button id="layer-go" class="primary">Answer</button>
        <div class="reveal" id="mean-r" hidden>${allMatch
          ? `<p><b>Strong evidence, not proof.</b> The count agrees, so no name is obviously missing or extra. But ${L.voices.none} names in this list have no voice tag yet, and agreement could hide one missed name and one extra. A reviewer still reads each one.</p><p class="muted">Agreement is evidence too. At Badr the same check disagreed, and the difference taught as much.</p>`
          : `<p><b>The last answer is the honest one.</b> ${groups ? "The totals agree with each other, so the author's arithmetic holds. " : ""}Names in Ibn Hishām's voice are the editor's additions, which the text marks. A shortfall is most likely in our own machine reading, which tags voice imperfectly and may miss names. Only a reviewer with the Arabic passage beside them can settle each one.</p>
            <p>That is why this list sits in the review queue as a mismatch, and why the graph never "corrects" the source to make the numbers fit.</p><p class="muted">Three layers can disagree: what happened, the text that reports it, and our reading of the text. Good history keeps them apart.</p>`}</div>
      </div></div>`;
    const showFrom = id => { const ids = ["p-pred", "p-look", "p-mean"]; ids.slice(0, ids.indexOf(id) + 1).forEach(i => $("#" + i).hidden = false); };
    if (groups) $("#sum-go").onclick = () => {
      const want = c.group_sum, v = +$("#sum").value; $("#sum-r").hidden = false;
      $("#sum-r").innerHTML = `<p>${v === want ? `<span class="ok">Yes: ${want}.</span>` : `Not quite: the sum is <b>${want}</b>.`} ${want === L.stated ? "The clan totals and the grand total agree. Whatever goes wrong next, it is not the author's arithmetic." : "The clan totals and the grand total do not agree."}</p>`;
      showFrom("p-pred");
    };
    $("#pred-go").onclick = () => {
      const p = $("input[name=pred]:checked"); M.pick(key + ":pred", p ? +p.value : null);
      const truth = L.found > L.stated ? 0 : L.found < L.stated ? 1 : 2;
      $$("#pred label").forEach((l, i) => l.classList.toggle("right", i === truth));
      showFrom("p-look"); $$(".field", body).forEach((f, i) => wireDots(X, c.lists.filter(l => l.people.length)[i], f.parentElement));
      $("#p-look").scrollIntoView({ behavior: "smooth", block: "start" }); showFrom("p-mean");
    };
    $("#layer-go").onclick = () => {
      $("#mean-r").hidden = false; const right = allMatch ? 1 : 3;
      $$("#layers label").forEach((l, i) => l.classList.toggle("right", i === right));
    };
    if (M.pick(key + ":pred") != null) { showFrom("p-mean"); $$(".field", body).forEach((f, i) => wireDots(X, c.lists.filter(l => l.people.length)[i], f.parentElement)); }
  }

  function caseDate(X, c, body, step) {
    const key = `${X.slug}:case${step}`;
    body.innerHTML = `<div class="stack"><div class="panel">
      <h3 style="margin-top:0">What the text says</h3>
      ${c.claims.map(k => prov("attested", `${esc(k.gloss)}<small>Claim ${esc(k.id)} · section ${k.section}, ${esc(k.page)} · ${VOICE[k.voice]}</small>`, "div", 'class="fact"')).join("")}
      ${prov("attested", `“${esc(c.text_en)}” <span lang="ar" dir="rtl">(${esc(c.text_ar)})</span><small>${esc(c.page)}. English: AI draft.</small>`, "div", 'class="fact"')}
      ${guide(`The text gives a weekday: <b>${esc(c.weekday_text)}</b>. A lunar date and a weekday together can be checked against the real moon. Predict: will any computed lunation fall on a ${esc(c.weekday_text)}?`)}
      <div class="choices" id="pred">${["Yes, at least one will", "No, none will"].map((o, i) => `<label><input type="radio" name="pred" value="${i}"> ${o}</label>`).join("")}</div>
      <button id="go" class="primary">Check against the moon</button>
      <div class="reveal" id="r" hidden>
        <div class="tablewrap"><table data-prov="computed"><thead><tr><th>If the month was</th><th>Conjunction</th><th>First crescent evening</th><th>The day</th><th>Weekday matches?</th></tr></thead><tbody>
        ${c.candidates.map(k => `<tr><td>${esc(CAND[k.key])}</td><td>${esc(k.conjunction)}</td><td>${esc(k.crescent_evening)}</td><td><b>${esc(k.day)}</b></td><td class="${k.match ? "ok" : "bad"}">${k.match ? "yes" : "no"}</td></tr>`).join("")}</tbody></table></div>
        <p class="muted">${esc(c.rule)} The modern tabular calendar points to ${esc(c.tabular)}. All dates are Julian.</p>
        <p>${c.candidates.some(k => k.match) ? `<b>One candidate agrees.</b> That is consistent with the text under this simple rule. It is not proof: the rule is a stand-in for real sighting, and the calendar of those years is itself debated.`
          : `<b>None agrees.</b> The text's weekday and the computed weekdays do not meet under this rule. Perhaps the crescent was seen a day later than the rule assumes, perhaps the calendar was still being intercalated, perhaps a report is off by a day. This page does not decide. It is the kind of question that goes to the scholars.`}</p>
        <div class="row">${c.candidates.map((k, i) => `<button data-c="${i}">See the sky of ${esc(CAND[k.key])}</button>`).join("")}</div>
      </div></div></div>`;
    const reveal = () => { $("#r").hidden = false; const hit = c.candidates.some(k => k.match) ? 0 : 1; $$("#pred label").forEach((l, i) => l.classList.toggle("right", i === hit)); };
    $("#go").onclick = () => { const p = $("input[name=pred]:checked"); M.pick(key + ":pred", p ? +p.value : -1); reveal(); };
    $$("[data-c]", body).forEach(b => b.onclick = () => { M.pick(X.slug + ":jump", { c: +b.dataset.c, ut: X.sky.candidates[+b.dataset.c].sunset_ut }); location.hash = `x-${X.slug}-0`; });
    if (M.pick(key + ":pred") != null) reveal();
  }

  function caseMoment(X, c, body, step) {
    const key = `${X.slug}:case${step}`;
    body.innerHTML = `<div class="stack"><div class="panel">
      <h3 style="margin-top:0">What the text says</h3>
      ${prov("attested", `“${esc(c.text_en)}”<small>${esc(X.source.work)}, ${esc(c.page)}. The narrator speaks in the first person. English: AI draft.</small>`, "div", 'class="fact"')}
      ${prov("attested", `The appointment: “${esc(c.date_text_en)}”<small>${esc(c.date_page)}. Which night exactly is not pinned down; shown: the night after the twelfth.</small>`, "div", 'class="fact"')}
      ${guide("They slipped out in secret, a third of the way into the night. Predict: what was the moon doing then?")}
      <div class="choices" id="pred">${["High and nearly full", "A thin crescent, low in the west", "It had already set"].map((o, i) => `<label><input type="radio" name="pred" value="${i}"> ${o}</label>`).join("")}</div>
      <button id="go" class="primary">Compute it</button>
      <div class="reveal" id="r" hidden>
        <div class="tablewrap"><table data-prov="computed"><thead><tr><th>If the month was</th><th>Night of</th><th>Night length</th><th>A third gone</th><th>Moon up</th><th>Lit</th></tr></thead><tbody>
        ${c.candidates.map(k => `<tr><td>${esc(CAND[k.key])}</td><td>${esc(k.day)}</td><td>${k.night_hours.toFixed(1)} h</td><td>${localTime(k.moment_ut, k.local_offset_minutes)}</td><td>${k.moon_alt.toFixed(0)}°</td><td>${k.illuminated.toFixed(0)}%</td></tr>`).join("")}</tbody></table></div>
        <p>${c.candidates.every(k => k.moon_alt > 10 && k.illuminated > 80)
          ? "Under every candidate the moon was high and nearly full. Whatever kept them hidden, it was not darkness. The text says only that they went in secret; the sky adds what it was like to do so."
          : "The candidates disagree about the moon, so the sky cannot say how dark it was. That depends on a date the text does not pin down."}</p>
        <button id="see" class="primary">Stand there at that moment</button>
      </div></div></div>`;
    const reveal = () => { $("#r").hidden = false; $$("#pred label").forEach((l, i) => l.classList.toggle("right", i === 0)); };
    $("#go").onclick = () => { const p = $("input[name=pred]:checked"); M.pick(key + ":pred", p ? +p.value : -1); reveal(); };
    $("#see").onclick = () => { const i = c.candidates.findIndex(k => k.key === "tabular"); M.pick(X.slug + ":jump", { c: i, ut: c.candidates[i].moment_ut }); location.hash = `x-${X.slug}-0`; };
    if (M.pick(key + ":pred") != null) reveal();
  }

  function caseRoute(X, c, body, step) {
    const key = `${X.slug}:case${step}`;
    body.innerHTML = `<div class="stack"><div class="panel">
      <h3 style="margin-top:0">What the text says</h3>
      ${prov("attested", `The guide took them by a road the text names stage by stage: <b>${c.named}</b> names from below Makkah to Qubāʾ.<small>${esc(X.source.work)}, ${esc(c.page)}. Names as written; English forms are AI drafts. Ibn Hishām gives other spellings for some.</small>`, "div", 'class="fact"')}
      ${guide(`Fourteen centuries later, how many of these ${c.named} names do you think anyone can still put on a map? Guess a number.`)}
      <div class="row"><label for="n">My guess:</label><input id="n" type="number" inputmode="numeric" min="0" max="${c.named}"><button id="go" class="primary">Show the road</button></div>
      <div class="reveal" id="r" hidden>
        <p><b>${c.located}</b> of ${c.named} have a gazetteer point here; the rest are named, not located. <b>${c.with_claims}</b> are recorded as claims so far, which is a gap in our own extraction, not in the text.</p>
        <div class="stage" style="aspect-ratio: 4 / 5"><canvas id="routemap" class="mapcv" data-redraw aria-label="The located stages of the road on a map; the dashed line joins them in order and is not the road"></canvas></div>
        <p class="muted" data-prov="schematic">The dashed line only joins the located points in the text's order. It is not the road: the real road ran between them through places no one has placed.</p>
        <p data-prov="computed">Thawr to Qubāʾ in a straight line: <b>${Math.round(c.straight_km)} km</b>. Any road is longer.</p>
        <ol class="stages">${c.stages.map(s => `<li><span class="num quiet">${s.n}</span><span>${esc(s.en)} <span class="ar" lang="ar" dir="rtl">${esc(s.ar)}</span>${s.variant ? `<br><span class="quiet" style="font-size:.82rem">${esc(s.variant)}</span>` : ""}${s.voice ? `<br><span class="quiet" style="font-size:.82rem">this stage is in ${esc(s.voice)}'s voice</span>` : ""}</span>
          <span>${s.lat != null ? chip("located") : `<span class="chip plain">${s.region ? "a region" : "not located"}</span>`}${s.claim ? ` <span class="chip plain" title="${esc(s.claim.gloss)}">claim</span>` : ""}</span></li>`).join("")}</ol>
      </div></div></div>`;
    const cv = $("#routemap");
    const draw = () => drawMap(cv, { bbox: c.bbox, land: c.land, points: [Object.assign({ big: true }, c.start)].concat(c.stages.filter(s => s.lat != null).map(s => ({ name: s.en.replace(/^below /, ""), lat: s.lat, lon: s.lon }))) },
      { lens: lensOn, route: [c.start].concat(c.stages) });
    cv.addEventListener("redraw", draw);
    const reveal = () => { $("#r").hidden = false; requestAnimationFrame(draw); };
    $("#go").onclick = () => { M.pick(key + ":pred", +$("#n").value); reveal(); };
    if (M.pick(key + ":pred") != null) reveal();
  }

  function people(X, body) {
    const P = X.people, total = P.with + P.against + P.unrecorded;
    const pct = n => (n / Math.max(1, total) * 100).toFixed(1) + "%";
    body.innerHTML = `<div class="panel">
      <p data-prov="attested">The text places <b>${total}</b> named people at this event: <b>${P.with}</b> with the Prophet ﷺ, <b>${P.against}</b> against him, and <b>${P.unrecorded}</b> with no side recorded.</p>
      <div class="bar" aria-hidden="true"><span style="width:${pct(P.with)};background:var(--p-attested)"></span><span style="width:${pct(P.unrecorded)};background:var(--quiet)"></span><span style="width:${pct(P.against)};background:var(--dark-mark)"></span></div>
      <p class="muted">No one is drawn. Opponents are listed last, as dark marks, never as lights. A side is shown only where a claim records it; nobody's side is guessed. Honorifics wait until a scholar accepts the claim they rest on.</p>
      <div class="row" role="group" aria-label="Filter people" style="margin-block:8px">${["all", "with", "not recorded", "against"].map(f => `<button class="pf" data-f="${f}" aria-pressed="${f === "all"}">${{ all: "Everyone", with: "With the Prophet ﷺ", "not recorded": "No side recorded", against: "Against" }[f]}</button>`).join("")}</div>
      <ul class="people" id="plist"></ul></div>`;
    const list = f => {
      $$(".pf", body).forEach(b => b.setAttribute("aria-pressed", b.dataset.f === f));
      $("#plist").innerHTML = P.rows.filter(r => f === "all" || r.side === f).map(r => `<li class="${r.side === "against" ? "against" : ""}"><button class="linkish" data-n="${esc(r.name)}" style="all:unset;cursor:pointer">${esc(r.name)}</button>${r.roles.includes("died") ? ' <span class="quiet">· died</span>' : ""}${r.roles.includes("absent") ? ' <span class="quiet">· absent</span>' : ""}</li>`).join("");
      $$("#plist button", body).forEach(b => b.onclick = () => { M.see(b.dataset.n, X.slug); b.style.textDecoration = "underline"; });
    };
    $$(".pf", body).forEach(b => b.onclick = () => list(b.dataset.f));
    list("all");
  }

  function explain(X, body) {
    const k = X.slug + ":explain";
    body.innerHTML = `<div class="panel">${guide(`In two or three sentences, as if to a friend: what did standing in this place and checking the text show you that a summary would not?`)}
      <label class="sr-only" for="ex">Your explanation</label><textarea id="ex" placeholder="Write it here…">${esc(M.note(k))}</textarea>
      <div class="row" style="margin-top:8px"><button id="sv" class="primary">Save</button><span id="ok" class="muted"></span></div>
      <p class="muted" style="margin-top:10px">It stays on this device. Explaining in your own words is one of the surest ways to keep what you learned.</p></div>`;
    $("#sv").onclick = () => { M.note(k, $("#ex").value); $("#ok").textContent = "Saved on this device."; };
  }

  function quiz(qs, host, done) {
    host.innerHTML = qs.map((q, i) => `<div class="q" data-prov="${q.class}"><p><b>${i + 1}.</b> ${esc(q.q)}</p>${q.kind === "num"
      ? `<input type="number" id="q${i}" aria-label="Answer ${i + 1}">`
      : `<div class="choices">${q.opts.map((o, j) => `<label><input type="radio" name="q${i}" value="${j}"> ${esc(o)}</label>`).join("")}</div>`}<p class="muted" id="qa${i}" aria-live="polite"></p></div>`).join("")
      + `<button class="primary" id="qgo">Check my answers</button> <span class="muted" id="qs"></span>`;
    $("#qgo", host).onclick = () => {
      let right = 0;
      qs.forEach((q, i) => {
        const v = q.kind === "num" ? +$("#q" + i, host).value : +(($(`input[name=q${i}]:checked`, host) || {}).value ?? -1);
        const ok = v === q.a; right += ok;
        const card = M.grade(q.id, ok ? 3 : 1);
        $("#qa" + i, host).innerHTML = `${ok ? '<span class="ok">Right.</span>' : `<span class="bad">Not this time:</span> ${esc(q.kind === "num" ? q.a : q.opts[q.a])}.`} ${esc(q.why)} <span class="quiet">Next: ${fmtDue(card.due)}.</span>`;
      });
      $("#qs", host).textContent = `${right} of ${qs.length}.`;
      done && done();
    };
  }
  function remember(X, body) {
    body.innerHTML = `<div class="panel"><p class="muted">Answer from memory. Each question comes back on a schedule: sooner if you missed it, later if you knew it. Nothing leaves this device.</p><div id="quiz"></div></div>`;
    quiz(X.questions, $("#quiz"));
  }

  function connect(X, body) {
    const names = Object.fromEntries(INDEX.expeditions.map(e => [e.slug, e]));
    body.innerHTML = `<div class="panel"><p data-prov="computed">${X.connections.length} people this text places here are also placed at another expedition's event. Joined by machine from attested claims, so each link is only as good as the two claims under it.</p>
      ${X.connections.length ? `<div class="tablewrap"><table><thead><tr><th>Name</th><th>Also at</th></tr></thead><tbody>${X.connections.slice(0, 60).map(r => `<tr><td>${esc(r.name)}</td><td>${r.also.map(s => `<a href="#x-${s}">${esc(names[s].short)}</a>`).join(", ")}</td></tr>`).join("")}</tbody></table></div>` : ""}
      ${guide("Pick one name you met here. Where do you think you will meet them next?")}
      <div class="row">${INDEX.expeditions.filter(e => e.slug !== X.slug).map(e => `<a class="btn" href="#x-${e.slug}">${esc(e.title)}</a>`).join("")}</div></div>`;
  }

  /* ---------------- review ---------------- */
  async function review() {
    const all = await Promise.all(INDEX.expeditions.map(e => load(e.slug)));
    const byId = {}; all.forEach(X => X.questions.forEach(q => byId[q.id] = Object.assign({ from: X.short }, q)));
    const due = M.due().filter(id => byId[id]).map(id => byId[id]);
    const total = Object.keys(M.state.cards).length;
    view.innerHTML = `<div class="wrap"><p class="kicker">Remember</p><h1>Questions due</h1>
      <p class="muted">${total ? `${total} questions on your schedule; ${due.length} due now. Next after these: ${fmtDue(M.nextDue())}.` : "Nothing on your schedule yet: answer the Remember step of any expedition and its questions start coming back here."}</p>
      <div class="panel" id="dq">${due.length ? "" : '<p class="muted">Nothing due right now.</p>'}</div>
      <section class="block"><h2>Your sky</h2><canvas id="mysky" aria-label="A light for each name you have opened"></canvas><p class="muted">${Object.keys(M.state.seen).length} names opened. It records what you looked at; it ranks no one.</p></section>
      <section class="block"><h2>Your memory, on this device</h2>
        <p class="muted">${M.ok ? "Saved in this browser only." : "This browser is not keeping anything (private mode or blocked storage): your progress will be lost when you leave."} Copy it to move it to another device.</p>
        <div class="row"><button id="exp">Show my memory file</button><button id="imp">Load a memory file</button><button id="wipe">Erase everything</button></div>
        <textarea id="memtext" class="export" hidden></textarea><p id="memmsg" class="muted"></p></section></div>`;
    if (due.length) quiz(due, $("#dq"));
    const cv = $("#mysky"), dpr = Math.min(2, window.devicePixelRatio || 1); cv.width = cv.clientWidth * dpr; cv.height = cv.clientHeight * dpr;
    const x = cv.getContext("2d"); x.setTransform(dpr, 0, 0, dpr, 0, 0);
    for (const name of Object.keys(M.state.seen)) {
      let s = 2166136261; for (const ch of name) { s ^= ch.codePointAt(0); s = Math.imul(s, 16777619) >>> 0; }
      const px = (s % 1000) / 1000 * (cv.clientWidth - 12) + 6, py = ((s >>> 10) % 1000) / 1000 * (cv.clientHeight - 12) + 6;
      const g = x.createRadialGradient(px, py, 0, px, py, 5); g.addColorStop(0, "rgba(255,244,220,1)"); g.addColorStop(1, "rgba(255,244,220,0)"); x.fillStyle = g; x.beginPath(); x.arc(px, py, 5, 0, 7); x.fill();
    }
    const ta = $("#memtext"), msg = $("#memmsg");
    $("#exp").onclick = () => { ta.hidden = false; ta.value = M.export(); ta.select(); try { navigator.clipboard.writeText(ta.value).then(() => msg.textContent = "Copied.", () => msg.textContent = "Selected: copy it now."); } catch (e) { msg.textContent = "Selected: copy it now."; } };
    $("#imp").onclick = () => { if (ta.hidden) { ta.hidden = false; ta.value = ""; msg.textContent = "Paste a memory file into the box, then press Load again."; return; } try { M.import(ta.value); msg.textContent = "Loaded."; route(); } catch (e) { msg.textContent = "That is not a memory file from this app."; } };
    $("#wipe").onclick = () => { if ($("#wipe").dataset.sure) { M.wipe(); route(); } else { $("#wipe").dataset.sure = 1; $("#wipe").textContent = "Press again to erase everything"; } };
  }

  /* ---------------- the review desk ---------------- */
  async function desk(slug) {
    if (!slug) {
      view.innerHTML = `<div class="wrap"><p class="kicker">For scholars and editors</p><h1>Review desk</h1>
        <p class="muted" style="max-inline-size:44rem">Each expedition's claims form one batch, ordered by how often learners will meet them, then by the number of machine flags. A flag is a reason to look, never a verdict. Decisions are kept on this device and exported in the format <code>review/import_decisions.py</code> reads (<code>marsad-review-decisions</code>, version 1). Read each claim beside its Arabic passage with <code>ingest/ibn_hisham.py review</code>; the text itself is not shipped here.</p>
        <div class="cards">${INDEX.expeditions.map(e => `<article class="card"><h3>${esc(e.title)}</h3><p class="meta">${e.review.count} claims · ${e.review.flagged} flagged</p><p class="status"><b>${Object.keys(M.state.desk[e.slug] || {}).length}</b> decided on this device</p><div class="go"><a class="btn primary" href="#desk-${e.slug}">Open batch</a></div></article>`).join("")}</div></div>`;
      return;
    }
    const B = await load("review-" + slug);
    let onlyFlagged = false, shown = 40;
    view.innerHTML = `<div class="wrap"><p class="kicker"><a href="#desk">Review desk</a> · batch</p><h1>${esc(B.title)}</h1>
      <p class="muted">${B.count} claims, ${B.flagged} with machine flags. ${esc(B.format_note)}</p>
      <div class="row" style="margin-block:8px"><button id="ff" aria-pressed="false">Flagged only</button><label for="rid">Reviewer ID</label><input id="rid" type="text" placeholder="agt:…" value="${esc(M.reviewer())}" style="inline-size:16em"><button id="ex" class="primary">Export decisions</button></div>
      <textarea id="out" class="export" hidden aria-label="Decision file"></textarea><p id="msg" class="muted"></p>
      <div id="items"></div><button id="more">Show more</button></div>`;
    const draw = () => {
      const items = B.items.filter(it => !onlyFlagged || it.flags.length);
      $("#items").innerHTML = items.slice(0, shown).map(it => {
        const d = M.desk(slug, it.id) || {};
        return `<div class="desk-item" data-id="${esc(it.id)}" data-d="${esc(d.decision || "")}">
          <p class="claim" data-prov="attested">${esc(it.gloss || `${it.subject} — ${it.predicate} — ${it.object}`)}</p>
          <p class="muted" style="font-size:.84rem">${esc(it.subject)} · <i>${esc(it.predicate)}</i> · ${esc(it.object)}<br>Claim ${esc(it.id)} · section ${it.section}, ${esc(it.page)} · ${VOICE[it.voice]}${it.seen_in ? ` · seen in ${it.seen_in} learner step${it.seen_in > 1 ? "s" : ""}` : ""}</p>
          ${it.flags.length ? `<div class="flags">${it.flags.map(f => `<span>${esc(f)}</span>`).join("")}</div>` : ""}
          <div class="row">${["accept", "reject", "needs_discussion"].map(k => `<button data-k="${k}" aria-pressed="${d.decision === k}">${{ accept: "Accept", reject: "Reject", needs_discussion: "Needs discussion" }[k]}</button>`).join("")}
          <input type="text" class="nt" placeholder="Note (required for needs discussion)" value="${esc(d.note || "")}" style="flex:1 1 220px" aria-label="Note"></div></div>`;
      }).join("");
      $("#more").hidden = items.length <= shown;
      $$(".desk-item").forEach(el => {
        const id = el.dataset.id;
        $$("button[data-k]", el).forEach(b => b.onclick = () => {
          const cur = M.desk(slug, id) || {}, k = b.dataset.k;
          if (cur.decision === k) { M.desk(slug, id, null); el.dataset.d = ""; $$("button[data-k]", el).forEach(x => x.setAttribute("aria-pressed", false)); return; }
          M.desk(slug, id, { decision: k, note: $(".nt", el).value, date: new Date().toISOString().slice(0, 10) }); el.dataset.d = k;
          $$("button[data-k]", el).forEach(x => x.setAttribute("aria-pressed", x === b));
        });
        $(".nt", el).onchange = e => { const cur = M.desk(slug, id); if (cur) { cur.note = e.target.value; M.desk(slug, id, cur); } };
      });
    };
    $("#ff").onclick = e => { onlyFlagged = !onlyFlagged; e.currentTarget.setAttribute("aria-pressed", onlyFlagged); draw(); };
    $("#more").onclick = () => { shown += 40; draw(); };
    $("#rid").onchange = e => M.reviewer(e.target.value.trim());
    $("#ex").onclick = () => {
      const rid = $("#rid").value.trim(); M.reviewer(rid);
      const ds = Object.entries(M.state.desk[slug] || {});
      if (!/^agt:[0-9A-Za-z]{22}$/.test(rid)) { $("#msg").textContent = "Enter your reviewer ID from the roster (agt: followed by 22 letters and digits) first."; return; }
      const bad = ds.filter(([, d]) => d.decision === "needs_discussion" && !d.note.trim());
      if (bad.length) { $("#msg").textContent = `${bad.length} "needs discussion" decision${bad.length > 1 ? "s need" : " needs"} a note before export.`; return; }
      const file = { format: "marsad-review-decisions", version: 1, reviewer_id: rid, created: new Date().toISOString(),
        decisions: ds.map(([id, d]) => Object.assign({ kind: "claim", target: id, decision: d.decision, date: d.date }, d.note.trim() ? { note: d.note.trim() } : {})) };
      const ta = $("#out"); ta.hidden = false; ta.value = JSON.stringify(file, null, 1); ta.select();
      try { navigator.clipboard.writeText(ta.value).then(() => $("#msg").textContent = `${ds.length} decisions copied. Save them as a .json file and send it to the maintainer.`, () => $("#msg").textContent = "Selected: copy it now."); } catch (e) { $("#msg").textContent = "Selected: copy it now."; }
    };
    draw();
  }

  /* ---------------- about, follow ---------------- */
  function about() {
    view.innerHTML = `<div class="wrap" style="max-inline-size:52rem"><p class="kicker">How this works</p><h1>Where everything comes from</h1>
      <p>Every element on every screen belongs to one of four classes. Press <b>Provenance lens</b> to outline each one.</p>
      <div class="tablewrap"><table><tbody>${Object.entries(INDEX.classes).map(([k, v]) => `<tr><td>${chip(k)}</td><td>${esc(v)}</td></tr>`).join("")}</tbody></table></div>
      <h2 style="margin-top:24px">The rules this product keeps</h2>
      <ul><li>No pixel without provenance: nothing is drawn that a claim, a gazetteer point or a stated computation does not support.</li>
        <li>No depiction: no figure of the Prophet ﷺ, his family or the Companions, in any view. Places, ground, sky and names only.</li>
        <li>The guide asks; it never asserts. Every sentence of fact comes from a claim, a passage or a computation shown with its assumptions.</li>
        <li>A computed number is never rank or significance. Your sky records what you opened; it ranks no one.</li>
        <li>Reported and converted dates are kept apart. A mismatch goes to the scholars, never into a correction.</li></ul>
      <h2 style="margin-top:24px">Channel packs</h2>
      <p class="muted">Seven messages per expedition for the WhatsApp pilot. Drafts: a teacher reads each before it is sent.</p>
      <ul>${INDEX.expeditions.map(e => `<li><a href="channels/${e.slug}.txt">${esc(e.title)}</a></li>`).join("")}</ul>
      <h2 style="margin-top:24px">Sources</h2>
      <p class="muted">${esc(INDEX.source.work)}, OpenITI 0213IbnHisham.SiraNabawiyya.Shamela0023833-ara1, ${esc(INDEX.source.edition)}: names, voices, dates and totals as proposed claims, never the Arabic text itself. Gazetteer points: al-Thurayya (CC BY 4.0) and Wikidata (CC0), all proposed. Ground: Terrain Tiles on AWS Open Data (Mapzen), present-day elevation. Land outlines: Natural Earth (public domain). Sky: astronomy-engine 2.1.19 (MIT) and the HYG star catalogue v4.1 (CC BY-SA 4.0). Spaced review: FSRS-4.5 default weights.</p>
      <p class="muted">Halaqa mode mirrors its steps to other tabs of the same browser (open <a href="#follow">#follow</a> in a second window for a projector). Following on students' own phones needs a small relay server, which this preview does not include.</p></div>`;
  }
  function follow() {
    view.innerHTML = `<div class="wrap"><h1>Following the room</h1><p class="muted">This window shows whatever step the halaqa screen in this browser moves to. Leave it open on the projector.</p></div>`;
    try { bc = bc || new BroadcastChannel("marsad-halaqa"); bc.onmessage = e => { if (e.data && e.data.slug) location.hash = `x-${e.data.slug}-${e.data.step}`; }; } catch (e) { view.insertAdjacentHTML("beforeend", '<p class="wrap bad">This browser cannot follow another tab.</p>'); }
  }

  route();
})();
