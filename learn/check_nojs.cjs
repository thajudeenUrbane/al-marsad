#!/usr/bin/env node
/* Checks the learn pages in a real browser, driven by learn/data/pages.json.
 *
 *   NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
 *     node learn/check_nojs.cjs [site/dist [MORE_ROOTS ...]] [--shots DIR]
 *
 * Each root (a built site, for example a split build made with --step-budget) is checked:
 * 0. pages.json lists exactly the learn index.html files of the root.
 * 1. JavaScript off: every page loads and is complete: one h1, skip link, nav, licence
 *    footer, site.css, and no sideways scroll at 390 px. Per article[data-depth] (design §8,
 *    enforcement 4):
 *      discover          no .status, no draft banner, and every li.sentence (narration
 *                        and set-apart lines) has a .source;
 *      study, research   the draft banner and "Status:" in every li.claim.
 *    Every journey page: the rule, every step with its entity link, three depth links
 *    with one current, the pager and (page 1) the contents of a split depth, the anchor of
 *    its first stop; progress controls hidden, no form control. Links lead from the index
 *    to a journey, a step's entity page and back; a depth link lands on the page holding
 *    the stop; a contents link and learn/{slug}/#s-{key} reach a stop on another page.
 *    No request leaves the local server.
 * 2. JavaScript on: a step marked done survives a reload and is shared by every depth
 *    and page of its journey and by the index card; clearing clears it.
 * 3. JavaScript on but storage refused (as in some private windows): no error, no
 *    controls, no sideways scroll, the pages as in 1.
 * Pages are visited a few at a time (POOL), each in its own tab; the log lines keep the
 * order of pages.json. Needs the `playwright` npm package and a Chromium it can launch.
 * Exit 1 on any failure.
 */
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const args = process.argv.slice(2);
const shotsAt = args.indexOf("--shots");
const shots = shotsAt >= 0 ? args.splice(shotsAt, 2)[1] : null;
const roots = (args.length ? args : [path.join(__dirname, "..", "site", "dist")]).map((r) => path.resolve(r));
const EN = JSON.parse(fs.readFileSync(path.join(__dirname, "i18n", "en.json"), "utf8"));
const TYPES = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
  ".json": "application/json", ".ttl": "text/turtle; charset=utf-8" };

const POOL = 4;             // tabs open at once: each check is many small round trips to the browser
const failures = [];
const fail = (msg) => { failures.push(msg); console.log("  FAIL " + msg); };
const plain = (s) => s.replace(/\s+/g, " ").trim();
const DRAFT = plain(EN["learn.draft_banner"]);

// fn(item) for every item, POOL at a time; the log lines fn returns are printed in item order
async function eachPage(items, fn) {
  const logs = new Array(items.length);
  let next = 0;
  const worker = async () => {
    while (next < items.length) {
      const i = next++;
      logs[i] = await fn(items[i]);
    }
  };
  await Promise.all(Array.from({ length: Math.min(POOL, items.length) }, worker));
  for (const line of logs) if (line) console.log(line);
}

function serve(root) {
  const server = http.createServer((req, res) => {
    const p = decodeURIComponent(req.url.split("?")[0]);
    let f = path.join(root, p);
    if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
    if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
    if (!fs.existsSync(f)) { res.writeHead(404); return res.end("not found"); }
    res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" });
    fs.createReadStream(f).pipe(res);
  });
  return new Promise((r) => server.listen(0, "127.0.0.1", () => r(server)));
}

function htmlFiles(dir, rel = "") {
  let out = [];
  for (const name of fs.readdirSync(path.join(dir, rel)).sort()) {
    const sub = rel ? `${rel}/${name}` : name;
    if (fs.statSync(path.join(dir, sub)).isDirectory()) out = out.concat(htmlFiles(dir, sub));
    else if (name === "index.html") out.push(sub);
  }
  return out;
}

async function noSideways(page, p) {
  const [sw, cw] = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
  if (sw > cw) fail(`${p}: scrolls sideways at ${cw} px (scrollWidth ${sw})`);
}

