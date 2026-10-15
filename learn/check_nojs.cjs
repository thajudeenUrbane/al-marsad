#!/usr/bin/env node
/* Checks the learn pages in a real browser.
 *
 *   NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
 *     node learn/check_nojs.cjs [site/dist] [--shots DIR]
 *
 * 1. JavaScript off: the learn index, every journey and the practice page load and are
 *    complete: one h1, skip link, nav, licence footer, both stylesheets applied, the
 *    draft banner, every step with its link and every claim with a status label; the
 *    progress controls stay hidden; links lead to entity pages and back; no request
 *    leaves the local server.
 * 2. JavaScript on: marking a step done survives a reload, shows on the index, and
 *    can be cleared.
 * 3. JavaScript on but storage refused (as in some private windows): no error, no
 *    controls, the page as in 1.
 * Needs the `playwright` npm package and a Chromium it can launch. Exit 1 on any failure.
 */
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const args = process.argv.slice(2);
const shotsAt = args.indexOf("--shots");
const shots = shotsAt >= 0 ? args.splice(shotsAt, 2)[1] : null;
const root = path.resolve(args[0] || path.join(__dirname, "..", "site", "dist"));
const EN = JSON.parse(fs.readFileSync(path.join(__dirname, "i18n", "en.json"), "utf8"));
const SITE_EN = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "site", "i18n", "en.json"), "utf8"));
const TYPES = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
  ".json": "application/json", ".ttl": "text/turtle; charset=utf-8" };

const server = http.createServer((req, res) => {
  const p = decodeURIComponent(req.url.split("?")[0]);
  let f = path.join(root, p);
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end("not found"); }
  res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});

const failures = [];
const fail = (msg) => { failures.push(msg); console.log("  FAIL " + msg); };
const plain = (s) => s.replace(/\s+/g, " ").trim();

function journeys() {
  const d = path.join(root, "learn");
  return fs.readdirSync(d).filter((n) => n !== "assets" && n !== "practice" &&
    fs.existsSync(path.join(d, n, "index.html"))).sort();
}

async function frame(page, p) {
  if ((await page.locator("h1").count()) !== 1) fail(`${p}: not exactly one h1`);
  if ((await page.locator('a[href="#main"]').count()) !== 1) fail(`${p}: no skip link`);
  if ((await page.locator("header nav a").count()) < 5) fail(`${p}: navigation links missing`);
  if ((await page.locator("footer a").count()) < 4) fail(`${p}: licence footer links missing`);
  const font = await page.locator("body").evaluate((el) => getComputedStyle(el).fontFamily);
  if (!/system-ui/.test(font)) fail(`${p}: site.css not applied (${font})`);
}

