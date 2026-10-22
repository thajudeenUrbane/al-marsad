/* Sky Atlas, part 6 of 8 — tracing threads between two records, and search. */

// fewest steps (a family step counts two); never through the Prophet ﷺ, who is linked to
// almost everyone, and unless asked never through names known only from lineages
function traceDistances(a) {
  const dist = new Int32Array(n).fill(1e9);
  const buckets = [[a], [], []];
  dist[a] = 0;
  let d = 0, guard = 0, left = 1;
  while (left > 0 && guard++ < 2e6) {
    const bk = buckets[d % 3];
    if (!bk.length) { d++; continue; }
    const x = bk.pop(); left--;
    if (dist[x] !== d) continue;
    if (x !== a && !passable(x)) continue;
    for (const c of claimsOf(x)) {
      const y = other(c, x), w = pclass(c) === "kinship" ? 2 : 1;
      if (dist[x] + w < dist[y]) { dist[y] = dist[x] + w; buckets[dist[y] % 3].push(y); left++; }
    }
  }
  return dist;
}
const passable = (x) => x !== LIGHT && (S.trace.lineage || !isBack(x));
function threads(a, b, limit) { // every shortest thread, up to a limit, walked back from b
  const dist = traceDistances(a);
  if (dist[b] >= 1e9) return [];
  const out = [];
  const walk = (v, path) => {
    if (out.length >= limit) return;
    if (v === a) { out.push(path.slice().reverse()); return; }
    const seen = new Set();
    for (const c of claimsOf(v)) {
      const u = other(c, v), w = pclass(c) === "kinship" ? 2 : 1;
      if (seen.has(u) || dist[u] + w !== dist[v] || (u !== a && !passable(u))) continue;
      seen.add(u);
      path.push([u, c]);
      walk(u, path);
      path.pop();
    }
  };
  walk(b, [[b, -1]]);
  // each step names its claim; prefer threads whose steps carry a cited source
  const fix = (p) => { const steps = []; for (let k = 0; k < p.length; k++) steps.push([p[k][0], k ? p[k - 1][1] : -1]); return steps; };
  const score = (p) => p.filter(([, c]) => c >= 0 && cf("cs", c)).length / Math.max(1, p.length - 1);
  return out.map(fix).sort((x, y) => score(y) - score(x)).map((p) => ({ path: p, score: score(p) }));
}
function trace(a, b, k) {
  if (a < 0 || b < 0 || a === b) { toast(t("trace.pick_both")); return; }
  pushHistory();
  S.trace.from = a; S.trace.to = b;
  const th = threads(a, b, 60);
  if (!th.length) { S.trace.path = null; toast(t("trace.none", { a: nameOf(a), b: nameOf(b) })); return; }
  S.trace.threads = th; S.trace.k = Math.min(k || 0, th.length - 1);
  LOG.traces++; saveLog(); checkMilestones();
  showThread();
}
function showThread() {
  const th = S.trace.threads, k = S.trace.k, a = S.trace.from, b = S.trace.to;
  const path = th[k].path;
  S.trace.path = path;
  const set = new Set(path.map(([x]) => x)), lines = new Set();
  for (const [, c] of path) if (c >= 0) lines.add(Math.min(CL.s[c], CL.o[c]) * 100000 + Math.max(CL.s[c], CL.o[c]));
  S.focus = b;
  emphasise(set, lines);
  R.flyToNode(b, spread(b, set));
  const shown = Math.min(5, th.length);
  showPanel([
    h("p", { class: "kind" }, t("trace.kind")),
    h("h2", { class: "name" }, nameOf(a), " → ", nameOf(b)),
    h("p", { class: "note warn" }, t("trace.note")),
    h("p", { class: "muted" }, t("trace.found", { n: fmt(th.length), steps: fmt(path.length - 1), shown: fmt(shown) }), " ", t("trace.rank_note")),
    h("div", { class: "row" }, th.slice(0, shown).map((x, j) => h("button", { type: "button", class: "chip small", "aria-pressed": String(j === k), onclick: () => { S.trace.k = j; showThread(); } }, t("trace.thread_n", { k: fmt(j + 1), steps: fmt(x.path.length - 1) })))),
    h("p", { class: "muted small" }, t("trace.rules")),
    h("label", { class: "toggle" }, h("input", { type: "checkbox", id: "trace-lineage", checked: S.trace.lineage ? true : null, onchange: (e) => { S.trace.lineage = e.target.checked; trace(a, b); } }), h("span", null, t("trace.lineage"))),
    h("ol", { class: "plain path" }, path.map(([x, c]) => h("li", null, nameBtn(x), c >= 0 ? h("ul", { class: "plain claims" }, claimRow(c, -1)) : null))),
    h("div", { class: "row" },
      h("button", { type: "button", class: "chip small", onclick: () => trace(b, a) }, t("trace.swap")),
      h("button", { type: "button", class: "chip small", onclick: () => copyText(location.href.split("#")[0] + "#" + viewToken()) }, t("trace.copy_link")),
      h("button", { type: "button", class: "chip small", onclick: () => { S.trace.path = null; S.trace.threads = null; clearFocus(); } }, t("trace.clear"))),
    h("p", { class: "note" }, t("trace.stories")),
  ]);
  here(); refreshText(); writeHash();
}

