// Exhibition walk check (Playwright + Chromium):
//   NODE_PATH="$(npm root -g)" node exhibition/check.cjs [ignored] [screenshot dir]
//   NODE_PATH="$(npm root -g)" node exhibition/check.cjs --stills    # rewrites exhibition/stills/
// It starts exhibition/serve.py on a spare port and walks the eight halls at 1920 x 1080 and
// 1280 x 800: every hall fits its screen, the keys move through the halls, both live views load,
// answer their steps and hand the keys back, the still pictures stand in, the notes, the timer
// and a notes window work, the leave-behind prints on one A4 page, nothing is fetched from
// outside this machine, and every ﷺ is the marked sign.
"use strict";
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const http = require("http");
const path = require("path");
const fs = require("fs");

const ROOT = path.resolve(__dirname, "..");
const STILLS = process.argv.includes("--stills");
const args = process.argv.slice(2).filter((a) => a !== "--stills");
// scripts/check_all.sh passes site/dist first, as it does to every browser check; it is not used here
const shots = STILLS ? path.join(__dirname, "stills") : args[1] || path.join(require("os").tmpdir(), "exhibition-check");
fs.mkdirSync(shots, { recursive: true });
const PORT = +(process.env.EXHIBITION_PORT || 8771);
const BASE = `http://127.0.0.1:${PORT}`;
let failures = 0;
const ok = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); if (!cond) failures++; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function get(p) {
  return new Promise((res) => {
    http.get(BASE + p, (r) => {
      let body = "";
      r.on("data", (d) => (body += d));
      r.on("end", () => res({ status: r.statusCode, type: r.headers["content-type"] || "", body }));
    }).on("error", () => res({ status: 0, type: "", body: "" }));
  });
}

async function serve() {
  const proc = spawn(process.env.PYTHON || "python3", [path.join(__dirname, "serve.py"), "--no-browser", "--port", String(PORT)],
    { cwd: ROOT, stdio: ["ignore", "ignore", "inherit"] });
  for (let k = 0; k < 50; k++) {
    if ((await get("/exhibition/")).status === 200) return proc;
    await sleep(200);
  }
  proc.kill();
  throw new Error(`exhibition/serve.py did not start on port ${PORT}`);
}

async function context(browser, viewport) {
  const ctx = await browser.newContext(viewport ? { viewport } : {});
  ctx.errors = []; ctx.external = [];
  ctx.on("request", (r) => { const u = r.url(); if (!u.startsWith(BASE + "/") && !/^(data|blob|about):/.test(u)) ctx.external.push(u); });
  ctx.on("page", (p) => {
    p.on("pageerror", (e) => ctx.errors.push(e.message));
    // a failed load is reported once, with its address, by the response listener below
    p.on("console", (m) => { if (m.type() === "error" && !/^Failed to load resource/.test(m.text())) ctx.errors.push(m.text()); });
  });
  ctx.on("response", (r) => { if (r.status() >= 400) ctx.errors.push(`${r.status()} ${r.url().replace(BASE, "")}`); });
  return ctx;
}
const frameOf = async (page, hall) => (await page.$(`#hall-${hall} iframe`)).contentFrame();
const ready = (page, hall) => page.waitForSelector(`#hall-${hall} figure.live[data-ready='1']`, { timeout: 60000 }).then(() => true, () => false);

async function stills(browser) {
  const ctx = await context(browser, { width: 1920, height: 1080 });
  const page = await ctx.newPage();
  await page.goto(BASE + "/exhibition/#hall-3");
  await page.waitForSelector("html[data-ready='1']");
  const shot = async (hall, name) => {
    await (await page.$(`#hall-${hall} iframe`)).screenshot({ path: path.join(shots, name + ".jpg"), type: "jpeg", quality: 82 });
    console.log(`wrote exhibition/stills/${name}.jpg`);
  };
  const step = async (hall, k, wait) => { await page.click(`#hall-${hall} .steps button:nth-child(${k})`); await page.waitForTimeout(wait); };
  ok(await ready(page, 3), "the Atlas loads");
  await page.waitForTimeout(3500); await shot(3, "atlas-sky");
  await step(3, 2, 3500); await shot(3, "atlas-khadija");
  await step(3, 3, 3500); await shot(3, "atlas-ecliptic");
  await page.evaluate(() => window.__exhibition.show(3));
  ok(await ready(page, 4), "the expedition loads");
  await page.waitForTimeout(4000); await shot(4, "badr-eve");
  await step(4, 2, 1500);
  const x = await frameOf(page, 4);
  await x.click("#go"); await page.waitForTimeout(600);
  await x.evaluate(() => document.getElementById("r").scrollIntoView({ block: "center" }));
  await page.waitForTimeout(600); await shot(4, "badr-friday");
  await step(4, 3, 2500); await shot(4, "badr-halaqa");
  ok(ctx.errors.length === 0, `no page errors (${ctx.errors.slice(0, 3).join(" | ")})`);
  ok(ctx.external.length === 0, `nothing fetched from outside this machine (${ctx.external.slice(0, 3).join(" ")})`);
  await ctx.close();
}

