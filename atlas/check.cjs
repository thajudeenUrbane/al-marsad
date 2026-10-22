// Sky Atlas browser check (Playwright + Chromium):
//   NODE_PATH="$(npm root -g)" node atlas/check.cjs [atlas/index.html] [screenshot dir]
// Desktop and a 390 x 844 phone: the page unpacks and draws with no page error and no
// external request; the guided tour, search, every view, the record card, a traced
// connection, the drawer tabs and the Arabic interface all work; nothing scrolls sideways.
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

// scripts/check_all.sh passes site/dist to every browser check: anything but an .html file
// means the committed page
const arg = process.argv[2] || "";
const file = path.resolve(arg.endsWith(".html") ? arg : path.join(__dirname, "index.html"));
const shots = process.argv[3] || path.join(require("os").tmpdir(), "atlas-check");
fs.mkdirSync(shots, { recursive: true });
let failures = 0;
const ok = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); if (!cond) failures++; };

async function run(size, tag) {
  const browser = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"] });
  const page = await browser.newPage({ viewport: size, hasTouch: tag === "phone", isMobile: tag === "phone" });
  const errors = [], external = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("request", (r) => { if (!/^(file|data|blob):/.test(r.url())) external.push(r.url()); });
  await page.goto("file://" + file);
  await page.waitForSelector("html[data-ready='1']", { timeout: 60000 });
  await page.waitForTimeout(1500);
  const shot = async (name) => page.screenshot({ path: path.join(shots, `atlas-${tag}-${name}.png`) });
  await shot("01-start");
  ok(await page.isVisible("#welcome"), `${tag}: the welcome card shows on a first visit`);
  // the guided tour
  await page.click("#welcome-guide");
  await page.waitForTimeout(1800);
  ok(await page.isVisible("#guide"), `${tag}: the guide opens`);
  const prog = await page.textContent("#guide-progress");
  ok(/Stop 1 of \d+/.test(prog), `${tag}: guide progress reads "${prog}"`);
  await shot("02-tour-1");
  await page.click("#guide-next"); await page.waitForTimeout(1600);
  await page.click("#guide-next"); await page.waitForTimeout(1600);
  ok(/Stop 3 of/.test(await page.textContent("#guide-progress")), `${tag}: Next moves the tour on`);
  ok((await page.$$(".dir")).length >= 2, `${tag}: the stop offers directions onward`);
  await shot("03-tour-3");
  // jump to Badr in the tour via the ecliptic: search instead
  await page.click("#guide-end"); await page.waitForTimeout(600);
  await page.fill("#search", "Battle of Badr");
  await page.waitForTimeout(300);
  const hits = await page.$$eval("#search-results li", (els) => els.map((e) => e.textContent));
  ok(hits.length > 0 && /Badr/.test(hits[0]), `${tag}: search finds Badr (${hits[0]})`);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(1800);
  ok(await page.isVisible("#record"), `${tag}: the record opens`);
  const who = await page.$$eval("#record-body .person-chip", (els) => els.length);
  ok(who > 10, `${tag}: Badr's record lists the people recorded there (${who} chips shown)`);
  await shot("04-badr");
  // study depth shows sources
  await page.click("#depth-study"); await page.waitForTimeout(500);
  const cites = await page.$$eval("#record-body .cite", (els) => els.length);
  ok(cites > 0, `${tag}: Study depth shows citations (${cites})`);
  // a person, the lineage view
  await page.fill("#search", "Ali b. Abi Talib"); await page.waitForTimeout(300); await page.keyboard.press("Enter");
  await page.waitForTimeout(1500);
  const nm = await page.textContent("#record-body .name");
  ok(/Ali|ʿAlī/.test(nm), `${tag}: Ali's record opens (${nm})`);
  ok(/One of the ten|rightly guided/.test(await page.textContent("#record-body")), `${tag}: membership list tags show`);
  await page.evaluate(() => window.__atlas.setView("lineage"));
  await page.waitForTimeout(1600);
  ok(/lineage of/i.test(await page.textContent("#caption")), `${tag}: the Lineage view opens`);
  await shot("05-lineage");
  // trace
  await page.evaluate(() => { const a = window.__atlas; const s = a.search("Abu Bakr as-Siddiq")[0], t = a.search("Bilal")[0]; a.trace(s, t); });
  await page.waitForTimeout(1500);
  ok(/connects these two/.test(await page.textContent("#record-body")), `${tag}: a traced connection shows its note`);
  // views
  for (const v of ["book", "time", "map", "sky"]) {
    await page.click(`#view-${v}`); await page.waitForTimeout(1500);
    ok((await page.getAttribute(`#view-${v}`, "aria-selected")) === "true", `${tag}: the ${v} view opens`);
    if (v !== "sky") await shot(`06-view-${v}`);
  }
  // drawer tabs
  await page.click("#close-record").catch(() => {});
  await page.click("#open-atlas"); await page.waitForTimeout(400);
  for (const tab of ["guide", "show", "index", "log", "text", "key"]) {
    await page.click(`#tab-${tab}`); await page.waitForTimeout(250);
    ok((await page.$$eval("#drawer-body > *", (els) => els.length)) > 2, `${tag}: the ${tab} tab has content`);
  }
  await shot("07-drawer-key");
  await page.click("#tab-guide"); await page.waitForTimeout(200);
  const tours = await page.$$eval(".tour h3", (els) => els.map((e) => e.textContent));
  ok(tours.length >= 6, `${tag}: ${tours.length} tours listed: ${tours.join(" | ")}`);
  await page.click("#close-atlas");
  await features(page, tag, shot);
  // Arabic
  await page.click("#lang"); await page.waitForTimeout(800);
  ok(await page.isVisible("#lang-note"), `${tag}: the Arabic draft note shows`);
  ok((await page.getAttribute("html", "dir")) === "rtl", `${tag}: Arabic switches the page to right to left`);
  await page.evaluate(() => { const a = window.__atlas; a.startTour(a.TOURS()[0], 4); });
  await page.waitForTimeout(1800);
  ok(/المحطة/.test(await page.textContent("#guide-progress")), `${tag}: the guide speaks Arabic`);
  await shot("08-arabic-tour");
  const wide = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  ok(!wide, `${tag}: nothing scrolls sideways`);
  ok(errors.length === 0, `${tag}: no page errors ${errors.length ? JSON.stringify(errors.slice(0, 3)) : ""}`);
  ok(external.length === 0, `${tag}: no external requests ${external.length ? external.slice(0, 3).join(" ") : ""}`);
  await browser.close();
}