// ------------------------------------------------------------------ search
let SEARCH = null;
function buildSearch() {
  SEARCH = [];
  for (let i = 0; i < n; i++) SEARCH.push([ND.n[i], nf("sch", i), nf("ar", i), ...(nf("other", i) || [])].filter(Boolean).map(norm));
  SEARCH[LIGHT].push(norm(t("light.name")), norm(EN["light.name"]), norm(AR["light.name"]), "muhammad", "محمد", "النبي");
}
function search(q, max) {
  const s = norm(q);
  if (!s) return [];
  const hits = [];
  for (let i = 0; i < n; i++) {
    let best = 0;
    for (const f of SEARCH[i]) {
      if (f === s) best = Math.max(best, 4);
      else if (f.startsWith(s)) best = Math.max(best, 3);
      else if (f.includes(" " + s)) best = Math.max(best, 2);
      else if (s.length > 2 && f.includes(s)) best = Math.max(best, 1);
    }
    if (best && S.show.kinds[KIND[i]]) hits.push([i, best]);
  }
  hits.sort((a, b) => b[1] - a[1] || e3Key(a[0])[0] - e3Key(b[0])[0] || isBack(a[0]) - isBack(b[0]) || deg[b[0]] - deg[a[0]] || (ND.n[a[0]] < ND.n[b[0]] ? -1 : 1));
  return hits.slice(0, max || 14).map((x) => x[0]);
}
// a name box with its own short list of matches; choose(i) is called with the pick
function namePicker(id, label, choose, initial) {
  const wrap = h("div", { class: "picker" });
  const inp = h("input", { id, type: "search", class: "field", placeholder: label, "aria-label": label, autocomplete: "off", value: initial >= 0 ? nameOf(initial) : "" });
  const list = h("ul", { class: "results inline", role: "listbox", hidden: true });
  const render = () => {
    const items = search(inp.value, 8);
    list.replaceChildren(...(items.length ? items.map((i) => h("li", { role: "option", onmousedown: (e) => { e.preventDefault(); inp.value = nameOf(i); list.hidden = true; choose(i); } }, glyph(i), h("span", { class: "nm" }, nameOf(i)), h("span", { class: "ctx" }, kindText(i) + (contextLine(i) ? " · " + contextLine(i) : "")))) : [h("li", { class: "empty" }, t("search.none"))]));
    list.hidden = !inp.value.trim();
  };
  inp.addEventListener("input", render);
  inp.addEventListener("blur", () => setTimeout(() => { list.hidden = true; }, 150));
  inp.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); const r = search(inp.value, 1); if (r.length) { inp.value = nameOf(r[0]); list.hidden = true; choose(r[0]); } } });
  wrap.append(inp, list);
  return wrap;
}
function wireSearch() {
  const inp = $("search"), list = $("search-results");
  let items = [], sel = -1;
  const close = () => { list.hidden = true; inp.setAttribute("aria-expanded", "false"); sel = -1; };
  const render = () => {
    list.replaceChildren();
    if (!inp.value.trim()) { close(); return; }
    items = search(inp.value);
    if (!items.length) list.append(h("li", { class: "empty" }, t("search.none")));
    items.forEach((i, k) => list.append(h("li", { role: "option", id: "sr-" + k, "aria-selected": String(k === sel),
      onmousedown: (e) => { e.preventDefault(); choose(i); } }, glyph(i), h("span", { class: "nm" }, nameOf(i)), h("span", { class: "ctx" }, kindText(i) + (contextLine(i) ? " · " + contextLine(i) : "")))));
    list.hidden = false; inp.setAttribute("aria-expanded", "true");
  };
  const choose = (i) => { close(); inp.value = ""; inp.blur(); if (S.visible && !S.visible[i]) setView("sky", { camera: false, record: false }); focus(i); };
  inp.addEventListener("input", () => { sel = -1; render(); });
  inp.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { sel = Math.min(items.length - 1, sel + 1); render(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { sel = Math.max(0, sel - 1); render(); e.preventDefault(); }
    else if (e.key === "Escape") close();
  });
  inp.addEventListener("blur", () => setTimeout(close, 120));
  $("search-form").addEventListener("submit", (e) => { e.preventDefault(); const r = search(inp.value); if (r.length) choose(r[Math.max(0, sel)]); });
}