async function serverChecks() {
  const page = await get("/exhibition/");
  ok(/charset=utf-8/i.test(page.type), `serve.py sends pages as UTF-8 (${page.type})`);
  ok((await get("/")).status === 302, "serve.py sends / to the exhibition");
  ok((await get("/.git/config")).status === 404 && (await get("/.claude/launch.json")).status === 404, "serve.py never serves a dot folder");
  ok((await get("/docs/")).status === 404, "serve.py lists no folders");
  const pj = await get("/exhibition/presenter.local.json");
  ok(pj.status === 200 && /json/.test(pj.type), "the presenter file answers (empty when there is none)");
}

async function walk(browser, viewport, tag) {
  const ctx = await context(browser, viewport);
  const page = await ctx.newPage();
  await page.goto(BASE + "/exhibition/");
  await page.waitForSelector("html[data-ready='1']", { timeout: 30000 });
  let notesPage = null;
  const where = () => page.evaluate(() => ({
    on: (document.querySelector(".hall.on") || {}).id, hash: location.hash, n: document.querySelector(".bar .n").textContent.trim(),
  }));
  const press = async (key, wait = 450) => { await page.keyboard.press(key); await page.waitForTimeout(wait); };
  for (let i = 1; i <= 8; i++) {
    const s = await where();
    ok(s.on === `hall-${i}` && s.hash === `#hall-${i}` && s.n === `${i} / 8`, `${tag}: hall ${i} is shown (${s.on}, ${s.hash}, "${s.n}")`);
    if (i === 3 || i === 4) ok(await ready(page, i), `${tag}: the live view in hall ${i} loads`);
    const fit = await page.evaluate(() => {
      const h = document.querySelector(".hall.on"), bar = document.querySelector(".bar").getBoundingClientRect();
      let bottom = 0;
      h.querySelectorAll("*").forEach((e) => {
        if (e.closest(".notes")) return;
        const r = e.getBoundingClientRect();
        if (r.width && r.height) bottom = Math.max(bottom, r.bottom);
      });
      return { sideways: document.documentElement.scrollWidth > innerWidth + 1, overflow: h.scrollHeight - h.clientHeight, bottom: Math.round(bottom), bar: Math.round(bar.top) };
    });
    ok(!fit.sideways && fit.overflow <= 1 && fit.bottom <= fit.bar + 1,
      `${tag}: hall ${i} fits the screen (overflow ${fit.overflow}px, content ends at ${fit.bottom}, bar at ${fit.bar}${fit.sideways ? ", scrolls sideways" : ""})`);
    await page.waitForTimeout(700); // the cross-fade between halls
    await page.screenshot({ path: path.join(shots, `hall-${i}-${tag}.png`) });

    if (i === 1) { await press("ArrowRight"); continue; }
    if (i === 3) {
      const atlas = await frameOf(page, 3);
      ok(!(await atlas.isVisible("#welcome").catch(() => false)), `${tag}: no welcome card over the Atlas`);
      await page.click("#hall-3 .steps button:nth-child(2)"); await page.waitForTimeout(2500);
      const focus = await atlas.evaluate(() => window.__atlas.S.focus);
      ok(focus != null && focus >= 0, `${tag}: “One record” opens Khadīja’s record in the Atlas (focus ${focus})`);
      await page.click("#hall-3 .steps button:nth-child(3)"); await page.waitForTimeout(2500);
      ok(await atlas.evaluate(() => !!window.__atlas.S.guide), `${tag}: “The Sīra in the order of the text” starts the Atlas tour`);
      await press("p");
      const title = await page.textContent("#sheet .sheet-title");
      ok(await page.isVisible("#sheet") && title === "3 / 8 · The sky of the Sīra", `${tag}: P opens the notes for hall 3 ("${title}")`);
      await press("p");
      ok(!(await page.isVisible("#sheet")), `${tag}: P closes the notes`);
      await press("t");
      const clock = await page.textContent("#timer .clock"), plan = await page.textContent("#timer .plan");
      ok(await page.isVisible("#timer") && /^\d\d:\d\d$/.test(clock) && /hall 3/.test(plan), `${tag}: T shows the timer (${clock} ${plan})`);
      await press("t");
      await page.$eval("#hall-3 iframe", (f) => f.focus());
      await press("PageDown", 700);
      ok((await where()).on === "hall-4", `${tag}: PageDown inside the Atlas moves the walk on`);
      continue;
    }
    if (i === 4) {
      const x = await frameOf(page, 4);
      await page.click("#hall-4 .steps button:nth-child(2)"); await page.waitForTimeout(1500);
      ok(await x.evaluate(() => location.hash === "#x-badr-2" && !!document.getElementById("go") && document.getElementById("r").hidden),
        `${tag}: “Which Friday?” asks its question afresh`);
      await press("s");
      // The picture loads when it is first shown; give it a moment before measuring it.
      await page.waitForFunction(() => { const img = document.querySelector("#hall-4 figure.live img.still"); return img.complete && img.naturalWidth > 0; }, null, { timeout: 5000 }).catch(() => {});
      const still = await page.evaluate(() => {
        const f = document.querySelector("#hall-4 figure.live"), img = f.querySelector("img.still");
        return { on: f.classList.contains("still-on"), shown: !img.hidden, w: img.naturalWidth, src: img.getAttribute("src") };
      });
      ok(still.on && still.shown && still.w > 0, `${tag}: S puts the still picture in place (${still.src}, ${still.w}px wide)`);
      await press("s");
      ok(!(await page.evaluate(() => document.querySelector("#hall-4 figure.live").classList.contains("still-on"))), `${tag}: S brings the live view back`);
      await page.click("#hall-4 .expand"); await page.waitForTimeout(500);
      ok(await page.evaluate(() => document.body.classList.contains("expanded") && !!document.querySelector(".unexpand")), `${tag}: “Open full screen” fills the screen`);
      await press("Escape");
      ok(await page.evaluate(() => !document.body.classList.contains("expanded")), `${tag}: Esc closes the full view`);
      await page.click("#hall-4 .steps button:nth-child(3)"); await page.waitForTimeout(2000);
      await page.$eval("#hall-4 iframe", (f) => f.focus());
      await press("PageDown", 900);
      const h = await x.evaluate(() => location.hash);
      ok((await where()).on === "hall-4" && h === "#halaqa-badr-1", `${tag}: PageDown in the halaqa room steps the room, not the walk (${h})`);
      await press("Escape");
      await press("PageDown");
      ok((await where()).on === "hall-5", `${tag}: Esc, then PageDown, moves the walk on from the halaqa room`);
      continue;
    }
    if (i === 5 && tag === "1920") {
      notesPage = await ctx.newPage();
      await notesPage.goto(BASE + "/exhibition/?notes#hall-5");
      await notesPage.waitForSelector("html[data-ready='1']");
      const t = await notesPage.textContent("#sheet .sheet-title");
      ok(await notesPage.evaluate(() => document.documentElement.classList.contains("notes-window")) && t.startsWith("5 / 8"), `${tag}: the notes window opens on hall 5 ("${t}")`);
    }
    if (i === 8) {
      await press("ArrowLeft");
      ok((await where()).on === "hall-7", `${tag}: ArrowLeft goes back a hall`);
      await press("Home");
      ok((await where()).on === "hall-1", `${tag}: Home goes to the opening`);
      await press("6");
      ok((await where()).on === "hall-6", `${tag}: a digit jumps to its hall`);
      continue;
    }
    await press(i % 2 ? "Space" : "PageDown");
    if (i === 5 && notesPage) {
      await notesPage.waitForTimeout(400);
      const t = await notesPage.textContent("#sheet .sheet-title");
      ok(t.startsWith("6 / 8"), `${tag}: the notes window follows the walk ("${t}")`);
      await notesPage.close();
    }
  }
  const text = await page.evaluate(textRules, ".hall");
  ok(text.length === 0, `${tag}: every honorific and every Arabic word is marked${text.length ? " (" + text.slice(0, 5).join(" | ") + ")" : ""}`);
  ok(ctx.errors.length === 0, `${tag}: no page errors${ctx.errors.length ? " (" + ctx.errors.slice(0, 3).join(" | ") + ")" : ""}`);
  ok(ctx.external.length === 0, `${tag}: nothing fetched from outside this machine${ctx.external.length ? " (" + ctx.external.slice(0, 3).join(" ") + ")" : ""}`);
  await ctx.close();
}

