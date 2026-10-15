#!/usr/bin/env node
/* Drives the review pages in Chromium (slice 3b). Run by review/check_pages.py, which builds
 * the pages from a temporary copy of the corpus and imports what this script captures.
 *
 *   node review/check_pages.cjs PAGES OUT --reviewer ID --batch FILE [--identity FILE] [--timing]
 *
 * Checks, at 390x844 (phone, touch) and 1366x900 (laptop, keyboard): the reviewer ID is set
 * once from a link and kept; a batch is filled (accept with a citation, reject, needs
 * discussion with a note), with unfinished decisions held back; the page keeps working and
 * reopens offline; decisions survive a reload; "Send my decisions" downloads ONE file in the
 * decision-file format (saved as OUT/download.json); the share sheet path (Android shares
 * .txt, not .json) shares the same format (OUT/shared.txt); a cancelled share is not marked
 * sent; storage that the browser refuses shows a warning and loses nothing on the page;
 * the source sits below the claim on a phone and beside it on a laptop; tap targets are
 * large; nothing is requested from anywhere but the local server.
 * --timing: 50 claims in queue order on an emulated mid-range Android phone (Playwright's
 * "Moto G4", 4x CPU slowdown, Slow 4G), sent as one file (OUT/timing.json and
 * OUT/timing-decisions.json). Needs the `playwright` npm package and its Chromium.
 */
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium, devices } = require("playwright");

const argv = process.argv.slice(2);
function opt(name) { const i = argv.indexOf(name); return i >= 0 ? argv.splice(i, 2)[1] : null; }
function flag(name) { const i = argv.indexOf(name); if (i >= 0) argv.splice(i, 1); return i >= 0; }
const reviewerId = opt("--reviewer");
const batchFile = opt("--batch");
const identityFile = opt("--identity");
const timing = flag("--timing");
const root = path.resolve(argv[0]);
const out = path.resolve(argv[1]);
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json" };
const FILE_KEYS = ["format", "version", "reviewer_id", "created", "queue", "decisions"];
const DECISION_KEYS = ["kind", "target", "decision", "checks", "note", "date", "citation"];
const CITATION = "Test Source, vol. 0 p. 0 (browser test fixture, not a real citation)";
const NOTE = "Browser test note (fixture)";

const server = http.createServer((req, res) => {
  let f = path.join(root, decodeURIComponent(req.url.split("?")[0]));
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end("not found"); }
  res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream", "cache-control": "no-cache" });
  fs.createReadStream(f).pipe(res);
});

const failures = [];
const fail = (msg) => { failures.push(msg); console.log("  FAIL " + msg); };
const ok = (cond, msg) => { if (!cond) fail(msg); return cond; };

function checkFile(text, what, expect) {
  let doc;
  try { doc = JSON.parse(text); } catch (e) { fail(`${what}: not JSON (${e})`); return null; }
  const extra = Object.keys(doc).filter((k) => !FILE_KEYS.includes(k));
  ok(!extra.length, `${what}: fields outside the format: ${extra}`);
  ok(doc.format === "marsad-review-decisions" && doc.version === 1, `${what}: wrong format/version`);
  ok(doc.reviewer_id === reviewerId, `${what}: reviewer_id ${doc.reviewer_id}`);
  ok(!/Test Reviewer/.test(text), `${what}: holds a roster name`);
  for (const d of doc.decisions || []) {
    const bad = Object.keys(d).filter((k) => !DECISION_KEYS.includes(k));
    ok(!bad.length, `${what}: decision fields outside the format: ${bad}`);
    ok(/^\d{4}-\d{2}-\d{2}$/.test(d.date), `${what}: bad date ${d.date}`);
    ok(["claim", "identity"].includes(d.kind) && ["accept", "reject", "needs_discussion"].includes(d.decision), `${what}: bad kind/decision`);
  }
  if (expect) ok((doc.decisions || []).length === expect, `${what}: ${(doc.decisions || []).length} decisions, expected ${expect}`);
  return doc;
}

