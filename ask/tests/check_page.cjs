#!/usr/bin/env node
/* Checks the ask page in a real browser, with JavaScript off and then on.
 *
 *   NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
 *     node ask/tests/check_page.cjs [site/dist] [--shots DIR]
 *
 * JS off: the page has one h1, the question box stays hidden, the "needs JavaScript"
 * note shows, the answered questions are listed and open as complete pages whose
 * claims show their status in words; nothing but the page and its CSS is loaded.
 * JS on: the box shows, the index loads only when the visitor starts, questions are
 * answered in the page (a list with its claims, a refusal, an ambiguous name and its
 * choices, a link from the address), and no request leaves the local server.
 * Expected wording is read from ask/i18n/en.json. Exit 1 on any failure.
 */
"use strict";
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const args = process.argv.slice(2);
const shotsAt = args.indexOf("--shots");
const shots = shotsAt >= 0 ? args.splice(shotsAt, 2)[1] : null;
const root = path.resolve(args[0] || path.join(__dirname, "..", "..", "site", "dist"));
const T = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "i18n", "en.json"), "utf8"));
const TYPES = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".json": "application/json" };

const server = http.createServer((req, res) => {
  const p = decodeURIComponent(req.url.split("?")[0].split("#")[0]);
  let f = path.join(root, p);
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end("not found"); }
  res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});

