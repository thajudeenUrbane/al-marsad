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
  for (const tab of ["guide", "show", "index", "log", "key"]) {
    await page.click(`#tab-${tab}`); await page.waitForTimeout(250);
    ok((await page.$$eval("#drawer-body > *", (els) => els.length)) > 2, `${tag}: the ${tab} tab has content`);
  }
  await shot("07-drawer-key");
  await page.click("#tab-guide"); await page.waitForTimeout(200);
  const tours = await page.$$eval(".tour h3", (els) => els.map((e) => e.textContent));
  ok(tours.length >= 6, `${tag}: ${tours.length} tours listed: ${tours.join(" | ")}`);
  await page.click("#close-atlas");
  // Arabic
  await page.click("#lang"); await page.waitForTimeout(800);
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

(async () => {
  await run({ width: 1440, height: 900 }, "desktop");
  await run({ width: 390, height: 844 }, "phone");
  console.log(failures ? `${failures} check(s) failed` : "all checks passed");
  process.exit(failures ? 1 : 0);
})();