// every feature restored from the earlier Sky Atlas, and the new ones
async function features(page, tag, shot) {
  const A = (fn, arg) => page.evaluate(fn, arg);
  const text = async (sel) => (await page.textContent(sel)) || "";
  const wait = (ms) => page.waitForTimeout(ms);
  await A(() => window.__atlas.home()); await wait(900);
  // views new to this round
  for (const v of ["stories", "globe", "chains"]) {
    await page.click(`#view-${v}`); await wait(1500);
    ok((await page.getAttribute(`#view-${v}`, "aria-selected")) === "true", `${tag}: the ${v} view opens`);
    await shot(`10-view-${v}`);
  }
  await page.click("#view-sky"); await wait(1200);
  // viewpoints, blend, the 0 key
  for (const vp of ["face", "angle", "edge", "below"]) await page.click(`[data-viewpoint="${vp}"]`);
  await wait(900);
  await A(() => { const b = document.getElementById("blend"); b.value = "0.5"; b.dispatchEvent(new Event("input")); }); await wait(500);
  ok(/%/.test(await text("#here")), `${tag}: the blend slider blends two views (${await text("#here")})`);
  await shot("11-blend");
  await A(() => { const b = document.getElementById("blend"); b.value = "0"; b.dispatchEvent(new Event("input")); }); await wait(300);
  await page.focus("#ov"); await page.keyboard.press("0"); await wait(300);
  // play history
  await page.click("#play"); await wait(2600);
  ok(/CE/.test(await text("#play-year")), `${tag}: Play history counts the years (${await text("#play-year")})`);
  await shot("12-history");
  await page.click("#play"); await wait(200);
  ok(/Resume/.test(await text("#play")), `${tag}: Play history pauses`);
  await page.click("#play-clear"); await wait(300);
  ok((await text("#play-year")) === "", `${tag}: history can be left`);
  // vantage points
  const presets = await A(() => window.__atlas.S && Object.keys({}).length === 0 ? null : null);
  for (const key of ["hijrah_abubakr", "badr", "first_believers", "family", "chain"]) {
    await A((k) => window.__atlas.applyPreset(k), key); await wait(900);
    ok(/vantage/.test(await text("#here")), `${tag}: vantage point ${key}`);
  }
  await shot("13-vantage-chain");
  // back and home
  const a = await A(() => window.__atlas.search("Abu Bakr as-Siddiq")[0]), b = await A(() => window.__atlas.search("Umar b. al-Khattab")[0]);
  await A((i) => window.__atlas.focus(i), a); await wait(700);
  await A((i) => window.__atlas.focus(i), b); await wait(700);
  ok(await page.isVisible(".back-to"), `${tag}: the panel offers a way back to the record before`);
  await page.click("#back"); await wait(900);
  ok(/Ab[uū] Bakr/.test(await text("#record-body .name")), `${tag}: Back returns to the record before`);
  await page.click("#home"); await wait(900);
  ok(await page.isHidden("#record"), `${tag}: Home clears the sky`);
  // depth, evidence, ladders, presence, absence, duplicates
  await page.click("#depth-study"); await wait(300);
  await page.fill("#search", "Battle of Badr"); await wait(250); await page.keyboard.press("Enter"); await wait(1500);
  const rec = await text("#record-body");
  ok(/Who was there, and who wasn't/.test(rec), `${tag}: the presence facet lists who was and wasn't there`);
  ok(/Evidence summary/.test(rec) && /How do we know about/.test(rec), `${tag}: evidence summary and the item's ladder`);
  await shot("14-presence");
  await A((ab) => window.__atlas.openPair(ab[0], ab[1]), [a, b]); await wait(900);
  ok(/How do we know\? /.test(await text("#record-body .name")), `${tag}: a line opens its own ladder`);
  await page.fill("#search", "al-Zubayr"); await wait(250);
  await A(() => { const s = window.__atlas.search("al-Zubayr (2)")[0]; window.__atlas.focus(s); }); await wait(900);
  ok(/Same written name/.test(await text("#record-body")), `${tag}: entries with the same written name are shown, not merged`);
  await page.keyboard.press("Escape");
  // tours: why each stop
  await A(() => { const x = window.__atlas; x.startTour(x.TOURS().find((t) => t.key === "j_hijrah-step-by-step"), 1); }); await wait(1500);
  ok((await page.$$(".why")).length > 0, `${tag}: a journey stop says why it was chosen (${(await text(".why")).slice(0, 80)})`);
  await page.click("#guide-end"); await wait(500);
  // the full trace tool
  await A((k) => window.__atlas.openDrawer(k), "guide"); await wait(300);
  await page.fill("#trace-from", "Abu Bakr as-Siddiq"); await page.press("#trace-from", "Enter");
  await page.fill("#trace-to", "Bilal"); await page.press("#trace-to", "Enter");
  await page.click("#trace-find"); await wait(1500);
  ok(/Thread 1/.test(await text("#record-body")), `${tag}: the trace tool finds ranked threads`);
  // Ask: the rule-based engine of ask/, over this graph
  await A((k) => window.__atlas.openDrawer(k), "ask"); await wait(300);
  const askOut = async (q) => {
    await page.fill("#atlas-ask-q", q); await page.press("#atlas-ask-q", "Enter");
    await page.waitForFunction((q) => (document.getElementById("atlas-ask-out").textContent || "").includes(q), q, { timeout: 30000 });
    return text("#atlas-ask-out");
  };
  ok(/people\(at: place "Badr"\)/.test(await askOut("Who was at Badr?")), `${tag}: Ask turns a question into a query and answers it`);
  const lit = await A(() => (window.__atlas.S.lit ? window.__atlas.S.lit.size : 0));
  ok(lit > 50, `${tag}: Ask lights the answer on the sky (${lit})`);
  await shot("19-ask");
  ok(/does not rank people/.test(await askOut("Who was the greatest Companion?")), `${tag}: Ask refuses a ranking, with the reason`);
  ok(await A(() => !window.__atlas.S.lit), `${tag}: a refusal lights nothing`);
  ok(/matches \d+ entries/.test(await askOut("Relatives of Fatima")), `${tag}: Ask asks which one when a name fits several`);
  await askOut("Who was at Badr?");
  await page.click("#atlas-ask-out a[href^='#ask/person/']"); await wait(900);
  ok(await page.isVisible("#record"), `${tag}: a name in an answer opens its record`);
  ok(!(await page.evaluate(() => location.hash)).startsWith("#ask/"), `${tag}: answer links never change the address`);
  // the merge review and class notes (this file has no shared store, so both stay in this browser)
  await A((k) => window.__atlas.openDrawer(k), "merges"); await wait(300);
  ok((await page.$$("#drawer-body .merge")).length > 50, `${tag}: the merge review lists slice 11a's proposals`);
  await page.selectOption("#drawer-body .merge-edit select >> nth=0", "scholar");
  await page.click("#drawer-body .merge-edit button >> nth=0"); await wait(300);
  ok(/working list: ask a scholar/.test(await text("#drawer-body .merge-state >> nth=0")), `${tag}: a merge decision is kept as a working list`);
  ok(/,scholar,/.test(await A(() => window.__atlas.mergesCsv())), `${tag}: decisions copy out in the proposals file's format`);
  await shot("20-merges");
  await page.click("#close-atlas"); await wait(200);
  const badr = await A(() => window.__atlas.search("Battle of Badr")[0]);
  await A((i) => window.__atlas.focus(i), badr); await wait(800);
  ok(/Proposed merges/.test(await text("#record-body")), `${tag}: a record names the merges proposed for it`);
  await page.fill("#notes-facet textarea", "<b>Start</b> with the people of Badr tour.");
  await page.click("#notes-facet button.chip"); await wait(300);
  ok(/<b>Start<\/b>/.test(await text("#notes-facet .notes-list")), `${tag}: a class note is added, shown as text`);
  await shot("15-threads");
  // show tab: light, period, scenery, groups, test load, GPU, speed
  await A((k) => window.__atlas.openDrawer(k), "show"); await wait(300);
  await page.check("#light-chain"); await wait(300);
  await page.check("#light-none"); await wait(200);
  await page.check("#light-generation"); await wait(200);
  await page.check("#scrub-on"); await wait(300);
  ok(/CE/.test(await text("#here")), `${tag}: a period limits the sky (${await text("#here")})`);
  await page.uncheck("#scrub-on");
  await page.uncheck("#show-scenery"); await page.check("#show-scenery");
  await page.check("#show-cluster"); await wait(300);
  await page.selectOption("#scale-pick", "10000"); await wait(600);
  await page.uncheck("#show-gpu"); await wait(600);
  ok(/canvas/.test(await text("#perf")), `${tag}: the plain canvas draws when the GPU is off (${await text("#perf")})`);
  await shot("16-canvas-test-load");
  await page.check("#show-gpu"); await wait(400);
  ok(/GPU/.test(await text("#perf")), `${tag}: the GPU draws again`);
  await page.selectOption("#scale-pick", "0"); await page.uncheck("#show-cluster");
  await page.check("#show-big"); await wait(200);
  ok(await A(() => document.documentElement.classList.contains("big")), `${tag}: larger text`);
  await page.uncheck("#show-big");
  // text view and research
  await page.click("#depth-research"); await wait(300);
  await A((k) => window.__atlas.openDrawer(k), "text"); await wait(400);
  ok(/Every mark in this view/.test(await text("#drawer-body")), `${tag}: the text view lists every mark`);
  ok(await page.isVisible("#viewstate-json"), `${tag}: the research panel shows the view state`);
  const tok = await A(() => window.__atlas.viewToken());
  ok(/^[A-Za-z0-9._~-]+$/.test(tok), `${tag}: the view code uses link-safe characters (${tok.slice(0, 60)})`);
  ok(await A((t) => window.__atlas.applyViewState(t), tok), `${tag}: a view code opens again`);
  await page.click("#close-atlas").catch(() => {});
  await page.click("#depth-discover");
  // new: compare, star chart and my tour, quests, copy, read aloud, classroom
  await A((ab) => window.__atlas.compare(ab[0], ab[1]), [a, b]); await wait(1000);
  ok(/Events both are recorded at/.test(await text("#record-body")), `${tag}: two records compare side by side`);
  await shot("17-compare");
  await A((ab) => { window.__atlas.toggleStar(ab[0]); window.__atlas.toggleStar(ab[1]); }, [a, b]);
  await A((k) => window.__atlas.openDrawer(k), "log"); await wait(300);
  ok(/My star chart/.test(await text("#drawer-body")) && /Tour my stars/.test(await text("#drawer-body")), `${tag}: the star chart makes a tour`);
  ok(/Quests/.test(await text("#drawer-body")) && /Meet the ten/.test(await text("#drawer-body")), `${tag}: quests are listed`);
  await shot("18-logbook");
  await page.click("#drawer-body button:has-text('Tour my stars')"); await wait(1200);
  ok(/My tour/.test(await text("#guide-tour")), `${tag}: my tour runs`);
  await page.click("#guide-speak"); await wait(200); await page.click("#guide-speak");
  await page.click("#guide-end"); await wait(400);
  await A((i) => window.__atlas.focus(i), a); await wait(600);
  await page.click("#record-body button:has-text('Copy citation')"); await wait(400);
  await A((ab) => { window.__atlas.toggleStar(ab[0]); window.__atlas.toggleStar(ab[1]); }, [a, b]);
  await A((k) => window.__atlas.openDrawer(k), "show"); await wait(200);
  await page.check("#show-classroom"); await wait(1500);
  ok(await A(() => document.documentElement.classList.contains("classroom")) && await page.isVisible("#guide"), `${tag}: classroom mode plays the guide in large type`);
  await page.keyboard.press("Escape"); await wait(400);
  ok(!(await A(() => document.documentElement.classList.contains("classroom"))), `${tag}: Esc leaves classroom mode`);
  await A(() => window.__atlas.endTour()); await A(() => window.__atlas.home()); await wait(600);
}

(async () => {
  // the two sizes run side by side: the check stays well inside CI's time limit
  await Promise.all([run({ width: 1440, height: 900 }, "desktop"), run({ width: 390, height: 844 }, "phone")]);
  console.log(failures ? `${failures} check(s) failed` : "all checks passed");
  process.exit(failures ? 1 : 0);
})();