(async () => {
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();
  const failures = [];
  const fail = (msg) => { failures.push(msg); console.log("  FAIL " + msg); };
  const ok = (msg) => console.log("  ok   " + msg);
  if (shots) fs.mkdirSync(shots, { recursive: true });

  // ------------------------------------------------------------ JavaScript off
  {
    const ctx = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 900 } });
    const requests = [];
    ctx.on("request", (rq) => requests.push(rq.url()));
    const page = await ctx.newPage();
    console.log("JavaScript off: /ask/");
    const resp = await page.goto(origin + "/ask/", { waitUntil: "load" });
    if (resp.status() !== 200) fail(`/ask/: HTTP ${resp.status()}`);
    if ((await page.locator("h1").count()) !== 1) fail("expected one h1");
    if (await page.locator("#ask-form").isVisible()) fail("the question box shows without JavaScript");
    else ok("question box hidden");
    if (!(await page.locator("#ask-nojs").isVisible())) fail("the no-JavaScript note is not shown");
    else ok("no-JavaScript note shown");
    const cached = await page.locator(".cached-list a").count();
    if (cached < 20) fail(`only ${cached} answered questions listed`);
    else ok(`${cached} answered questions listed`);
    const bg = await page.evaluate(() => getComputedStyle(document.querySelector(".ask-nojs")).borderInlineStartWidth);
    if (bg === "0px") fail("ask.css not applied");
    if (shots) await page.screenshot({ path: path.join(shots, "nojs-ask.png"), fullPage: true });
    // an answer page and a refusal page
    const first = await page.locator(".cached-list a").first().getAttribute("href");
    await page.goto(origin + "/ask/" + first, { waitUntil: "load" });
    const answerText = await page.locator("main").innerText();
    if ((await page.locator("h1").count()) !== 1) fail(`${first}: expected one h1`);
    if (!(await page.locator(".answer .row").count())) fail(`${first}: no rows`);
    if (!answerText.includes(T["status.proposed"])) fail(`${first}: a proposed claim is not worded as "${T["status.proposed"]}"`);
    else ok(`${first}: rows with claims, status in words`);
    if (shots) await page.screenshot({ path: path.join(shots, "nojs-answer.png"), fullPage: false });
    await page.goto(origin + "/ask/", { waitUntil: "load" });
    const refusalHref = await page.locator(".cached h3:last-of-type + ul a").first().getAttribute("href");
    await page.goto(origin + "/ask/" + refusalHref, { waitUntil: "load" });
    if (!(await page.locator(".outcome-refusal .refusal-reason").count())) fail(`${refusalHref}: no refusal reason`);
    else ok(`${refusalHref}: refused with its reason`);
    const back = await page.locator(".back a").getAttribute("href");
    await page.goto(new URL(back, page.url()).href, { waitUntil: "load" });
    if (!page.url().endsWith("/ask/")) fail("the back link does not return to the ask page");
    const loaded = requests.filter((u) => !u.endsWith(".css") && !u.endsWith("/") && !u.endsWith(".html"));
    if (loaded.some((u) => u.endsWith(".js") || u.includes(".json"))) fail("script or index loaded with JavaScript off: " + loaded.join(", "));
    const external = requests.filter((u) => !u.startsWith(origin));
    if (external.length) fail("requests left the server: " + external.join(", "));
    await ctx.close();
  }

  // ------------------------------------------------------------ JavaScript on
  {
    const ctx = await browser.newContext({ javaScriptEnabled: true, viewport: { width: 390, height: 900 } });
    const requests = [];
    const errors = [];
    ctx.on("request", (rq) => requests.push(rq.url()));
    const page = await ctx.newPage();
    page.on("pageerror", (e) => errors.push(String(e)));
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    console.log("JavaScript on: /ask/");
    await page.goto(origin + "/ask/", { waitUntil: "load" });
    if (!(await page.locator("#ask-form").isVisible())) fail("the question box is hidden with JavaScript on");
    else ok("question box shown");
    if (await page.locator("#ask-nojs").isVisible()) fail("the no-JavaScript note shows with JavaScript on");
    if (requests.some((u) => u.includes("ask-index.json"))) fail("the index loaded before the visitor started");
    else ok("index not loaded before use");

    async function ask(q) {
      await page.fill("#ask-q", q);
      await page.press("#ask-q", "Enter");
      await page.waitForFunction((qq) => {
        const a = document.querySelector("#ask-answer .answer .asked");
        return a && a.textContent.includes(qq);
      }, q, { timeout: 15000 });
    }
    await ask("Who was at both Badr and Uhud?");
    const rows = await page.locator("#ask-answer ol.rows > li.row").count();
    if (rows !== 8) fail(`both Badr and Uhud: ${rows} rows, expected 8`);
    else ok("both Badr and Uhud: 8 rows");
    const txt = await page.locator("#ask-answer").innerText();
    if (!txt.includes(T["status.proposed"])) fail("live answer: proposed claims not worded as recorded, not yet reviewed");
    if (!(await page.evaluate(() => location.hash.startsWith("#q=")))) fail("the question is not kept in the address");
    else ok("question kept in the address (#q=)");
    if (shots) await page.screenshot({ path: path.join(shots, "js-answer.png"), fullPage: false });

    await ask("What is the ruling on music?");
    if (!(await page.locator("#ask-answer .outcome-refusal").count())) fail("ruling question not refused");
    else ok("ruling question refused with its reason");
    if (shots) await page.screenshot({ path: path.join(shots, "js-refusal.png"), fullPage: false });

    await ask("Relatives of Fatima");
    const choices = await page.locator("#ask-answer .outcome-ambiguous a[data-dsl]").count();
    if (choices < 2) fail(`ambiguous name: ${choices} choices`);
    else {
      await page.locator("#ask-answer .outcome-ambiguous a[data-dsl]").first().click();
      await page.waitForSelector("#ask-answer .outcome-answer", { timeout: 15000 });
      const dsl = await page.locator("#ask-answer code.dsl").textContent();
      if (!dsl.startsWith("relatives(")) fail(`choice ran ${dsl}`);
      else ok(`ambiguous name: ${choices} choices; choosing one runs ${dsl}`);
    }

    await page.locator(".ask-try button").first().click();
    await page.waitForFunction(() => document.querySelector("#ask-answer .outcome-answer, #ask-answer .outcome-refusal"), null, { timeout: 15000 });
    ok("a suggested question runs");

    const page2 = await ctx.newPage();
    page2.on("pageerror", (e) => errors.push(String(e)));
    await page2.goto(origin + "/ask/#q=" + encodeURIComponent("Who was the father of Aisha?"), { waitUntil: "load" });
    await page2.waitForSelector("#ask-answer .outcome-answer", { timeout: 15000 });
    if ((await page2.locator("#ask-answer ol.rows > li.row").count()) !== 1) fail("question from the address: expected one row");
    else ok("question from the address runs");

    const indexLoads = requests.filter((u) => u.includes("ask-index.json")).length;
    if (indexLoads < 1) fail("the index was never loaded");
    const external = requests.filter((u) => !u.startsWith(origin));
    if (external.length) fail("requests left the server: " + external.join(", "));
    else ok("no request left the server");
    if (errors.length) fail("script errors: " + errors.join(" | "));
    await ctx.close();
  }

  await browser.close();
  server.close();
  if (failures.length) {
    console.log(`FAILED: ${failures.length} problem(s)`);
    process.exit(1);
  }
  console.log("OK: the ask page works with JavaScript off and on");
})().catch((e) => { console.error(e); process.exit(1); });