async function frame(page, p) {
  if ((await page.locator("h1").count()) !== 1) fail(`${p}: not exactly one h1`);
  if ((await page.locator('a[href="#main"]').count()) !== 1) fail(`${p}: no skip link`);
  if ((await page.locator("header nav a").count()) < 5) fail(`${p}: navigation links missing`);
  if ((await page.locator("footer a").count()) < 4) fail(`${p}: licence footer links missing`);
  const font = await page.locator("body").evaluate((el) => getComputedStyle(el).fontFamily);
  if (!/system-ui/.test(font)) fail(`${p}: site.css not applied (${font})`);
  await noSideways(page, p);
}

async function journeyPage(page, p, entry) {
  const article = page.locator("article[data-depth]");
  if ((await article.count()) !== 1) { fail(`${p}: no article[data-depth]`); return; }
  const depth = await article.getAttribute("data-depth");
  if (depth !== entry.depth) fail(`${p}: data-depth ${depth}, pages.json says ${entry.depth}`);
  const total = parseInt(await article.getAttribute("data-total"), 10);
  const keys = (await article.getAttribute("data-steps")).split(" ").filter(Boolean);
  if (!(total > 0) || keys.length !== total) fail(`${p}: data-total ${total} and data-steps ${keys.length} differ`);
  const text = plain(await page.locator("main").innerText());
  if (!text.includes(EN["learn.rule.heading"])) fail(`${p}: the rule is not shown`);
  const claims = page.locator("li.claim");
  const nc = await claims.count();
  const sentences = page.locator("li.sentence");
  const ns = await sentences.count();
  if (depth === "discover") {
    if ((await page.locator(".status").count()) !== 0) fail(`${p}: a .status on a Discover page`);
    if (text.includes(DRAFT) || text.includes("Status:")) fail(`${p}: review status on a Discover page`);
    for (let i = 0; i < ns; i++) {
      if ((await sentences.nth(i).locator(".source").count()) < 1) fail(`${p}: sentence ${i + 1} has no .source`);
    }
  } else {
    if (!text.includes(DRAFT)) fail(`${p}: no draft banner`);
    for (let i = 0; i < nc; i++) {
      if (!/Status:/.test(await claims.nth(i).textContent())) fail(`${p}: claim ${i + 1} has no status label`);
    }
  }
  const steps = page.locator("li.step");
  const n = await steps.count();
  if (n + (await page.locator("li.apart").count()) < 1) fail(`${p}: no stops`);
  for (let i = 0; i < n; i++) {
    const step = steps.nth(i);
    if (!(await step.isVisible())) fail(`${p}: step ${i + 1} not visible`);
    if ((await step.locator("h3.step-title a").count()) !== 1) fail(`${p}: step ${i + 1} has no entity link`);
  }
  const depths = page.locator("nav.journey-depths a");
  if ((await depths.count()) !== 3) fail(`${p}: not three depth links`);
  if ((await page.locator('nav.journey-depths a[aria-current="page"]').count()) !== 1) fail(`${p}: no current depth`);
  if ((await page.locator(`[id="s-${entry.first}"]`).count()) !== 1) fail(`${p}: no anchor for its first stop`);
  if (entry.pages > 1 && (await page.locator("nav.journey-pager").count()) !== 1) fail(`${p}: split, but no pager`);
  if ((await page.locator("nav.journey-contents").count()) !== (entry.pages > 1 && entry.page === 1 ? 1 : 0)) {
    fail(`${p}: the contents list belongs on page 1 of a split depth only`);
  }
  if (await page.locator("[data-progress]").isVisible()) fail(`${p}: progress box visible without JavaScript`);
  if ((await page.locator("input").count()) !== 0) fail(`${p}: form controls without JavaScript`);
  const rule = await page.locator(".journey-rule").evaluate((el) => getComputedStyle(el).borderTopStyle);
  if (rule !== "solid") fail(`${p}: learn.css not applied`);
  return { depth, n, nc, ns, keys };
}