async function box(loc) { return await loc.boundingBox(); }

async function newContext(browser, external, options) {
  const ctx = await browser.newContext(Object.assign({ acceptDownloads: true }, options));
  ctx.on("request", (rq) => { if (!/^(http:\/\/127\.0\.0\.1:\d+\/|blob:|data:)/.test(rq.url())) external.push(rq.url()); });
  ctx.on("page", (p) => p.on("pageerror", (e) => fail("script error: " + e.message)));
  return ctx;
}

async function setReviewerFromLink(page, origin) {
  await page.goto(`${origin}/index.html#reviewer=${encodeURIComponent(reviewerId)}`);
  ok(await page.locator("#reviewer").isVisible(), "a link with #reviewer= opens the reviewer form");
  ok((await page.inputValue("#reviewer-id")) === reviewerId, "the reviewer ID from the link is filled in");
  await page.click("#reviewer-save");
  ok((await page.textContent("#who-text")).includes(reviewerId), "the header shows the saved reviewer ID");
}

async function sendAndCapture(page, file) {
  const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#send-share")]);
  ok(/^marsad-decisions-\d{4}-\d{2}-\d{2}-\d{4}-\w{6}\.json$/.test(dl.suggestedFilename()), `file name ${dl.suggestedFilename()}`);
  await dl.saveAs(file);
  return fs.readFileSync(file, "utf8");
}

