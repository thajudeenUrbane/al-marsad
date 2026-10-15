#!/usr/bin/env node
/* Search in a real browser, with JavaScript on and off.
 *
 *   NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
 *     node site/check_search.cjs [site/dist]
 *
 * JavaScript on: every query the slice-2 brief names finds Abu Bakr as the first result
 * (his page is found by his name in search.json, never by ID); the search box on another
 * page lands on the results; typing updates the results and the address; a query with no
 * match says what was searched, what the corpus holds and that it is unverified
 * (docs/05 section 3), never a blank.
 * JavaScript off: the search box still submits, and the search page lists every name A to
 * Z under a note that says why. In both modes no request may leave the local server.
 * Needs the `playwright` npm package and a Chromium it can launch. Exit 1 on any failure.
 */
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const root = path.resolve(process.argv[2] || path.join(__dirname, "dist"));
const EN = JSON.parse(fs.readFileSync(path.join(__dirname, "i18n", "en.json"), "utf8"));
const TYPES = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
                ".json": "application/json", ".ttl": "text/turtle; charset=utf-8" };
const QUERIES = ["Abu Bakr", "Abū Bakr", "abubakr", "ابو بكر", "أبو بكر"];
const NAME = "Abu Bakr as-Siddiq";   // his name as shown, from the graph label Abū Bakr al-Ṣiddīq

const server = http.createServer((req, res) => {
  let f = path.join(root, decodeURIComponent(req.url.split("?")[0]));
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end("not found"); }
  res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});

(async () => {
  const index = JSON.parse(fs.readFileSync(path.join(root, "search.json"), "utf8"));
  const abu = index.items.filter((it) => it.n === NAME);
  if (abu.length !== 1) throw new Error(`expected one item named ${NAME}, found ${abu.length}`);
  const abuHref = `${abu[0].u}/`;
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();
  const failures = [], external = [];
  const fail = (msg) => { failures.push(msg); console.log("  FAIL " + msg); };
  const context = async (js) => {
    const ctx = await browser.newContext({ javaScriptEnabled: js, viewport: { width: 390, height: 900 } });
    ctx.on("request", (rq) => { if (!rq.url().startsWith(origin)) external.push(rq.url()); });
    return ctx;
  };
  const firstResult = async (page) => {
    await page.waitForSelector("#search-results:not([hidden]), #search-empty:not([hidden])", { timeout: 10000 });
    const a = page.locator("#search-results li a").first();
    return (await a.count()) ? a.getAttribute("href") : null;
  };

  // ---------------------------------------------------------------- JavaScript on
  const on = await context(true);
  let page = await on.newPage();
  for (const q of QUERIES) {
    await page.goto(`${origin}/search/?q=${encodeURIComponent(q)}`);
    const href = await firstResult(page);
    const status = await page.locator("#search-status").innerText();
    const ok = href && href.endsWith(abuHref) && status.includes(q);
    console.log(`  JS on  ${JSON.stringify(q)} -> ${ok ? NAME : href} | ${status}`);
    if (!ok) fail(`query ${JSON.stringify(q)} did not list ${NAME} first`);
    if (await page.locator("#search-nojs").isVisible()) fail("the no-JavaScript note is still shown");
    if (await page.locator("#search-all").isVisible()) fail("the A-Z list is shown under results");
    if (/[؀-ۿ]/.test(q) && !(await page.locator("#search-results").innerText()).includes(EN["search.arabic_note"])) {
      fail(`query ${JSON.stringify(q)}: no note that Arabic is matched by sound`);
    }
  }
  // the search box on an entity page
  await page.goto(`${origin}/${abuHref}`);
  await page.fill("#site-q", "abubakr");
  await page.press("#site-q", "Enter");
  await page.waitForURL(/\/search\/\?q=abubakr$/);
  if (!(await firstResult(page) || "").endsWith(abuHref)) fail("the header search box did not reach the results");
  // typing on the search page updates the results and the address
  await page.fill("#search-q", "");
  await page.waitForFunction(() => !document.getElementById("search-all").hidden);
  await page.fill("#search-q", "أبو بكر");
  await page.waitForFunction(() => location.search.startsWith("?q=%D8%A3"), null, { timeout: 5000 }).catch(() => fail("typing did not update the address"));
  if (!(await firstResult(page) || "").endsWith(abuHref)) fail("typing did not update the results");
  // a query with no match: the empty-state rule
  await page.goto(`${origin}/search/?q=zzqx`);
  await page.waitForSelector("#search-empty:not([hidden])", { timeout: 10000 }).catch(() => fail("no empty state for zzqx"));
  const status = await page.locator("#search-status").innerText();
  const empty = await page.locator("#search-empty").innerText();
  console.log(`  JS on  "zzqx" -> ${status} | ${empty.slice(0, 90)}...`);
  if (status !== EN["search.none"].replace("{q}", "zzqx")) fail("the empty state does not say what was searched");
  if (!empty.includes(EN["search.unverified"]) && !/accepted by scholars/.test(empty)) fail("the empty state does not say the corpus is unverified");
  if (!/\d+ people/.test(empty) || !empty.includes(EN["search.empty_next"])) fail("the empty state does not say what the corpus holds");
  await page.close();
  await on.close();

  // ---------------------------------------------------------------- JavaScript off
  const off = await context(false);
  page = await off.newPage();
  await page.goto(`${origin}/${abuHref}`);
  await page.fill("#site-q", "Abu Bakr");
  await page.press("#site-q", "Enter");
  await page.waitForLoadState("load");
  const url = new URL(page.url());
  console.log(`  JS off "Abu Bakr" -> ${url.pathname}${url.search}`);
  if (url.pathname !== "/search/" || url.searchParams.get("q") !== "Abu Bakr") fail("the search box did not submit to search/ with JavaScript off");
  const note = await page.locator("#search-nojs").innerText().catch(() => "");
  if (!note.includes(EN["search.nojs"].slice(0, 40))) fail("no note explaining the A-Z fallback");
  if (!note.includes(EN["search.unverified"]) && !/accepted by scholars/.test(note)) fail("the fallback note does not say the corpus is unverified");
  if ((await page.locator("h1").count()) !== 1) fail("search page: not one h1");
  const link = page.locator(`#search-all a[href$="${abuHref}"]`);
  if (!(await link.count()) || !(await link.first().isVisible())) fail(`${NAME} is not in the A-Z list`);
  if (await page.locator("#search-results").isVisible()) fail("results shown without JavaScript");
  const rows = await page.locator("#search-all .index-list li").count();
  console.log(`  JS off A-Z list: ${rows} names; note: ${note.slice(0, 70)}...`);
  if (rows !== index.items.length) fail(`A-Z list has ${rows} names, the index ${index.items.length}`);
  await link.first().click();
  await page.waitForLoadState("load");
  if (!page.url().endsWith(abuHref)) fail("the A-Z link did not open his page");
  await page.close();
  await off.close();

  if (external.length) fail("requests left the local server: " + external.join(", "));
  await browser.close();
  server.close();
  console.log(failures.length ? `FAILED: ${failures.length}` : "OK: search finds Abu Bakr from every required spelling with JavaScript on; with it off the box submits to the A-Z list; no external requests");
  process.exit(failures.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