async function checkRoot(browser, root) {
  console.log(`== ${root}`);
  const manifest = path.join(root, "learn", "data", "pages.json");
  if (!fs.existsSync(manifest)) { fail(`${manifest} not found: run site/build.py, then learn/build_learn.py`); return; }
  const pages = JSON.parse(fs.readFileSync(manifest, "utf8")).pages;
  const listed = pages.map((e) => e.file).sort();
  const found = htmlFiles(root, "learn").sort();
  if (JSON.stringify(listed) !== JSON.stringify(found)) {
    fail(`pages.json lists ${listed.length} pages, learn/ holds ${found.length}: ` +
      `${listed.filter((f) => !found.includes(f)).concat(found.filter((f) => !listed.includes(f))).slice(0, 5).join(", ")}`);
  }
  const server = await serve(root);
  const origin = `http://127.0.0.1:${server.address().port}`;
  const external = [];
  const watch = (ctx) => ctx.on("request", (rq) => { if (!rq.url().startsWith(origin)) external.push(rq.url()); });
  const journeys = pages.filter((e) => e.kind === "journey");
  const slugs = [...new Set(journeys.map((e) => e.journey))].sort();
  const url = (e) => `${origin}/${e.path}`;

  // ---------------------------------------------------------------- 1. JavaScript off
  console.log("JavaScript off");
  const off = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 900 } });
  watch(off);
  await eachPage(pages, async (e) => {
    const p = "/" + e.path;
    const page = await off.newPage();
    const resp = await page.goto(origin + p, { waitUntil: "load" });
    if (resp.status() !== 200) { fail(`${p}: HTTP ${resp.status()}`); await page.close(); return null; }
    await frame(page, p);
    const text = plain(await page.locator("main").innerText());
    let line = null;
    if (e.kind === "journey") {
      const r = await journeyPage(page, p, e);
      if (r) line = `${p} -> ${r.depth} page ${e.page}/${e.pages}: ${r.n} steps, ${r.nc} claims, ${r.ns} sentences`;
    } else if (e.kind === "index") {
      if ((await page.locator(".status").count()) !== 0 || text.includes(EN["learn.draft_banner"])) fail(`${p}: review status on the index`);
      for (const slug of slugs) {
        if ((await page.locator(`[data-journey-card="${slug}"] .depth-links a`).count()) !== 3) fail(`${p}: ${slug} has not three depth links`);
      }
      line = `${p} -> index, ${slugs.length} journeys`;
    } else {
      const n = await page.locator("li.question").count();
      if (n === 0 && !text.includes(EN["learn.practice.empty"])) fail(`${p}: empty bank not explained`);
      line = `${p} -> practice, ${n} questions`;
    }
    if (shots) {
      fs.mkdirSync(shots, { recursive: true });
      await page.screenshot({ path: path.join(shots, "nojs" + p.replace(/[^a-z0-9]+/gi, "_") + ".png"), fullPage: true });
    }
    await page.close();
    return line;
  });

  // follow links without JavaScript: index -> journey -> entity page -> back to the index
  {
    const page = await off.newPage();
    await page.goto(origin + "/learn/");
    await page.locator(".journey-cards h3 a").first().click();
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
  // a depth link lands on the page of that depth holding this page's first stop
  await eachPage(journeys.filter((x) => x.page === 1), async (e) => {
    const page = await off.newPage();
    await page.goto(url(e));
    const other = page.locator('nav.journey-depths a:not([aria-current])').first();
    await other.click();
    await page.waitForLoadState("load");
    const hash = new URL(page.url()).hash;
    if (hash !== `#s-${e.first}` || (await page.locator(`[id="s-${e.first}"]`).count()) !== 1) {
      fail(`/${e.path}: a depth link did not land on its first stop (${page.url()})`);
    }
    await page.close();
    return null;
  });
  // a split depth: a contents link and learn/{slug}/...#s-{key} reach a stop on another page
  let splitChecked = 0;
  for (const e of journeys.filter((x) => x.pages > 1 && x.page === 1)) {
    const later = journeys.find((x) => x.journey === e.journey && x.depth === e.depth && x.page === 2);
    const page = await off.newPage();
    await page.goto(`${url(e)}#s-${later.first}`);
    const entry = page.locator(`nav.journey-contents li[id="s-${later.first}"] a`);
    if ((await entry.count()) !== 1) fail(`/${e.path}#s-${later.first}: no contents anchor for a stop on page 2`);
    else {
      await entry.click();
      await page.waitForLoadState("load");
      if (!page.url().endsWith(`/${later.path}#s-${later.first}`)) fail(`contents link went to ${page.url()}`);
      if ((await page.locator(`li [id="s-${later.first}"], li[id="s-${later.first}"]`).count()) < 1) fail(`${page.url()}: stop not on its page`);
      const pager = page.locator('nav.journey-pager a[aria-current="page"]');
      if ((await pager.count()) !== 1 || plain(await pager.innerText()) !== "2") fail(`${page.url()}: the pager does not mark page 2`);
    }
    splitChecked++;
    await page.close();
  }
  console.log(`  links: index, entity pages, depth links${splitChecked ? `, contents and pager on ${splitChecked} split depths` : ""}`);
  await off.close();

  // ---------------------------------------------------------------- 2. JavaScript on
  console.log("JavaScript on");
  const on = await browser.newContext({ viewport: { width: 390, height: 900 } });
  watch(on);
  {
    // a journey with a split depth if there is one, so that progress is seen across pages too
    const split = journeys.find((x) => x.pages > 1);
    const slug = split ? split.journey : slugs[0];
    const door = journeys.find((x) => x.journey === slug && x.door && x.page === 1);
    const others = journeys.filter((x) => x.journey === slug && x !== door && (x.page === 1 || x === split ||
      (split && x.depth === split.depth && x.page === 2)));
    const page = await on.newPage();
    const errors = [];
    page.on("pageerror", (err) => errors.push(String(err)));
    await page.goto(url(door));
    const total = parseInt(await page.locator("article").getAttribute("data-total"), 10);
    if (!(await page.locator("[data-progress]").isVisible())) fail("progress box not shown with JavaScript");
    if ((await page.locator("[data-step-check]").count()) !== (await page.locator("li.step").count())) fail("not one done box per step");
    await page.locator("[data-step-check]").first().check();
    const want = EN["learn.progress.count"].replace("{done}", "1").replace("{total}", String(total));
    if (plain(await page.locator("[data-progress-count]").innerText()) !== want) fail("count did not update");
    await page.reload();
    if (!(await page.locator("[data-step-check]").first().isChecked())) fail("progress lost on reload");
    for (const e of others) {
      await page.goto(url(e));
      const got = plain(await page.locator("[data-progress-count]").innerText());
      if (got !== want) fail(`/${e.path}: shows "${got}", expected "${want}" (progress shared by depths and pages)`);
      if (e.first === door.first && !(await page.locator(`li.step[data-step="${door.first}"] [data-step-check]`).isChecked())) {
        fail(`/${e.path}: the step done at ${door.depth} is not done here`);
      }
    }
    await page.goto(`${origin}/learn/`);
    const card = plain(await page.locator(`[data-journey-card="${slug}"] [data-card-progress]`).innerText());
    if (card !== want) fail(`index shows "${card}", expected "${want}"`);
    await page.goto(url(others[others.length - 1] || door));
    await page.locator("[data-progress-reset]").click();
    await page.goto(url(door));
    if (await page.locator("[data-step-check]").first().isChecked()) fail("clear did not clear");
    if (errors.length) fail("script errors: " + errors.join("; "));
    console.log(`  /${door.path}: done box, reload, ${others.length} other pages of the journey, index count and clear work`);
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
  await eachPage(pages.filter((x) => x.kind !== "practice"), async (e) => {
    const p = "/" + e.path;
    const page = await blocked.newPage();
    const errors = [];
    page.on("pageerror", (err) => errors.push(String(err)));
    await page.goto(origin + p);
    if (errors.length) fail(`${p}: script errors with storage refused: ${errors.join("; ")}`);
    if ((await page.locator("[data-step-check]").count()) !== 0) fail(`${p}: done boxes shown without storage`);
    await noSideways(page, p);
    if (e.kind === "journey" && (await page.locator("li.step, li.apart").count()) < 1) fail(`${p}: stops missing`);
    await page.close();
    return null;
  });
  console.log("  no errors, no controls, no sideways scroll, pages complete");
  await blocked.close();
  if (external.length) fail("requests left the local server: " + external.join(", "));
  server.close();
}

(async () => {
  const browser = await chromium.launch();
  for (const root of roots) await checkRoot(browser, root);
  await browser.close();
  console.log(failures.length ? `FAILED: ${failures.length}` :
    "OK: learn pages are complete with JavaScript off at every depth; progress works on the device and fails safe");
  process.exit(failures.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
