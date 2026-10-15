#!/usr/bin/env node
/* Loads the Sky with JavaScript on and checks it works, at desktop and phone size.
 * Derived from site/observatory/check_observatory.cjs: the Sky shares the Observatory's
 * page logic, so the same checks apply, plus the Sky's own (turning, viewpoints, Play
 * history, the option buttons, a finger tap on a star).
 *
 *   NODE_PATH="$(npm root -g)" PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
 *     node site/sky/check_sky.cjs [site/dist] [--shots DIR]
 *
 * Checks: the page is at most 2 MB; it renders (canvas drawn, legend, banner, "you are
 * here"); no request leaves the local server; no script error; the text view is not
 * empty; focusing a node (from the search box, from the keyboard and from the text view)
 * opens the panel with its facets; "How do we know?" opens the evidence ladder; every
 * frame button works; a thread can be traced; the Research lens shows the view state as
 * JSON; at 390x844 the panel is a bottom sheet and nothing scrolls sideways.
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
const page_ = path.join(root, "sky", "index.html");
const TYPES = { ".html": "text/html; charset=utf-8", ".css": "text/css" };
const BUDGET = 2000000;

const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split("?")[0].split("#")[0]);
  let f = path.join(root, p);
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end("not found"); }
  res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});

(async () => {
  const failures = [];
  const fail = (msg) => { failures.push(msg); console.log("  FAIL " + msg); };
  const ok = (msg) => console.log("  ok   " + msg);
  if (!fs.existsSync(page_)) { console.error(`${page_} not found: run site/sky/build_sky.py`); process.exit(1); }
  const size = fs.statSync(page_).size;
  if (size > BUDGET) fail(`page is ${size} bytes, over ${BUDGET}`); else ok(`page weight ${size} bytes (budget ${BUDGET})`);

  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();

  for (const vp of [{ width: 1280, height: 900, name: "desktop" }, { width: 390, height: 844, name: "phone", mobile: true }]) {
    console.log(`${vp.name} ${vp.width}x${vp.height}`);
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: !!vp.mobile, hasTouch: !!vp.mobile });
    const external = [];
    const errors = [];
    ctx.on("request", (rq) => { if (!rq.url().startsWith(origin) && !rq.url().startsWith("data:")) external.push(rq.url()); });
    const page = await ctx.newPage();
    page.on("pageerror", (e) => errors.push(String(e)));
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    const resp = await page.goto(origin + "/sky/", { waitUntil: "load" });
    if (resp.status() !== 200) fail(`HTTP ${resp.status()}`);
    await page.waitForFunction(() => document.documentElement.dataset.ready === "true", null, { timeout: 15000 }).catch(() => fail("page never became ready"));
    await page.waitForTimeout(300);

    // renders: canvas has pixels other than the background
    const drawn = await page.evaluate(() => {
      const c = document.getElementById("obs-canvas");
      const g = c.getContext("2d");
      const d = g.getImageData(0, 0, c.width, c.height).data;
      const bg = [d[0], d[1], d[2]];
      let diff = 0;
      for (let i = 0; i < d.length; i += 16) if (Math.abs(d[i] - bg[0]) + Math.abs(d[i + 1] - bg[1]) + Math.abs(d[i + 2] - bg[2]) > 40) diff++;
      return { w: c.width, h: c.height, diff };
    });
    if (drawn.w < 200 || drawn.diff < 200) fail(`canvas not drawn (${JSON.stringify(drawn)})`); else ok(`canvas drawn (${drawn.diff} sampled pixels differ from the background)`);
    for (const sel of [".banner", "#obs-here", "#obs-scale", "#legend-types li", "#legend-lines li", "h1"]) {
      if ((await page.locator(sel).count()) < 1) fail(`missing ${sel}`);
    }
    const here = await page.locator("#obs-here").innerText();
    if (!/lens/.test(here)) fail(`"you are here" is empty: ${here}`); else ok(`you are here: ${here}`);
    const scale = await page.locator("#obs-scale").innerText();
    if (!/Showing \d+ of \d+/.test(scale)) fail(`no scale note: ${scale}`); else ok(`scale note: ${scale}`);
    const alt = (await page.locator("#obs-textalt-body").innerText()).trim();
    if (alt.length < 80) fail("text view is empty"); else ok(`text view: ${alt.split("\n")[0].slice(0, 90)}…`);

    // focus from the search box
    const target = await page.evaluate(() => {
      const opts = [...document.querySelectorAll("#obs-names option")].map((o) => o.value);
      return opts.find((v) => /^Abu Bakr/.test(v)) || opts[0];
    });
    await page.fill("#obs-search", target);
    await page.press("#obs-search", "Enter");
    await page.waitForTimeout(900);
    const panelOpen = await page.locator("#obs-panel").evaluate((el) => el.dataset.open === "true" && getComputedStyle(el).display !== "none");
    const facets = await page.locator("#obs-panel .facet").count();
    const title = await page.locator("#panel-title").innerText().catch(() => "");
    if (!panelOpen || facets < 5) fail(`focus did not open the panel with facets (open=${panelOpen}, facets=${facets})`);
    else ok(`focused "${title}": panel open with ${facets} facets`);
    const altFocus = await page.locator("#obs-textalt-body").innerText();
    if (!/In focus:/.test(altFocus)) fail("text view does not describe the focused item"); else ok("text view lists the focused item's facets");
    // statuses visible
    const chips = await page.locator("#obs-panel .st").count();
    if (chips < 1) fail("no status labels in the panel"); else ok(`${chips} status labels in the panel`);

    // interrogate a link
    await page.locator("#obs-panel button.how").nth(1).click();
    await page.waitForTimeout(300);
    const rungs = await page.locator("#obs-panel ol.ladder > li").count();
    const ladderText = await page.locator("#obs-panel").innerText();
    if (rungs < 5 || !/Status/i.test(ladderText) || !/Recorded by/i.test(ladderText)) fail(`evidence ladder incomplete (${rungs} rungs)`);
    else ok(`evidence ladder: ${rungs} rungs`);
    if (shots) { fs.mkdirSync(shots, { recursive: true }); await page.screenshot({ path: path.join(shots, `${vp.name}-ladder.png`) }); }

    // back, then every frame
    await page.click("#obs-back");
    await page.waitForTimeout(200);
    for (const f of ["time", "geo", "stories", "isnad", "network"]) {
      await page.click(`#frame-${f}`);
      await page.waitForTimeout(850);
      const pressed = await page.locator(`#frame-${f}`).getAttribute("aria-pressed");
      if (pressed !== "true") fail(`frame ${f} did not become active`);
      if (shots) await page.screenshot({ path: path.join(shots, `${vp.name}-${f}.png`) });
    }
    ok("all five frames reachable");

    // keyboard: focus the canvas and press Enter
    await page.click("#obs-home");
    await page.waitForTimeout(800);
    await page.focus("#obs-canvas");
    await page.keyboard.press("Enter");
    await page.waitForTimeout(800);
    const kbTitle = await page.locator("#panel-title").innerText().catch(() => "");
    if (!kbTitle || /One sky/.test(kbTitle)) fail("Enter on the canvas did not focus a node"); else ok(`keyboard focus: ${kbTitle}`);

    // the text view's item list is a keyboard route to every node
    await page.click("#obs-home");
    await page.waitForTimeout(800);
    await page.locator(".all-items summary").click();
    const itemButtons = await page.locator(".all-items button.nb").count();
    if (itemButtons < 100) fail(`text view lists only ${itemButtons} item buttons`); else ok(`text view lists ${itemButtons} items as buttons`);

    // trace a thread between two named items
    await page.click("#obs-trace");
    await page.waitForTimeout(200);
    const pair = await page.evaluate(() => {
      const opts = [...document.querySelectorAll("#obs-names option")].map((o) => o.value);
      return [opts.find((v) => /^Asma/.test(v)) || opts[1], opts.find((v) => /Badr — Event/.test(v)) || opts[2]];
    });
    await page.fill("#trace-a", pair[0]);
    await page.fill("#trace-b", pair[1]);
    await page.locator(".trace-form button[type=submit]").click();
    await page.waitForTimeout(900);
    const hops = await page.locator("ol.thread .t-hop").count();
    if (hops < 1) fail(`no thread found between ${pair[0]} and ${pair[1]}`); else ok(`thread ${pair[0]} → ${pair[1]}: ${hops} step(s)`);
    if (shots) await page.screenshot({ path: path.join(shots, `${vp.name}-trace.png`) });

    // presets
    const presets = await page.locator("#obs-preset option").count();
    if (presets < 2) fail("no vantage presets"); else ok(`${presets - 1} vantage presets`);
    if (presets >= 2) {
      const v = await page.locator("#obs-preset option").nth(1).getAttribute("value");
      await page.selectOption("#obs-preset", v);
      await page.waitForTimeout(900);
      if (shots) await page.screenshot({ path: path.join(shots, `${vp.name}-preset.png`) });
    }

    // the Sky's own: a drag turns the view, viewpoints, Play history, option buttons
    const snap = () => page.evaluate(() => document.getElementById("obs-canvas").toDataURL());
    await page.click("#obs-home");
    await page.waitForTimeout(900);
    await page.locator("#obs-canvas").scrollIntoViewIfNeeded();
    const before = await snap();
    const cb = await page.locator("#obs-canvas").boundingBox();
    await page.mouse.move(cb.x + cb.width * 0.3, cb.y + cb.height * 0.5);
    await page.mouse.down();
    for (let k = 1; k <= 10; k++) await page.mouse.move(cb.x + cb.width * 0.3 + k * 18, cb.y + cb.height * 0.5 + k * 4);
    await page.mouse.up();
    await page.waitForTimeout(700);
    if ((await snap()) === before) fail("dragging did not turn the sky"); else ok("a drag turns the sky");
    for (const v of ["face", "edge", "below", "angle"]) {
      await page.click(`[data-sky-view="${v}"]`);
      await page.waitForTimeout(950);
    }
    ok("all four viewpoints reachable");
    await page.click("#sky-play");
    await page.waitForTimeout(1500);
    const playing = await page.locator("#sky-play").getAttribute("aria-pressed");
    const period = await page.locator("#scrub-on").isChecked();
    const scale2 = await page.locator("#obs-scale").innerText();
    if (playing !== "true" || !period || !/hollow/.test(scale2)) fail(`Play history did not run (pressed=${playing}, period=${period}, ${scale2})`);
    else ok(`Play history: ${scale2}`);
    await page.click("#sky-play");
    for (const id of ["sky-generation", "sky-names", "sky-scenery", "sky-orbit"]) {
      const b = page.locator("#" + id), was = await b.getAttribute("aria-pressed");
      await b.click();
      if ((await b.getAttribute("aria-pressed")) === was) fail(`${id} does not toggle`);
      await b.click();
    }
    ok("generation, names, distant stars and orbit toggle");
    if (shots) await page.screenshot({ path: path.join(shots, `${vp.name}-play.png`) });

    // research lens: view state JSON
    await page.locator('label[for="lens-research"]').click();
    await page.waitForTimeout(300);
    const json = await page.locator("pre.json").innerText().catch(() => "");
    try {
      const v = JSON.parse(json);
      if (!v.corpus_version || !v.morph_weights) throw new Error("fields missing");
      ok(`research lens: view state JSON (${Object.keys(v).length} fields)`);
    } catch (e) { fail("research lens has no valid view-state JSON: " + e.message); }
    await page.locator('label[for="lens-discover"]').click();
    await page.waitForTimeout(300);

    if (vp.mobile) {
      const pos = await page.locator("#obs-panel").evaluate((el) => getComputedStyle(el).position);
      if (pos !== "fixed") fail(`panel is not a bottom sheet on the phone (position ${pos})`); else ok("panel is a bottom sheet");
      const sw = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      if (sw > 1) fail(`page scrolls sideways by ${sw}px`); else ok("no sideways scroll");
      // touch: a finger tap on a star focuses it
      await page.click("#obs-home");
      await page.waitForTimeout(900);
      await page.locator("#obs-canvas").scrollIntoViewIfNeeded();
      const star = await page.evaluate(() => {
        const c = document.getElementById("obs-canvas"), r = c.getBoundingClientRect();
        const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data, k = c.width / r.width;
        // the brightest pixel away from the centre is a star (the light at the centre is skipped)
        let best = null, bv = 0;
        for (let y = 8; y < c.height - 8; y += 3) for (let x = 8; x < c.width - 8; x += 3) {
          if (Math.hypot(x - c.width / 2, y - c.height / 2) < c.width * 0.15) continue;
          const o = (y * c.width + x) * 4, v = d[o] + d[o + 1] + d[o + 2];
          if (v > bv) { bv = v; best = [r.left + x / k, r.top + y / k]; }
        }
        return best;
      });
      if (star) {
        await page.touchscreen.tap(star[0], star[1]);
        await page.waitForTimeout(900);
        const t2 = await page.locator("#panel-title").innerText().catch(() => "");
        const names = await page.evaluate(() => JSON.parse(document.getElementById("obs-data").textContent).nodes.map((nd) => nd.n));
        if (!names.includes(t2)) fail(`a finger tap on a star did not focus it (panel: ${t2})`); else ok(`finger tap focused: ${t2}`);
      } else fail("no star found to tap");
    }
    if (shots) await page.screenshot({ path: path.join(shots, `${vp.name}-final.png`), fullPage: false });
    if (external.length) fail("requests left the local server: " + external.join(", ")); else ok("no external requests");
    if (errors.length) fail("script errors: " + errors.join(" | ")); else ok("no script errors");
    await ctx.close();
  }
  await browser.close();
  server.close();
  console.log(failures.length ? `FAILED: ${failures.length}` : "OK: the Sky renders and works with JavaScript on, at 1280x900 and 390x844, with no external requests");
  process.exit(failures.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
