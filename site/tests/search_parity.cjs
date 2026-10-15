#!/usr/bin/env node
/* Runs the browser search engine (site/static/search.js) under Node for the parity test.
 * Reads one JSON job on stdin: {rules, inputs: [text], items: [{u, n, k}], queries: [text]}
 * and writes {normal: [...], sound: [...], search: [[[u, tier], ...], ...]} on stdout.
 * Used by site/tests/test_search.py; no npm package needed.
 */
const path = require("path");
const { makeEngine } = require(path.join(__dirname, "..", "static", "search.js"));

let buf = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (d) => { buf += d; });
process.stdin.on("end", () => {
  const job = JSON.parse(buf);
  const e = makeEngine(job.rules);
  const items = e.prepare(job.items);
  const normal = job.inputs.map((s) => e.normalise(s));
  process.stdout.write(JSON.stringify({
    normal,
    sound: normal.map((n) => e.skeleton(n)),
    search: job.queries.map((q) => e.search(items, q)),
  }));
});
