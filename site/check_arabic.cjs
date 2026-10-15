#!/usr/bin/env node
/* The Arabic interface (site/dist/ar/) in a real browser, at phone width (390 x 844).
 *
 *   NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
 *     node site/check_arabic.cjs [site/dist] [--shots DIR]
 *
 * JavaScript off: a sample of Arabic pages is right to left (html lang="ar" dir="rtl", the
 * computed direction too), does not scroll sideways, has its Arabic stylesheet and font
 * stack, one h1, the draft notice in the footer, mirrored breadcrumb arrows, hreflang
 * alternates, and a language switch that opens the same page in English and back.
 * JavaScript on: Arabic search (Latin and Arabic queries, Arabic counts and notes) and
 * the thread view (recorded names marked lang="en", Arabic plural in the lead).
 * No request may leave the local server. Exit 1 on any failure.
 */
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const args = process.argv.slice(2);
const shotsAt = args.indexOf("--shots");
const shots = shotsAt >= 0 ? args.splice(shotsAt, 2)[1] : null;
const root = path.resolve(args[0] || path.join(__dirname, "dist"));
const AR = JSON.parse(fs.readFileSync(path.join(__dirname, "i18n", "ar.json"), "utf8"));
const TYPES = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
                ".json": "application/json", ".ttl": "text/turtle; charset=utf-8" };
const ARABIC_WORDS = /[؀-ۿ]/;

const server = http.createServer((req, res) => {
  let f = path.join(root, decodeURIComponent(req.url.split("?")[0]));
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end("not found"); }
  res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});

function firstDir(kind) {
  const d = path.join(root, "ar", kind);
  return fs.readdirSync(d).filter((n) => fs.statSync(path.join(d, n)).isDirectory()).sort()[0];
}

