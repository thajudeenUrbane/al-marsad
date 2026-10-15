#!/usr/bin/env node
/* Browser check of the timeline and the map with JavaScript ON (slice 10).
 *
 * For each page, as a phone (390 px, touch) and as a desktop, it checks that:
 *  - the drawing renders from data.json, with no script error;
 *  - no request leaves the local server, and no image of any kind is loaded;
 *  - the page loads less than 2,000,000 bytes before any user action;
 *  - every drawn mark links to a page that exists, and shows its status;
 *  - the text version lists exactly the drawn items;
 *  - marks are reachable by keyboard (Tab) and by touch (tap shows the record, a second tap
 *    opens the page), and the map's selection panel shows the status;
 *  - bars keep their positions when the year cursor or the focus change, and one scrub step
 *    is drawn in under 100 ms (docs/08 section 7);
 *  - with prefers-reduced-motion, transitions are off.
 * Then it loads both pages with JavaScript OFF: the text version must list every item.
 *
 *   NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
 *     node site/interactive/check_interactive.cjs [site/dist] [--shots DIR]
 *
 * Needs the `playwright` npm package and a Chromium it can launch. Exit 1 on any failure.
 */
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const args = process.argv.slice(2);
const shotsAt = args.indexOf("--shots");
const shots = shotsAt >= 0 ? args.splice(shotsAt, 2)[1] : null;
const root = path.resolve(args[0] || path.join(__dirname, "..", "dist"));
const BUDGET = 2000000;
const STEP_MS = 100;
const TYPES = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8", ".ttl": "text/turtle; charset=utf-8" };
const READER = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "i18n", "en.json"), "utf8"));
const STATUS = READER["status.label"].split("{")[0].trim();          // "Status:"

const server = http.createServer((req, res) => {
  const p = decodeURIComponent(req.url.split("?")[0].split("#")[0]);
  let f = path.join(root, p);
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end("not found"); }
  res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});

const failures = [];
const fail = (msg) => { failures.push(msg); console.log("  FAIL " + msg); };
const data = (view) => JSON.parse(fs.readFileSync(path.join(root, view, "data.json"), "utf8"));
const pageExists = (view, href) => fs.existsSync(path.join(root, view, href.split("#")[0], "index.html"));
const same = (a, b) => JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());

const PROFILES = [
  ["phone", { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }],
  ["desktop", { viewport: { width: 1280, height: 900 } }],
];

