#!/usr/bin/env node
/* Runs the browser engine (ask/static/ask.js) in Node for the parity test.
 *
 *   node ask/tests/parity_runner.cjs DATA.json INPUT.json
 *
 * DATA.json is what build_ask.py writes as ask-index.json; INPUT.json is
 * {"questions": [...], "names": [...], "years": [[n, "ah"], ...], "base": "../"}.
 * Prints {"answers": [{answer, html} | {error}], "tokens": [...], "keys": [...],
 * "bounds": [...]} as JSON. ask/tests/test_parity.py compares it with Python.
 */
"use strict";
const fs = require("fs");
const path = require("path");
const Ask = require(path.join(__dirname, "..", "static", "ask.js"));

const data = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const input = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const api = Ask.create(data);
const out = { answers: [], tokens: [], keys: [], bounds: [] };
for (const q of input.questions) {
  try {
    const ans = api.answer(q);
    out.answers.push({ answer: ans, html: api.render(ans, input.base) });
  } catch (e) {
    out.answers.push({ error: String((e && e.stack) || e) });
  }
}
for (const s of input.names) {
  out.tokens.push(api.nameTokens(s));
  out.keys.push(api.textKey(s));
}
for (const [n, era] of input.years) out.bounds.push(api.yearBounds(n, era));
process.stdout.write(JSON.stringify(out));