(async () => {
  const index = JSON.parse(fs.readFileSync(path.join(root, "search.json"), "utf8"));
  const abu = index.items.find((it) => it.n === "Abu Bakr as-Siddiq");
  if (!abu) throw new Error("Abu Bakr as-Siddiq is not in search.json");
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();
  const failures = [], external = [];
  const fail = (msg) => { failures.push(msg); console.log("  FAIL " + msg); };
  const context = (js) => browser.newContext({ javaScriptEnabled: js, viewport: { width: 390, height: 844 } })
    .then((ctx) => { ctx.on("request", (rq) => { if (!rq.url().startsWith(origin)) external.push(rq.url()); }); return ctx; });
  const noSideways = async (page, label) => {
    const w = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
    if (w[0] > w[1] + 1) fail(`${label}: scrolls sideways (${w[0]} > ${w[1]})`);
  };
  const shot = async (page, label) => {
    if (!shots) return;
    fs.mkdirSync(shots, { recursive: true });
    await page.screenshot({ path: path.join(shots, label.replace(/[^a-z0-9]+/gi, "_") + ".png"), fullPage: true });
  };

  // ---------------------------------------------------------------- JavaScript off
  const off = await context(false);
  const pages = ["/ar/", "/ar/person/", "/ar/story/", "/ar/glossary/", "/ar/study/", "/ar/research/",
                 "/ar/search/?q=Abu+Bakr", `/ar/${abu.u}/`];
  for (const k of ["story", "event", "place", "group"]) pages.push(`/ar/${k}/${firstDir(k)}/`);
  for (const p of pages) {
    const page = await off.newPage();
    const resp = await page.goto(origin + p, { waitUntil: "load" });
    console.log(`${p} -> ${resp.status()}`);
    if (resp.status() !== 200) { fail(`${p}: HTTP ${resp.status()}`); await page.close(); continue; }
    const root_ = await page.evaluate(() => ({
      lang: document.documentElement.lang, dir: document.documentElement.dir,
      computed: getComputedStyle(document.documentElement).direction,
      font: getComputedStyle(document.body).fontFamily, h1: document.querySelectorAll("h1").length,
      skip: document.querySelectorAll('a[href="#main"]').length,
      alternates: [...document.querySelectorAll('link[rel="alternate"]')].map((l) => l.hreflang + "=" + l.getAttribute("href")),
    }));
    if (root_.lang !== "ar" || root_.dir !== "rtl") fail(`${p}: html is lang=${root_.lang} dir=${root_.dir}`);
    if (root_.computed !== "rtl") fail(`${p}: computed direction is ${root_.computed}`);
    if (!/Noto Sans Arabic/.test(root_.font)) fail(`${p}: the Arabic font stack is not applied (${root_.font})`);
    if (root_.h1 !== 1) fail(`${p}: ${root_.h1} h1 elements`);
    if (root_.skip !== 1) fail(`${p}: no skip link`);
    if (root_.alternates.length !== 2) fail(`${p}: expected two hreflang alternates, found ${root_.alternates.length}`);
    await noSideways(page, p);
    const foot = await page.locator("footer").innerText();
    if (!foot.includes(AR["footer.ar_draft"]) || !foot.includes(AR["footer.ar_draft_en"])) fail(`${p}: the footer does not say the Arabic text is a draft`);
    if (!ARABIC_WORDS.test(await page.locator("main h1").innerText() + await page.locator("header nav").innerText())) fail(`${p}: no Arabic in the heading or navigation`);
    if (/^\/ar\/(person|story|event|place|group)\/[^/]+\/$/.test(p)) {
      const sep = await page.evaluate(() => {
        const li = document.querySelector(".breadcrumb li + li");
        return li ? getComputedStyle(li, "::before").content : null;
      });
      if (sep !== '"‹"') fail(`${p}: breadcrumb separator is ${sep}, expected a mirrored arrow`);
      const named = await page.locator("main h1 [lang=en]").count();
      if (!named && !ARABIC_WORDS.test(await page.locator("main h1").innerText())) fail(`${p}: the recorded name is not marked lang=en`);
    }
    if (p === "/ar/") {
      // the views are English only for now: each link is labelled and says so with hreflang
      const hub = await page.evaluate(() => [...document.querySelectorAll(".hub-list a.hub-name[hreflang=en]")]
        .map((a) => !!a.parentElement.querySelector(".english-only")));
      if (hub.some((x) => !x)) fail(`${p}: a link to an English-only view carries no label`);
      if ((await page.locator(".banner").innerText()).length < 20) fail(`${p}: no note on what the Arabic interface covers`);
    }
    // the switch: same page in English, and back
    const sw = page.locator("a.lang-switch");
    if ((await sw.count()) !== 1) { fail(`${p}: no language switch`); await page.close(); continue; }
    await shot(page, p);
    await sw.click();
    await page.waitForLoadState("load");
    const want = p.replace(/^\/ar\//, "/");
    if (new URL(page.url()).pathname !== want.split("?")[0]) fail(`${p}: the switch went to ${page.url()}`);
    const en = await page.evaluate(() => [document.documentElement.lang, document.documentElement.dir]);
    if (en[0] !== "en" || en[1] !== "ltr") fail(`${p}: the English twin is lang=${en[0]} dir=${en[1]}`);
    await page.locator("a.lang-switch").click();
    await page.waitForLoadState("load");
    if (new URL(page.url()).pathname !== p.split("?")[0]) fail(`${p}: the switch back went to ${page.url()}`);
    await page.close();
  }
  // an English page links its Arabic twin too
  {
    const page = await off.newPage();
    await page.goto(`${origin}/${abu.u}/`);
    const href = await page.locator("a.lang-switch").getAttribute("href");
    const lang = await page.locator("a.lang-switch").getAttribute("lang");
    if (lang !== "ar" || !href.endsWith(`ar/${abu.u}/`)) fail(`/${abu.u}/: the switch is ${href} (${lang})`);
    await noSideways(page, `/${abu.u}/`);
    await page.close();
  }

  // ---------------------------------------------------------------- JavaScript on
  const on = await context(true);
  {
    const page = await on.newPage();
    await page.goto(`${origin}/ar/search/`);
    const run = async (q) => {
      await page.fill("#search-q", q);
      await page.waitForTimeout(500);   // the search waits 150 ms after the last key
      await page.waitForSelector("#search-results:not([hidden]), #search-empty:not([hidden])", { timeout: 10000 });
      return { first: await page.locator("#search-results li a").first().getAttribute("href").catch(() => null),
               status: await page.locator("#search-status").innerText() };
    };
    for (const q of ["Abu Bakr", "أبو بكر"]) {
      const r = await run(q);
      if (!r.first || !r.first.endsWith(`${abu.u}/`)) fail(`ar search "${q}": first result is ${r.first}`);
      if (!/نتيجة|نتائج|نتيجتان/.test(r.status)) fail(`ar search "${q}": the count is not in Arabic: ${r.status}`);
    }
    const none = await run("zzzzqx");
    if (!none.status.includes("لا اسم يطابق")) fail(`ar search with no match says: ${none.status}`);
    if (!ARABIC_WORDS.test(await page.locator("#search-empty").innerText())) fail("ar search with no match: the note is not in Arabic");
    await noSideways(page, "/ar/search/ (results)");
    await run("Abu Bakr");
    await shot(page, "ar-search-results");
    await page.close();
  }
  {
    const page = await on.newPage();
    await page.goto(`${origin}/ar/${abu.u}/`);
    await page.locator(".thread-open").click();
    await page.waitForSelector("#thread-view:not([hidden]) .thread-lead", { timeout: 10000 });
    const lead = await page.locator(".thread-lead").innerText();
    if (!/لحظة|لحظات|لحظتان/.test(lead)) fail(`ar thread: the lead is not in Arabic: ${lead}`);
    if ((await page.locator("#thread-view h1[lang=en]").count()) !== 1) fail("ar thread: the recorded name is not marked lang=en");
    if ((await page.locator("#thread-view .moment a[lang=en]").count()) < 1) fail("ar thread: names in the moments are not marked lang=en");
    await noSideways(page, "/ar/<person>/ (thread)");
    await shot(page, "ar-thread");
    await page.locator("#thread-view a[data-follow]").first().click();
    await page.waitForSelector(".thread-path", { timeout: 10000 });
    if (!ARABIC_WORDS.test(await page.locator(".thread-path-label").innerText())) fail("ar thread: the path label is not in Arabic");
    await noSideways(page, "/ar/<person>/ (thread, followed)");
    await page.keyboard.press("Escape");
    await page.close();
  }

  if (external.length) fail("requests left the local server: " + external.join(", "));
  await browser.close();
  server.close();
  console.log(failures.length ? `FAILED: ${failures.length}` : "OK: the Arabic pages are right to left, fit 390 px, switch language both ways, search and thread work in Arabic");
  process.exit(failures.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