(async () => {
  if (!fs.existsSync(path.join(root, "learn", "index.html"))) {
    console.error(`${root}/learn not found: run site/build.py, then learn/build_learn.py`);
    process.exit(1);
  }
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();
  const slugs = journeys();
  const external = [];
  const watch = (ctx) => ctx.on("request", (rq) => { if (!rq.url().startsWith(origin)) external.push(rq.url()); });

  // ---------------------------------------------------------------- 1. JavaScript off
  console.log("JavaScript off");
  const off = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 900 } });
  watch(off);
  const pages = ["/learn/", ...slugs.map((s) => `/learn/${s}/`), "/learn/practice/"];
  for (const p of pages) {
    const page = await off.newPage();
    const resp = await page.goto(origin + p, { waitUntil: "load" });
    console.log(`${p} -> ${resp.status()}`);
    if (resp.status() !== 200) { fail(`${p}: HTTP ${resp.status()}`); await page.close(); continue; }
    await frame(page, p);
    const text = plain(await page.locator("main").innerText());
    if (p !== "/learn/practice/" && !text.includes(EN["learn.state.draft"])) fail(`${p}: no draft label`);
    if (p.split("/").length === 4 && p !== "/learn/" && p !== "/learn/practice/") {
      if (!text.includes(plain(EN["learn.draft_banner"]))) fail(`${p}: no draft banner`);
      if (!text.includes(EN["learn.rule.heading"])) fail(`${p}: the rule is not shown`);
      const steps = page.locator("li.step");
      const n = await steps.count();
      if (n < 1) fail(`${p}: no steps`);
      for (let i = 0; i < n; i++) {
        const step = steps.nth(i);
        if (!(await step.isVisible())) fail(`${p}: step ${i + 1} not visible`);
        if ((await step.locator("h3.step-title a").count()) !== 1) fail(`${p}: step ${i + 1} has no entity link`);
      }
      const claims = page.locator("li.claim");
      const nc = await claims.count();
      for (let i = 0; i < nc; i++) {
        if (!/Status:/.test(await claims.nth(i).textContent())) fail(`${p}: claim ${i + 1} has no status label`);
      }
      if (await page.locator("[data-progress]").isVisible()) fail(`${p}: progress box visible without JavaScript`);
      if ((await page.locator("input").count()) !== 0) fail(`${p}: form controls without JavaScript`);
      const rule = await page.locator(".journey-rule").evaluate((el) => getComputedStyle(el).borderTopStyle);
      if (rule !== "solid") fail(`${p}: learn.css not applied`);
      console.log(`  ${n} steps, ${nc} claims, all with a status label`);
    }
    if (p === "/learn/practice/") {
      const n = await page.locator("li.question").count();
      if (n === 0 && !text.includes(EN["learn.practice.empty"])) fail(`${p}: empty bank not explained`);
      console.log(`  ${n} questions`);
    }
    if (shots) {
      fs.mkdirSync(shots, { recursive: true });
      await page.screenshot({ path: path.join(shots, "nojs" + p.replace(/[^a-z0-9]+/gi, "_") + ".png"), fullPage: true });
    }
    await page.close();
  }

  // follow links without JavaScript: index -> journey -> entity page -> back to the index
  {
    const page = await off.newPage();
    await page.goto(origin + "/learn/");
    await page.locator(".journey-cards a").first().click();
    await page.waitForLoadState("load");
    if (!/\/learn\/[a-z0-9-]+\/$/.test(page.url())) fail("journey card link did not open a journey");
    const href = await page.locator("li.step h3.step-title a").first().getAttribute("href");
    await page.locator("li.step h3.step-title a").first().click();
    await page.waitForLoadState("load");
    if (!/\/(person|event|story|group|place)\/[^/]+\/$/.test(page.url())) fail(`step link ${href} did not open an entity page`);
    if ((await page.locator("h1").count()) !== 1) fail("entity page reached from a step has no h1");
    await page.goBack();
    await page.locator('nav.breadcrumb a[href$="learn/"]').click();
    await page.waitForLoadState("load");
    if (!/\/learn\/$/.test(page.url())) fail("breadcrumb back to Learn failed");
    await page.close();
  }
  await off.close();

  // ---------------------------------------------------------------- 2. JavaScript on
  console.log("JavaScript on");
  const on = await browser.newContext({ viewport: { width: 390, height: 900 } });
  watch(on);
  {
    const slug = slugs[0];
    const page = await on.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    await page.goto(`${origin}/learn/${slug}/`);
    const total = await page.locator("li.step").count();
    if (!(await page.locator("[data-progress]").isVisible())) fail("progress box not shown with JavaScript");
    if ((await page.locator("[data-step-check]").count()) !== total) fail("not one done box per step");
    await page.locator("[data-step-check]").first().check();
    const want = EN["learn.progress.count"].replace("{done}", "1").replace("{total}", String(total));
    if (plain(await page.locator("[data-progress-count]").innerText()) !== want) fail("count did not update");
    await page.reload();
    if (!(await page.locator("[data-step-check]").first().isChecked())) fail("progress lost on reload");
    await page.goto(`${origin}/learn/`);
    const card = plain(await page.locator(`[data-journey-card="${slug}"] [data-card-progress]`).innerText());
    if (card !== want) fail(`index shows "${card}", expected "${want}"`);
    await page.goto(`${origin}/learn/${slug}/`);
    await page.locator("[data-progress-reset]").click();
    if (await page.locator("[data-step-check]").first().isChecked()) fail("clear did not clear");
    if (errors.length) fail("script errors: " + errors.join("; "));
    console.log(`  /learn/${slug}/: done box, reload, index count and clear work`);
    await page.close();
  }
  await on.close();

  // ---------------------------------------------------------------- 3. storage refused
  console.log("JavaScript on, storage refused");
  const blocked = await browser.newContext({ viewport: { width: 390, height: 900 } });
  watch(blocked);
  await blocked.addInitScript(() => {
    Object.defineProperty(window, "localStorage", { get() { throw new Error("storage refused"); } });
  });
  for (const p of ["/learn/", ...slugs.map((s) => `/learn/${s}/`)]) {
    const page = await blocked.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    await page.goto(origin + p);
    if (errors.length) fail(`${p}: script errors with storage refused: ${errors.join("; ")}`);
    if ((await page.locator("[data-step-check]").count()) !== 0) fail(`${p}: done boxes shown without storage`);
    if (p !== "/learn/" && (await page.locator("li.step").count()) < 1) fail(`${p}: steps missing`);
    await page.close();
  }
  console.log("  no errors, no controls, pages complete");
  await blocked.close();

  if (external.length) fail("requests left the local server: " + external.join(", "));
  await browser.close();
  server.close();
  console.log(failures.length ? `FAILED: ${failures.length}` :
    "OK: learn pages are complete with JavaScript off; progress works on the device and fails safe");
  process.exit(failures.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
