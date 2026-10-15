#!/usr/bin/env node
/* The three doors, the thread and plain words in a real browser, at 390 x 844 (a phone),
 * with JavaScript on and off.
 *
 *   NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
 *     node site/check_doors.cjs [site/dist] [--shots DIR]
 *
 * JavaScript off: the home page shows the three doors and the hub, nothing sideways;
 * Discover leads to the stories; Study opens a person's page at #evidence, with the
 * claims there; no thread switch and no plain-words switch are visible, and every page is
 * complete. JavaScript on: the thread opens on Abu Bakr's page (found by his name), lists
 * moments in order, follows someone who shares a moment, Back returns, Close restores the
 * page; plain words hides the bracketed Arabic term, survives a reload (kept on the device)
 * and switches off again. In both modes no request may leave the local server.
 * Needs the `playwright` npm package and a Chromium it can launch. Exit 1 on any failure.
 */
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const args = process.argv.slice(2);
const shotsAt = args.indexOf("--shots");
const shots = shotsAt >= 0 ? args.splice(shotsAt, 2)[1] : null;
const root = path.resolve(args[0] || path.join(__dirname, "dist"));
const EN = JSON.parse(fs.readFileSync(path.join(__dirname, "i18n", "en.json"), "utf8"));
const TYPES = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
                ".json": "application/json", ".ttl": "text/turtle; charset=utf-8" };
const NAME = "Abu Bakr as-Siddiq";

const server = http.createServer((req, res) => {
  let f = path.join(root, decodeURIComponent(req.url.split("?")[0]));
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end("not found"); }
  res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});

