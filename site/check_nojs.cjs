#!/usr/bin/env node
/* Loads sample pages with JavaScript switched off and checks they are complete:
 * one h1, the skip link and nav, claims with their status text, working internal links,
 * the stylesheet applied, and no request leaves the local server.
 *
 *   NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
 *     node site/check_nojs.cjs [site/dist] [--shots DIR]
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
const root = path.resolve(args[0] || path.join(__dirname, "dist"));
const TYPES = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".ttl": "text/turtle; charset=utf-8" };

const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split("?")[0]);
  let f = path.join(root, p);
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end("not found"); }
  res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});

function firstDir(kind) {
  const d = path.join(root, kind);
  return fs.readdirSync(d).filter((n) => fs.statSync(path.join(d, n)).isDirectory()).sort()[0];
}

(async () => {
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 900 } });
  const failures = [];
  const external = [];
  ctx.on("request", (rq) => { if (!rq.url().startsWith(origin)) external.push(rq.url()); });
  const fail = (msg) => { failures.push(msg); console.log("  FAIL " + msg); };

  // find a person page with stories, and a story page, from the generated site
  const pages = ["/", "/person/", "/story/", "/glossary/"];
  const withStories = fs.readdirSync(path.join(root, "person")).filter((n) => fs.existsSync(path.join(root, "person", n, "index.html")))
    .find((n) => /id="s-stories"/.test(fs.readFileSync(path.join(root, "person", n, "index.html"), "utf8")));
  if (withStories) pages.push(`/person/${withStories}/`);
  for (const k of ["story", "event", "place", "group"]) pages.push(`/${k}/${firstDir(k)}/`);

  for (const p of pages) {
    const page = await ctx.newPage();
    const resp = await page.goto(origin + p, { waitUntil: "load" });
    console.log(`${p} -> ${resp.status()}`);
    if (resp.status() !== 200) fail(`${p}: HTTP ${resp.status()}`);
    const h1 = await page.locator("h1").count();
    if (h1 !== 1) fail(`${p}: ${h1} h1 elements`);
    if ((await page.locator('a[href="#main"]').count()) !== 1) fail(`${p}: no skip link`);
    if ((await page.locator("header nav a").count()) < 5) fail(`${p}: navigation links missing`);
    if ((await page.locator("footer a").count()) < 4) fail(`${p}: licence footer links missing`);
    const body = await page.locator("body").evaluate((el) => getComputedStyle(el).backgroundColor + "|" + getComputedStyle(el).fontFamily).catch(() => null);
    if (!body || !/system-ui/.test(body)) fail(`${p}: stylesheet not applied (${body})`);
    const jsOn = await page.evaluate(() => typeof navigator !== "undefined").catch(() => "blocked");
    if (/\/(person|story|event|place|group)\/[^/]+\/$/.test(p)) {
      const text = await page.locator("main").innerText();
      if (!/Coverage:/.test(text)) fail(`${p}: coverage label missing`);
      if (/id="s-/.test(await page.content()) && !/Status:/.test(text)) fail(`${p}: claims without a status label`);
    }
    if (shots) {
      fs.mkdirSync(shots, { recursive: true });
      await page.screenshot({ path: path.join(shots, p.replace(/[^a-z0-9]+/gi, "_") + ".png"), fullPage: true });
    }
    await page.close();
  }

  // follow a link from a person page to a story and back to the index, still without JS
  if (withStories) {
    const page = await ctx.newPage();
    await page.goto(`${origin}/person/${withStories}/`);
    await page.locator("#s-stories a[href*='/story/']").first().click();
    await page.waitForLoadState("load");
    if (!/\/story\/[^/]+\/$/.test(page.url())) fail("link to a story did not land on a story page");
    if (!(await page.locator(".banner").innerText()).includes("Draft")) fail("story page has no draft banner");
    await page.locator('nav.breadcrumb a[href$="story/"]').click();
    await page.waitForLoadState("load");
    if (!/\/story\/$/.test(page.url())) fail("breadcrumb to the story index failed");
    await page.close();
  }
  if (external.length) fail("requests left the local server: " + external.join(", "));
  await browser.close();
  server.close();
  console.log(failures.length ? `FAILED: ${failures.length}` : "OK: pages render and navigate with JavaScript off, no external requests");
  process.exit(failures.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