async function phone(browser, origin, external) {
  console.log("phone 390x844: fill a batch, offline, reload, send");
  const ctx = await newContext(browser, external, { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  await page.goto(`${origin}/index.html`);
  ok((await page.textContent("#who-text")).length > 0 && !(await page.textContent("#who-text")).includes("agt:"), "no reviewer ID before one is set");
  await setReviewerFromLink(page, origin);
  await page.goto(`${origin}/${batchFile}`);
  ok(!(await page.locator("#reviewer").isVisible()), "the reviewer form stays closed once the ID is set");
  const cards = page.locator(".card");
  ok((await cards.count()) >= 3, "the batch has at least three cards");
  const [c1, c2, c3] = [cards.nth(0), cards.nth(1), cards.nth(2)];
  ok((await c1.getAttribute("data-cite")) === "1", "the first card needs a citation to accept");

  // layout: no sideways scrolling, source below the claim, big tap targets
  const width = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  ok(width[0] <= width[1], `no horizontal scroll at 390px (${width})`);
  const claimBox = await box(c1.locator(".claim-col")), srcBox = await box(c1.locator(".source-col"));
  ok(srcBox.y >= claimBox.y + claimBox.height - 1, "phone: the source is below the claim");
  for (const sel of [".choice-accept", ".choice-reject", ".choice-discuss", ".check"]) {
    const b = await box(c1.locator(sel).first());
    ok(b.height >= 44 && b.width >= 44, `phone: ${sel} is a large tap target (${Math.round(b.width)}x${Math.round(b.height)})`);
  }

  await c1.locator(".choice-accept").tap();
  ok(/source you checked/i.test(await c1.locator(".msg").textContent()), "accept without a citation says what is missing");
  ok(/not finished/.test(await page.textContent("#send-summary")), "an unfinished decision is listed, not sent");
  ok(await page.locator("#send-share").isDisabled(), "nothing to send yet");
  await c1.locator('input[name="citation"]').fill(CITATION);
  await c1.locator(".check").nth(0).tap();
  await c1.locator(".check").nth(3).tap();
  await c2.locator(".choice-reject").tap();
  await c2.locator(".check").nth(2).tap();
  await c3.locator(".choice-discuss").tap();
  ok(/note/i.test(await c3.locator(".msg").textContent()), "needs discussion without a note says what is missing");
  await c3.locator("textarea").fill(NOTE);
  ok((await page.textContent("#progress")).startsWith("3 of"), "progress counts three decided");
  ok(/3 decisions ready/.test(await page.textContent("#send-summary")), "three decisions ready to send");

  // offline: the page keeps working; once its service worker holds it, it reopens offline
  const cached = await page.evaluate(async () => {
    if (!("serviceWorker" in navigator)) return false;
    await navigator.serviceWorker.ready;
    for (let i = 0; i < 50; i++) {
      const c = await caches.open("marsad-review-1");
      if (await c.match(location.href.split("#")[0])) return true;
      await new Promise((r) => setTimeout(r, 100));
    }
    return false;
  });
  ok(cached, "the service worker keeps the page for offline use");
  await ctx.setOffline(true);
  await page.reload();
  ok((await page.locator(".card").count()) >= 3, "offline: the page reopens from the service worker");
  ok(await page.locator(".card").nth(1).locator('input[value="reject"]').isChecked(), "after a reload the decisions are back");
  ok((await page.locator(".card").nth(0).locator('input[name="citation"]').inputValue()) === CITATION, "after a reload the citation is back");
  const text = await sendAndCapture(page, path.join(out, "download.json"));
  const doc = checkFile(text, "download.json", 3);
  if (doc) {
    const by = Object.fromEntries(doc.decisions.map((d) => [d.target, d]));
    const t1 = await c1.getAttribute("data-target"), t2 = await c2.getAttribute("data-target"), t3 = await c3.getAttribute("data-target");
    ok(by[t1] && by[t1].decision === "accept" && by[t1].citation === CITATION && by[t1].checks.join() === "report_in_source,identity", "file: accept with citation and checks");
    ok(by[t2] && by[t2].decision === "reject" && !("citation" in by[t2]), "file: reject");
    ok(by[t3] && by[t3].decision === "needs_discussion" && by[t3].note === NOTE, "file: needs discussion with note");
    ok(typeof doc.queue === "string" && doc.queue.startsWith("sha256:"), "file: names the queue it was made from");
  }
  const again = page.locator(".card").nth(2);
  ok(/sent/.test(await again.locator(".msg").textContent()), "sent decisions say so");
  await again.locator(".check").nth(1).tap();
  ok(/changed this after sending/.test(await again.locator(".msg").textContent()), "a change after sending is flagged");
  await again.locator(".check").nth(1).tap();
  ok(/sent/.test(await again.locator(".msg").textContent()), "changing it back matches what was sent");
  await ctx.setOffline(false);
  await page.goto(`${origin}/index.html`);
  const prog = await page.locator(`li[data-batch] a[href="${batchFile}"]`).locator("xpath=..").locator("[data-prog]").textContent();
  ok(/^3 of/.test(prog), `the index shows the batch's progress (${prog})`);
  await ctx.close();
}

async function share(browser, origin, external) {
  console.log("share sheet: Android shares .txt; a cancelled share is not sent");
  const ctx = await newContext(browser, external, { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  await ctx.addInitScript(() => {
    window.__shared = [];
    window.__cancel = false;
    navigator.canShare = (d) => !!(d && d.files && d.files.every((f) => /\.txt$/.test(f.name) && f.type === "text/plain"));
    navigator.share = async (d) => {
      if (window.__cancel) throw new DOMException("cancelled", "AbortError");
      for (const f of d.files) window.__shared.push({ name: f.name, text: await f.text() });
    };
  });
  const page = await ctx.newPage();
  await setReviewerFromLink(page, origin);
  const target = identityFile || batchFile;
  await page.goto(`${origin}/${target}`);
  const card = page.locator(".card").last();
  await card.locator(".choice-discuss").tap();
  await card.locator("textarea").fill(NOTE);
  await page.evaluate(() => { window.__cancel = true; });
  await page.click("#send-share");
  await page.waitForFunction(() => /cancelled/.test(document.getElementById("send-status").textContent));
  ok(!/sent/.test(await card.locator(".msg").textContent()), "a cancelled share is not marked sent");
  await page.evaluate(() => { window.__cancel = false; });
  await page.click("#send-share");
  await page.waitForFunction(() => window.__shared.length === 1);
  const shared = await page.evaluate(() => window.__shared[0]);
  ok(/\.txt$/.test(shared.name), `shared as .txt (${shared.name})`);
  fs.writeFileSync(path.join(out, "shared.txt"), shared.text);
  checkFile(shared.text, "shared.txt", 1);
  ok(/\.txt/.test(await page.textContent("#send-status")), "the page says the phone sent a .txt");
  await ctx.close();
}

async function laptop(browser, origin, external) {
  console.log("laptop 1366x900: keyboard, source beside the claim");
  const ctx = await newContext(browser, external, { viewport: { width: 1366, height: 900 } });
  const page = await ctx.newPage();
  await setReviewerFromLink(page, origin);
  await page.goto(`${origin}/${batchFile}`);
  const cards = page.locator(".card");
  const claimBox = await box(cards.nth(0).locator(".claim-col")), srcBox = await box(cards.nth(0).locator(".source-col"));
  ok(srcBox.x >= claimBox.x + claimBox.width - 1 && Math.abs(srcBox.y - claimBox.y) < 40, "laptop: the source is beside the claim");
  await cards.nth(0).focus();
  await page.keyboard.press("Digit1");
  await page.keyboard.press("Digit3");
  await page.keyboard.press("KeyR");
  ok(await cards.nth(0).locator('input[value="reject"]').isChecked(), "R rejects");
  ok((await cards.nth(0).locator('input[name="check"]:checked').count()) === 2, "1 and 3 tick checks");
  ok(await page.evaluate(() => document.activeElement.id === document.querySelectorAll(".card")[1].id), "after R the next claim has focus");
  await page.keyboard.press("KeyA");
  ok(await page.evaluate(() => document.activeElement.name === "citation"), "A on a claim that needs a citation goes to the citation");
  await page.keyboard.type("typed j k a r d");
  ok(await cards.nth(1).locator('input[value="accept"]').isChecked(), "letters typed in a field are not shortcuts");
  await page.keyboard.press("Enter");
  ok(await page.evaluate(() => document.activeElement.id === document.querySelectorAll(".card")[2].id), "Enter in the citation goes to the next claim");
  await page.keyboard.press("KeyD");
  ok(await page.evaluate(() => document.activeElement.tagName === "TEXTAREA"), "D goes to the note");
  await page.keyboard.type("x");
  await page.keyboard.press("Escape");
  await page.keyboard.press("KeyK");
  ok(await page.evaluate(() => document.activeElement.id === document.querySelectorAll(".card")[1].id), "K goes back");
  await page.keyboard.press("KeyS");
  ok(await page.evaluate(() => document.activeElement.id === "send"), "S goes to Send");
  ok(/3 decisions ready/.test(await page.textContent("#send-summary")), "three keyboard decisions ready");
  await ctx.close();
}

async function blocked(browser, origin, external) {
  console.log("storage refused: warning, nothing lost on the page");
  const ctx = await newContext(browser, external, { viewport: { width: 390, height: 844 } });
  await ctx.addInitScript(() => {
    Storage.prototype.setItem = function () { throw new DOMException("blocked", "QuotaExceededError"); };
  });
  const page = await ctx.newPage();
  await page.goto(`${origin}/${batchFile}`);
  ok(await page.locator("#storage-warning").isVisible(), "a warning says decisions are not kept");
  await page.fill("#reviewer-id", reviewerId);
  await page.click("#reviewer-save");
  await page.locator(".card").nth(1).locator(".choice-reject").click();
  ok(/1 decision ready/.test(await page.textContent("#send-summary")), "decisions still work in memory");
  const text = await sendAndCapture(page, path.join(out, "blocked.json"));
  checkFile(text, "blocked.json", 1);
  await ctx.close();
}

async function timed(browser, origin, external) {
  console.log("timing: 50 claims on an emulated mid-range Android phone");
  const ctx = await newContext(browser, external, Object.assign({ serviceWorkers: "block" }, devices["Moto G4"]));
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  await cdp.send("Network.enable");
  await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: 1.6e6 / 8, uploadThroughput: 750e3 / 8 });
  await setReviewerFromLink(page, origin);
  const first = await page.locator(".batch-list a").first().getAttribute("href");
  const t0 = Date.now();
  const loads = [];
  let s = Date.now();
  await page.goto(`${origin}/${first}`, { waitUntil: "load" });
  loads.push({ page: first, ms: Date.now() - s, bytes: fs.statSync(path.join(root, first)).size });
  const actions = [];
  const mix = { accept: 0, reject: 0, needs_discussion: 0 };
  let done = 0;
  while (done < 50) {
    const cards = page.locator(".card");
    const n = await cards.count();
    for (let i = 0; i < n && done < 50; i++, done++) {
      const card = cards.nth(i);
      await card.scrollIntoViewIfNeeded();
      const a = Date.now();
      if (done % 5 === 4) {
        await card.locator(".choice-discuss").tap();
        await card.locator("textarea").fill(NOTE);
      } else if (done % 3 === 2) {
        await card.locator(".choice-reject").tap();
      } else {
        await card.locator(".check").nth(0).tap();
        await card.locator(".check").nth(3).tap();
        await card.locator(".choice-accept").tap();
        if ((await card.getAttribute("data-cite")) === "1") await card.locator('input[name="citation"]').fill(CITATION);
      }
      actions.push(Date.now() - a);
      mix[done % 5 === 4 ? "needs_discussion" : done % 3 === 2 ? "reject" : "accept"]++;
    }
    if (done < 50) {
      const next = await page.locator('a[rel="next"]').getAttribute("href");
      s = Date.now();
      await Promise.all([page.waitForEvent("load"), page.locator('a[rel="next"]').tap()]);
      loads.push({ page: next, ms: Date.now() - s, bytes: fs.statSync(path.join(root, next)).size });
    }
  }
  const sendStart = Date.now();
  const text = await sendAndCapture(page, path.join(out, "timing-decisions.json"));
  const sendMs = Date.now() - sendStart;
  const total = Date.now() - t0;
  checkFile(text, "timing-decisions.json", 50);
  actions.sort((x, y) => x - y);
  const result = {
    profile: "Playwright 'Moto G4' (360x640, touch), 4x CPU slowdown, Slow 4G (150 ms, 1.6 Mbit/s down)",
    claims: 50, pages: loads.length, total_ms: total, page_loads_ms: loads.map((l) => l.ms), page_bytes: loads.map((l) => l.bytes),
    per_claim_ms: { median: actions[25], max: actions[49], mean: Math.round(actions.reduce((x, y) => x + y, 0) / 50) },
    send_ms: sendMs, mix, how: "accept = 2 checks + accept + citation where needed; needs discussion = note; text entered with fill(); no service worker (a first visit)"
  };
  fs.writeFileSync(path.join(out, "timing.json"), JSON.stringify(result, null, 1));
  console.log(JSON.stringify(result));
  await ctx.close();
}

(async () => {
  fs.mkdirSync(out, { recursive: true });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();
  const external = [];
  try {
    await phone(browser, origin, external);
    await share(browser, origin, external);
    await laptop(browser, origin, external);
    await blocked(browser, origin, external);
    if (timing) await timed(browser, origin, external);
  } catch (e) {
    fail("stopped: " + (e && e.stack ? e.stack.split("\n").slice(0, 3).join(" | ") : e));
  }
  ok(!external.length, "requests left the local server: " + external.join(", "));
  await browser.close();
  server.close();
  console.log(failures.length ? `FAILED: ${failures.length}` : "OK: the review pages work on a phone and a laptop, offline once loaded, and send one decision file");
  process.exit(failures.length ? 1 : 0);
})();