(async () => {
  const thread = JSON.parse(fs.readFileSync(path.join(root, "thread.json"), "utf8"));
  const abu = thread.e.filter((r) => r[2] === NAME);
  if (abu.length !== 1) throw new Error(`expected one ${NAME} in thread.json, found ${abu.length}`);
  const abuPath = `/person/${abu[0][1]}/`;
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();
  const failures = [], external = [];
  const fail = (msg) => { failures.push(msg); console.log("  FAIL " + msg); };
  const context = async (js) => {
    const ctx = await browser.newContext({ javaScriptEnabled: js, viewport: { width: 390, height: 844 } });
    ctx.on("request", (rq) => { if (!rq.url().startsWith(origin)) external.push(rq.url()); });
    return ctx;
  };
  const shot = async (page, name) => {
    if (!shots) return;
    fs.mkdirSync(shots, { recursive: true });
    await page.screenshot({ path: path.join(shots, name + ".png"), fullPage: false });
  };
  const noSideways = async (page, where) => {
    const w = await page.evaluate(() => document.documentElement.scrollWidth);
    if (w > 390) fail(`${where}: the page is ${w}px wide at 390px (sideways scroll)`);
  };

  // ---------------------------------------------------------------- JavaScript off
  const off = await context(false);
  let page = await off.newPage();
  await page.goto(origin + "/");
  const doors = await page.locator(".door h2").allInnerTexts();
  console.log(`  JS off home: doors ${JSON.stringify(doors)}; hub items ${await page.locator(".hub-list > li").count()}`);
  const want = [EN["door.discover.title"], EN["door.study.title"], EN["door.research.title"]];
  if (JSON.stringify(doors) !== JSON.stringify(want)) fail("the home page does not show the three doors in order");
  if (await page.locator(".plain-toggle").isVisible()) fail("the plain-words switch shows without JavaScript");
  await noSideways(page, "home");
  await shot(page, "home-nojs");
  await page.locator("#door-discover a").first().click();
  await page.waitForLoadState("load");
  if (!/\/story\/$/.test(new URL(page.url()).pathname)) fail("Discover did not lead to the stories");
  await page.goto(origin + "/");
  await page.locator("#door-study a").first().click();
  await page.waitForLoadState("load");
  if (new URL(page.url()).pathname !== "/study/") fail("Study did not lead to the study page");
  const studyLink = page.locator(`#study-people a[href$="${abuPath.slice(1)}#evidence"]`);
  if (!(await studyLink.count())) fail(`${NAME} is not on the study page with #evidence`);
  else {
    await studyLink.first().click();
    await page.waitForLoadState("load");
    const u = new URL(page.url());
    if (u.pathname !== abuPath || u.hash !== "#evidence") fail(`Study did not open ${NAME} at #evidence (${page.url()})`);
    const top = await page.locator("#evidence").evaluate((el) => el.getBoundingClientRect().top);
    if (Math.abs(top) > 40) fail(`the evidence is not at the top of the window (${top}px)`);
    if (!(await page.locator("#evidence .claim").first().isVisible())) fail("no claim under the evidence heading");
    if (await page.locator(".thread-root").isVisible()) fail("the thread switch shows without JavaScript");
    if ((await page.locator("h1").count()) !== 1) fail("person page: not one h1");
    await noSideways(page, "person page");
    await shot(page, "evidence-nojs");
    console.log(`  JS off Study -> ${u.pathname}${u.hash}, evidence at ${Math.round(top)}px`);
  }
  await page.goto(origin + "/research/");
  if (!(await page.locator(`#research-records a[href$="${abuPath.slice(1)}#evidence"]`).count())) fail("Research does not list the record at #evidence");
  await page.goto(origin + "/experiments/");
  if ((await page.locator(".proto-list > li").count()) !== 3) fail("the Experiments page does not list three prototypes");
  await page.close();
  await off.close();

  // ---------------------------------------------------------------- JavaScript on
  const on = await context(true);
  page = await on.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(origin + abuPath);
  if (!(await page.locator(".thread-open").isVisible())) fail("no Follow the thread button with JavaScript");
  await page.click(".thread-open");
  await page.waitForSelector(".thread-view .moment", { timeout: 10000 }).catch(() => fail("the thread did not open"));
  const moments = await page.locator(".thread-view .moment").count();
  const head = await page.locator("#thread-h").innerText().catch(() => "");
  console.log(`  JS on thread of ${head}: ${moments} moments; ${page.url().replace(origin, "")}`);
  if (head !== NAME || moments < 10) fail("the thread does not show his moments");
  if (!(await page.locator(".thread-view .status").first().innerText()).startsWith("Status:")) fail("a moment without its status");
  if (await page.locator("article").isVisible()) fail("the page is still shown under the thread");
  await noSideways(page, "thread");
  await shot(page, "thread");
  const chip = page.locator(".thread-view .chip").first();
  const next = await chip.innerText();
  await chip.click();
  await page.waitForFunction((n) => document.getElementById("thread-h").textContent === n, next, { timeout: 5000 })
    .catch(() => fail(`following ${next} did not move the thread`));
  if (!/#thread=person\//.test(page.url()) && !/#thread=group\//.test(page.url())) fail("the address does not name the followed person");
  if ((await page.locator(".thread-path li").count()) !== 2) fail("the path does not show two steps");
  console.log(`  JS on followed to ${next}; path: ${(await page.locator(".thread-path").innerText()).replace(/\s+/g, " ")}`);
  await shot(page, "thread-followed");
  await page.goBack();
  await page.waitForFunction((n) => document.getElementById("thread-h").textContent === n, NAME, { timeout: 5000 })
    .catch(() => fail("Back did not return along the thread"));
  await page.click(".thread-close");
  if (!(await page.locator("article h1").isVisible())) fail("closing the thread did not restore the page");
  // a shared address opens the thread at the person it names
  await page.goto(origin + abuPath + "#thread");
  await page.waitForSelector(".thread-view .moment", { timeout: 10000 }).catch(() => fail("#thread did not open the thread"));

  // plain words
  await page.goto(origin + abuPath);
  const toggle = page.locator(".plain-toggle");
  if (!(await toggle.isVisible())) fail("no plain-words switch with JavaScript");
  const gloss = page.locator(".t-gloss").first();
  if (!(await gloss.count()) || !(await gloss.isVisible())) fail("no bracketed term shown before plain words");
  await toggle.click();
  if ((await toggle.getAttribute("aria-pressed")) !== "true") fail("the switch did not turn on");
  if (await gloss.isVisible()) fail("plain words did not hide the bracketed Arabic term");
  await page.reload();
  if ((await page.locator(".plain-toggle").getAttribute("aria-pressed")) !== "true") fail("plain words was not kept on this device");
  if (await page.locator(".t-gloss").first().isVisible()) fail("after a reload the bracketed term is back");
  await shot(page, "plain-on");
  await page.locator(".plain-toggle").click();
  if (!(await page.locator(".t-gloss").first().isVisible())) fail("switching plain words off did not restore the term");
  console.log("  JS on plain words: hides the bracketed term, kept across a reload, switches off");
  await page.goto(origin + "/");
  await noSideways(page, "home with JavaScript");
  await shot(page, "home");
  if (errors.length) fail("script errors: " + errors.join("; "));
  await page.close();
  await on.close();

  if (external.length) fail("requests left the local server: " + external.join(", "));
  await browser.close();
  server.close();
  console.log(failures.length ? `FAILED: ${failures.length}` : "OK: three doors (Study opens the evidence), the thread and plain words work with JavaScript on, and every page is complete with it off; 390px wide, no external requests");
  process.exit(failures.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