// Run in the page: every ﷺ is the marked sign, every Arabic word sits in a lang="ar" run, every
// honorific has a role and a label, no figure is empty, and each screen (the selector) that shows
// the sign also says it in words at its first mention.
function textRules(screens) {
  const bad = [];
  const AR = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDF9\uFDFB-\uFDFF\uFE70-\uFEFF]/;
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; (n = w.nextNode());) {
    const t = n.nodeValue, el = n.parentElement;
    if (el.closest("script, style")) continue;
    if (t.includes("\uFDFA")) {
      const hon = el.closest(".hon");
      if (!(hon && hon.textContent.trim() === "\uFDFA" && hon.getAttribute("role") === "img" && /peace and blessings/.test(hon.getAttribute("aria-label") || "")))
        bad.push("a bare ﷺ: " + t.trim().slice(0, 60));
    }
    if (AR.test(t)) {
      const l = el.closest("[lang]");
      if (!l || !/^ar/.test(l.getAttribute("lang"))) bad.push("Arabic outside lang=ar: " + t.trim().slice(0, 40));
    }
  }
  document.querySelectorAll(".hon").forEach((h) => { if (h.getAttribute("role") !== "img" || !h.getAttribute("aria-label")) bad.push("an honorific with no role or label: " + h.textContent); });
  document.querySelectorAll("[data-n], [data-t]").forEach((e) => { if (!e.textContent.trim()) bad.push("an empty figure: " + (e.dataset.n || e.dataset.t)); });
  document.querySelectorAll(screens).forEach((h) => {
    const signs = [...h.querySelectorAll('.hon[aria-label*="peace and blessings"]')].filter((s) => !s.closest(".notes"));
    if (signs.length && !h.querySelector(".words")) bad.push((h.id || screens) + ": no honorific in words at the first mention");
  });
  return bad;
}