async function open(browser, origin, view, options) {
  const ctx = await browser.newContext(options);
  const page = await ctx.newPage();
  const log = { external: [], images: [], errors: [], responses: [] };
  page.on("request", (rq) => {
    if (!rq.url().startsWith(origin)) log.external.push(rq.url());
    if (rq.resourceType() === "image") log.images.push(rq.url());
  });
  page.on("response", (r) => log.responses.push(r));
  page.on("pageerror", (e) => log.errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error") log.errors.push(m.text()); });
  await page.goto(`${origin}/${view}/`, { waitUntil: "load" });
  if (options.javaScriptEnabled !== false) {
    await page.waitForSelector("#ix-app[data-ready]", { timeout: 20000 });
    await page.waitForLoadState("networkidle");
  }
  log.bytes = await loaded(log);          // everything loaded before any user action
  return { ctx, page, log };
}

async function loaded(log) {
  let bytes = 0;
  for (const r of log.responses) { try { bytes += (await r.body()).length; } catch (e) { /* redirects */ } }
  return bytes;
}

async function tabTo(page, selector, max) {
  for (let i = 0; i < max; i++) {
    await page.keyboard.press("Tab");
    if (await page.evaluate((s) => !!(document.activeElement && document.activeElement.matches(s)), selector)) return true;
  }
  return false;
}

async function checkTimeline(browser, origin, name, options) {
  const d = data("timeline");
  const { ctx, page, log } = await open(browser, origin, "timeline", options);
  const tag = `timeline (${name})`;
  if ((await page.getAttribute("#ix-app", "data-ready")) !== "1") fail(`${tag}: the drawing did not render`);
  const rows = await page.$$eval(".tl-row", (els) => els.map((e) => e.dataset.id));
  if (!same(rows, d.items.map((i) => i.id)) || rows.length !== d.items.length) fail(`${tag}: drawn rows differ from data.json`);
  const bars = await page.$$eval(".tl-row .tl-bar", (els) => els.map((e) => e.getAttribute("href")));
  if (bars.length !== d.items.length) fail(`${tag}: ${bars.length} bars for ${d.items.length} items`);
  bars.filter((h) => !pageExists("timeline", h)).forEach((h) => fail(`${tag}: mark links to a missing page ${h}`));
  const alt = await page.$$eval("ol.ix-alt li[data-id]", (els) => els.map((e) => e.dataset.id));
  if (!same(alt, rows)) fail(`${tag}: the text version does not list exactly the drawn items`);
  const metas = await page.$$eval(".tl-row .tl-meta", (els) => els.map((e) => e.innerText));
  if (metas.length !== rows.length || metas.some((t) => !t.includes(STATUS))) fail(`${tag}: a drawn item shows no status`);

  // positions never move with the year cursor or the focus; one scrub step under 100 ms
  const boxes = () => page.$$eval(".tl-row .tl-bar", (els) => els.map((e) => { const r = e.getBoundingClientRect(); return [Math.round(r.x * 2), Math.round(r.width * 2)]; }));
  const before = await boxes();
  const ms = await page.evaluate(async () => {
    const el = document.getElementById("ix-year");
    const t0 = performance.now();
    el.value = String(parseInt(el.min, 10) + 15);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return performance.now() - t0;
  });
  if (ms > STEP_MS) fail(`${tag}: a scrub step took ${ms.toFixed(0)} ms`);
  const focusValue = await page.$eval("#ix-focus", (s) => (s.options[1] ? s.options[1].value : ""));
  if (focusValue) await page.selectOption("#ix-focus", focusValue);
  if (JSON.stringify(await boxes()) !== JSON.stringify(before)) fail(`${tag}: bars moved when the year or the focus changed`);
  if (!(await page.$$eval(".tl-row.is-dim", (e) => e.length))) fail(`${tag}: the year cursor and focus dimmed nothing`);
  if (!/#.*year=/.test(page.url())) fail(`${tag}: the view is not kept in the address`);

  // keyboard: a name link, then its disclosure button, opens the record with its status
  await page.evaluate(() => { document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0); });
  await page.keyboard.press("Escape");
  await page.focus("#ix-focus");
  if (!(await tabTo(page, ".tl-more", 40))) fail(`${tag}: no disclosure button reachable by Tab`);
  else {
    await page.keyboard.press("Enter");
    const open = await page.evaluate(() => {
      const b = document.activeElement;
      const det = document.getElementById(b.getAttribute("aria-controls"));
      return b.getAttribute("aria-expanded") === "true" && det && !det.hidden ? det.innerText : null;
    });
    if (!open || !open.includes(STATUS)) fail(`${tag}: Enter on the disclosure button did not show the record with its status`);
  }
  if (name === "phone") {
    await page.locator(".tl-more").nth(1).tap();
    if ((await page.locator(".tl-more").nth(1).getAttribute("aria-expanded")) !== "true") fail(`${tag}: tap did not open a record`);
  }
  if (shots) await page.screenshot({ path: path.join(shots, `timeline-${name}.png`), fullPage: false });
  report(tag, log, rows.length);
  await ctx.close();
}

async function checkMap(browser, origin, name, options) {
  const d = data("map");
  const { ctx, page, log } = await open(browser, origin, "map", options);
  const tag = `map (${name})`;
  if ((await page.getAttribute("#ix-app", "data-ready")) !== "1") fail(`${tag}: the drawing did not render`);
  const marks = await page.$$eval("a.mk", (els) => els.map((e) => [e.dataset.id, e.getAttribute("href")]));
  if (!same(marks.map((m) => m[0]), d.places.map((p) => p.id))) fail(`${tag}: drawn places differ from data.json`);
  marks.filter((m) => !pageExists("map", m[1])).forEach((m) => fail(`${tag}: mark links to a missing page ${m[1]}`));
  const drawnSegs = d.routes.flatMap((r) => r.segments.filter((s) => s.drawn).map((s) => s.id));
  const segs = await page.$$eval("a.map-seg", (els) => els.map((e) => e.dataset.id));
  if (!same(segs, drawnSegs)) fail(`${tag}: drawn route segments differ from data.json`);
  const altPlaces = await page.$$eval('ol.ix-alt[data-group="places"] li[data-id]', (els) => els.map((e) => e.dataset.id));
  if (!same(altPlaces, marks.map((m) => m[0]))) fail(`${tag}: the text version does not list exactly the drawn places`);
  const altSegs = await page.$$eval('ol.ix-alt[data-group="segments"] li[data-id]', (els) => els.map((e) => e.dataset.id));
  if (!drawnSegs.every((s) => altSegs.includes(s))) fail(`${tag}: a drawn segment is missing from the text version`);
  const titles = await page.$$eval("a.mk > title, a.map-seg > title", (els) => els.map((e) => e.textContent));
  if (titles.some((t) => !t.includes(STATUS))) fail(`${tag}: a mark's name does not carry its status`);

  // zoom works and keeps every mark
  await page.locator(".map-zoom button").first().click();
  if ((await page.$$eval("a.mk", (e) => e.length)) !== d.places.length) fail(`${tag}: marks lost on zoom`);

  if (name === "phone") {
    // touch: the first tap shows the record, the second opens the page
    const mark = page.locator("a.mk").first();
    await mark.tap();
    await page.waitForTimeout(150);
    if (new URL(page.url()).pathname !== "/map/") fail(`${tag}: the first tap left the map`);
    if (!(await page.locator(".map-panel").innerText()).includes(STATUS)) fail(`${tag}: the tapped record shows no status`);
    await Promise.all([page.waitForURL(/\/place\//, { timeout: 5000 }).catch(() => fail(`${tag}: the second tap did not open the page`)), mark.tap()]);
  } else {
    // keyboard: Tab reaches a mark, which shows its record; Enter opens its page
    await page.focus("#ix-focus");
    if (!(await tabTo(page, "a.mk", 60))) fail(`${tag}: no map mark reachable by Tab`);
    else {
      if (!(await page.locator(".map-panel").innerText()).includes(STATUS)) fail(`${tag}: the focused mark shows no status`);
      if (shots) await page.screenshot({ path: path.join(shots, `map-${name}.png`), fullPage: false });
      await Promise.all([page.waitForURL(/\/place\//, { timeout: 5000 }).catch(() => fail(`${tag}: Enter did not open the page`)),
        page.keyboard.press("Enter")]);
    }
  }
  if (shots && name === "phone") await page.goBack().then(() => page.screenshot({ path: path.join(shots, `map-${name}.png`) }));
  report(tag, log, marks.length + segs.length);
  await ctx.close();
}

function report(tag, log, n) {
  const bytes = log.bytes;
  if (log.external.length) fail(`${tag}: requests left the local server: ${log.external.join(", ")}`);
  if (log.images.length) fail(`${tag}: images were loaded: ${log.images.join(", ")}`);
  if (log.errors.length) fail(`${tag}: script errors: ${log.errors.join(" | ")}`);
  if (bytes > BUDGET) fail(`${tag}: ${bytes} bytes is over the ${BUDGET} byte budget`);
  console.log(`${tag}: ${n} marks drawn, ${bytes.toLocaleString("en")} bytes loaded`);
}

async function reducedMotion(browser, origin) {
  const { ctx, page } = await open(browser, origin, "timeline", { reducedMotion: "reduce", viewport: { width: 800, height: 900 } });
  const t = await page.$eval(".tl-row .tl-bar", (e) => getComputedStyle(e).transitionDuration);
  if (t !== "0s") fail(`timeline: transitions still run with reduced motion (${t})`);
  else console.log("reduced motion: transitions off");
  await ctx.close();
}

async function withoutJs(browser, origin) {
  for (const [view, sel, n] of [["timeline", "ol.ix-alt li[data-id]", data("timeline").items.length],
    ["map", 'ol.ix-alt[data-group="places"] li[data-id]', data("map").places.length]]) {
    const { ctx, page, log } = await open(browser, origin, view, { javaScriptEnabled: false });
    const got = await page.$$eval(sel, (e) => e.length);
    if (got !== n) fail(`${view} without JavaScript: the text version lists ${got} of ${n} items`);
    if (log.external.length) fail(`${view} without JavaScript: external requests ${log.external.join(", ")}`);
    console.log(`${view} without JavaScript: text version lists ${got} items`);
    await ctx.close();
  }
}

(async () => {
  for (const view of ["timeline", "map"]) {
    if (!fs.existsSync(path.join(root, view, "data.json"))) {
      console.error(`${root}/${view} not built: run site/build.py, then site/interactive/build_interactive.py`);
      process.exit(1);
    }
  }
  if (shots) fs.mkdirSync(shots, { recursive: true });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();
  for (const [name, options] of PROFILES) {
    await checkTimeline(browser, origin, name, options);
    await checkMap(browser, origin, name, options);
  }
  await reducedMotion(browser, origin);
  await withoutJs(browser, origin);
  await browser.close();
  server.close();
  console.log(failures.length ? `FAILED: ${failures.length}` : "OK: both pages render, stay local and under budget, and list every drawn item");
  process.exit(failures.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
