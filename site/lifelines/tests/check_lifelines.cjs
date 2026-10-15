#!/usr/bin/env node
/* Loads the Lifelines page in Chromium and checks it works: it renders, makes no request
 * beyond the local server, weighs at most 2 MB, the toggles work, a connector and a line
 * open their details, the table alternative is not empty, and a 390 x 844 phone gets no
 * horizontal page scroll. Also loads it once as a plain file (published on its own).
 *
 *   NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
 *     node site/lifelines/tests/check_lifelines.cjs [site/dist] [--shots DIR]
 *
 * Exit 1 on any failure.
 */
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const args = process.argv.slice(2);
const shotsAt = args.indexOf("--shots");
const shots = shotsAt >= 0 ? args.splice(shotsAt, 2)[1] : null;
const root = path.resolve(args[0] || path.join(__dirname, "..", "..", "dist"));
const pageFile = path.join(root, "lifelines", "index.html");
const MAX = 2000000;
const failures = [];
function check(ok, msg) { if (!ok) { failures.push(msg); console.log("FAIL", msg); } else { console.log("ok  ", msg); } }

const server = http.createServer((req, res) => {
  const p = decodeURIComponent(req.url.split("?")[0]);
  let f = path.join(root, p);
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end("not found"); }
  res.writeHead(200, { "content-type": f.endsWith(".html") ? "text/html; charset=utf-8" : "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});

async function open(browser, url, vp, touch) {
  const page = await browser.newPage({ viewport: vp, hasTouch: !!touch, deviceScaleFactor: 1 });
  const external = [], errors = [];
  page.on("request", (r) => {
    const u = r.url();
    if (!(u.startsWith("http://127.0.0.1") || u.startsWith("file://") || u.startsWith("data:") || u.startsWith("about:"))) external.push(u);
  });
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  await page.goto(url, { waitUntil: "load" });
  await page.waitForTimeout(300);
  return { page, external, errors };
}

(async () => {
  check(fs.existsSync(pageFile), `page exists: ${pageFile}`);
  if (!fs.existsSync(pageFile)) { process.exit(1); }
  const bytes = fs.statSync(pageFile).size;
  check(bytes <= MAX, `page weighs ${bytes} bytes (limit ${MAX})`);
  const html = fs.readFileSync(pageFile, "utf8");
  check(!/<(script|link|img|iframe)[^>]+(src|href)=["']?https?:/i.test(html), "no external script, stylesheet, image or frame in the HTML");
  const data = JSON.parse(html.split('<script type="application/json" id="ll-data">')[1].split("</script>")[0]);

  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();

  // ---- desktop
  const { page, external, errors } = await open(browser, `${origin}/lifelines/`, { width: 1366, height: 900 });
  check(await page.locator("svg.plot").count() === 1, "chart renders (svg.plot)");
  const nLines = await page.locator("svg.plot g.pl").count();
  const nBase = data.people.filter((p) => p.v.b).length;
  check(nLines === nBase, `one line per person with a sourced date: ${nLines} drawn, ${nBase} in the data`);
  check(await page.locator(".names button").count() === nBase, "one name per line in the name column");
  const rows = await page.locator(".ll-people tbody tr:not([hidden])").count();
  check(nBase === 0 || rows > 0, `table alternative not empty (${rows} rows)`);
  check(await page.locator("#undated-sec li").count() === data.undated.length, "undated list matches the data");
  const orient = await page.locator("#ll-count").textContent();
  check(/Showing \d+ of \d+/.test(orient), `orientation shown: "${orient.trim().slice(0, 70)}..."`);
  if (shots) await page.screenshot({ path: path.join(shots, "desktop-date.png") });

  // connector -> details
  const conns = page.locator("svg.plot g.ev");
  if (await conns.count()) {
    await conns.first().focus();
    await page.keyboard.press("Enter");
    await page.waitForTimeout(100);
    check(await page.locator("#ll-details").isVisible(), "a connector opens its details (keyboard)");
    const det = await page.locator("#ll-details").textContent();
    check(/Status:/.test(det) && /computed|birth not recorded/.test(det), "event details give each claim's status and a computed age");
    if (shots) await page.screenshot({ path: path.join(shots, "desktop-event.png") });
    await page.keyboard.press("Escape");
    check(await page.locator("#ll-details").isHidden(), "Escape closes the details");
  } else {
    console.log("note: no connector on the chart with today's data");
  }
  // line -> details
  if (nBase) {
    await page.locator(".names button").first().click();
    await page.waitForTimeout(100);
    const det = await page.locator("#ll-details").textContent();
    check(/Born/.test(det) && /Died/.test(det) && /Status:/.test(det), "a line opens the person's dates with sources and status");
    await page.keyboard.press("Escape");
  }
  // toggles
  await page.locator('label:has(input[name="align"][value="age"])').click();
  await page.waitForTimeout(900);
  check(await page.locator("svg.plot.m-age").count() === 1, "By age alignment applied (morph finished)");
  check(/by age/.test(await page.locator("#ll-count").textContent()), "orientation says the alignment");
  check((await page.locator("svg.plot g.ev").count()) === 0 || (await page.locator('svg.plot g.ev[opacity="0.000"]').count()) === (await page.locator("svg.plot g.ev").count()),
    "no connectors are drawn by age (no slanted lines)");
  if (shots) await page.screenshot({ path: path.join(shots, "desktop-age.png") });
  await page.locator('label:has(input[name="units"][value="solar"])').click();
  await page.waitForTimeout(200);
  check(/solar/.test(await page.locator("#ll-count").textContent()) && /solar/.test(await page.locator(".corner").textContent()),
    "units toggle: solar years labelled");
  await page.locator('label:has(input[name="align"][value="date"])').click();
  await page.waitForTimeout(900);
  check(await page.locator("svg.plot.m-age").count() === 0, "back to By date");
  await page.locator('label:has(input[name="align"][value="place"])').click();
  await page.waitForTimeout(150);
  const withPlace = data.people.filter((p) => p.v.b && !p.v.b.ages_only && (p.pp || []).length).length;
  check(await page.locator("svg.plot.m-place").count() === 1, "By place draws place lanes");
  check(await page.locator("svg.plot.m-place .lane-none").count() === 1, "By place keeps a 'place not recorded' lane");
  check(await page.locator("svg.plot.m-place g.pp").count() === data.people.filter((p) => p.v.b && !p.v.b.ages_only).length,
    "By place: every dated line is in the neutral lane");
  check(await page.locator("svg.plot.m-place .exc, svg.plot.m-place .res").count() >= withPlace, `By place: a step into a lane for each dated presence (${withPlace} people)`);
  await page.locator('label:has(input[name="align"][value="date"])').click();
  await page.waitForTimeout(150);
  const drawnLinks = (data.tl || []).filter((l) => l.f !== null && l.t !== null && data.people[l.f].v.b && data.people[l.t].v.b).length;
  if (drawnLinks) {
    await page.selectOption('select[name="order"]', "tm");
    await page.waitForTimeout(100);
    check(await page.locator("svg.plot g.tie.tm").count() === drawnLinks, `transmission order: one bracket per link with both lines (${drawnLinks})`);
    await page.locator("svg.plot g.tie.tm").first().focus();
    await page.keyboard.press("Enter");
    await page.waitForTimeout(100);
    check(/scholars rule/.test(await page.locator("#ll-details").textContent()), "a transmission link says the system flags and scholars rule");
    await page.keyboard.press("Escape");
  }
  check(await page.locator("#transmission").count() === 1 && /scholars rule/.test(await page.locator("#transmission").textContent()),
    "the overlap-check section states the rule");
  for (const v of ["tabaqa", "kin", "birth"]) {
    await page.selectOption('select[name="order"]', v);
    await page.waitForTimeout(100);
    check(await page.locator("svg.plot g.pl").count() >= nBase, `order "${v}" keeps every line`);
    if (v === "kin" && (data.kt || []).length) {
      const ties = page.locator("svg.plot g.tie");
      check(await ties.count() === data.kt.length, `family order: one undated bracket per recorded tie (${await ties.count()})`);
      await ties.first().focus();
      await page.keyboard.press("Enter");
      await page.waitForTimeout(100);
      const det = await page.locator("#ll-details").textContent();
      check(/Undated/.test(det) && /Status:/.test(det), "a kinship tie opens its claims, status and source, marked undated");
      await page.keyboard.press("Escape");
    }
  }
  await page.locator('input[name="review"]').check();
  await page.waitForTimeout(150);
  const nAll = data.people.length;
  check(await page.locator("svg.plot g.pl").count() === nAll, `needs-review toggle shows ${nAll} lines`);
  await page.locator('input[name="review"]').uncheck();
  // filter by label lookup
  if (data.events.length) {
    const label = "Event: " + data.events[0].n;
    await page.fill('input[name="filter"]', label);
    await page.dispatchEvent('input[name="filter"]', "change");
    await page.waitForTimeout(150);
    const shown = await page.locator("svg.plot g.pl").count();
    const want = new Set(data.events[0].ps.filter((ps) => data.people[ps.p].v.b).map((ps) => ps.p)).size;
    check(shown === want, `filter "${label}" shows its ${want} participants with a line (${shown})`);
    await page.locator('button[data-act="home"]').click();
    await page.waitForTimeout(150);
    check(await page.locator("svg.plot g.pl").count() === nBase, "Reset view brings everyone back");
  }
  check(external.length === 0, `zero external requests (${external.length})`);
  check(errors.length === 0, `no script errors (${errors.join(" | ")})`);
  await page.close();

  // ---- phone
  const ph = await open(browser, `${origin}/lifelines/`, { width: 390, height: 844 }, true);
  const sw = await ph.page.evaluate(() => document.documentElement.scrollWidth);
  check(sw <= 390, `phone 390x844: no horizontal page scroll (scrollWidth ${sw})`);
  check(await ph.page.locator("svg.plot").isVisible(), "phone: chart visible");
  const ta = await ph.page.evaluate(() => getComputedStyle(document.getElementById("ll-scroller")).touchAction);
  check(/pan-x/.test(ta) && /pan-y/.test(ta), `phone: one-finger pan is native, pinch handled by the page (touch-action: ${ta})`);
  if (nBase) {
    await ph.page.locator(".names button").first().tap();
    await ph.page.waitForTimeout(100);
    check(await ph.page.locator("#ll-details").isVisible(), "phone: tapping a name opens the details sheet");
  }
  if (shots) await ph.page.screenshot({ path: path.join(shots, "phone.png") });
  check(ph.external.length === 0 && ph.errors.length === 0, "phone: no external request, no script error");
  await ph.page.close();

  // ---- published on its own: opened as a single file
  const solo = await open(browser, "file://" + pageFile, { width: 1024, height: 768 });
  check(await solo.page.locator("svg.plot").count() === 1, "works as a single file (file://)");
  check(solo.external.length === 0 && solo.errors.length === 0, "single file: no external request, no script error");
  await solo.page.close();

  // ---- JavaScript off: the table and lists still read
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const nojs = await ctx.newPage();
  await nojs.goto(`${origin}/lifelines/`);
  check(await nojs.locator(".ll-people tbody tr:not([hidden])").count() === rows, "JavaScript off: the table is there");
  check(await nojs.locator(".controls").isHidden(), "JavaScript off: controls that need it stay hidden");
  await ctx.close();

  await browser.close();
  server.close();
  console.log(failures.length ? `\n${failures.length} check(s) failed` : "\nall checks passed");
  process.exit(failures.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