async function leaveBehind(browser) {
  const ctx = await context(browser);
  const page = await ctx.newPage();
  const r = await page.goto(BASE + "/exhibition/leave-behind.html");
  ok(r && r.status() === 200, "the leave-behind exists");
  ok(await page.waitForSelector("html[data-ready='1']", { timeout: 20000 }).then(() => true, () => false), "leave-behind: the page is ready");
  const text = await page.evaluate(textRules, ".sheet");
  ok(text.length === 0, `leave-behind: every figure is filled, every honorific and every Arabic word is marked${text.length ? " (" + text.slice(0, 5).join(" | ") + ")" : ""}`);
  const pdf = await page.pdf({ preferCSSPageSize: true, printBackground: true });
  const pages = (pdf.toString("latin1").match(/\/Type\s*\/Page(?!s)/g) || []).length;
  ok(pages === 1, `leave-behind: prints on one A4 page (${pages})`);
  fs.writeFileSync(path.join(shots, "leave-behind.pdf"), pdf);
  ok(ctx.errors.length === 0 && ctx.external.length === 0, `leave-behind: no page errors, nothing fetched from outside${ctx.errors.concat(ctx.external).length ? " (" + ctx.errors.concat(ctx.external).slice(0, 3).join(" | ") + ")" : ""}`);
  await ctx.close();
}

(async () => {
  const server = await serve();
  const browser = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"] });
  try {
    if (STILLS) await stills(browser);
    else {
      await serverChecks();
      await walk(browser, { width: 1920, height: 1080 }, "1920");
      await walk(browser, { width: 1280, height: 800 }, "1280");
      await leaveBehind(browser);
    }
  } catch (e) {
    ok(false, "the check itself broke: " + ((e && e.stack) || e));
  } finally {
    await browser.close();
    server.kill();
  }
  console.log(failures ? `${failures} check(s) failed` : "all checks passed");
  console.log("pictures in " + shots);
  process.exit(failures ? 1 : 0);
})();
