/* Sky Atlas, part 8 of 10 — Ask: a plain question answered by the rule-based engine of
   ask/ (ask/static/ask.js: the site's Ask engine, its rules and its refusals) over this
   page's graph. No model runs. A question the rules cannot read is said so; a refused one
   gives its reason. The names in an answer light on the sky and open their records. */
let ASK = null, ASK_E = null, ASK_LOADING = null, ASK_LAST = null;
const ASK_BASE = "#ask/";

function askEngine() {
  if (ASK) return Promise.resolve(ASK);
  if (!ASK_LOADING) {
    ASK_LOADING = (window.MarsadAsk && $("ask-data") ? unpack("ask-data") : Promise.reject(new Error("no ask data")))
      .then((d) => { ASK = window.MarsadAsk.create(d); ASK_E = d.entities; return ASK; })
      .catch((e) => { ASK_LOADING = null; throw e; });
  }
  return ASK_LOADING;
}

function askRows(ans) { // every row of the answer, not only the ones shown
  const res = ans && ans.result;
  if (!res) return [];
  const rows = res.type === "count" ? (res.set && res.set.rows) || [] : res.rows || [];
  return rows.map((r) => ASK_BASE + ASK_E[r.e].r + "/");
}
function askNodes(box, extra) { // the marks an answer names: its rows, then every name it links
  const seen = new Set(), out = [];
  const hrefs = (extra || []).concat([...box.querySelectorAll('a[href^="' + ASK_BASE + '"]')].map((a) => a.getAttribute("href")));
  for (const href of hrefs) {
    const i = askTarget(href);
    if (i !== undefined && !seen.has(i)) { seen.add(i); out.push(i); }
  }
  return out;
}
function askTarget(href) { // "#ask/person/<id>/" -> a mark, or undefined
  const m = /^#ask\/([a-z]+)\/([^/]+)\/$/.exec(href || "");
  const i = m && m[1] !== "ask" ? byId(m[2]) : -1;
  return i >= 0 ? i : undefined;
}

function ask(q) {
  q = (q || "").trim();
  if (!q) return;
  const out = $("atlas-ask-out"), status = $("atlas-ask-status");
  if (status) status.textContent = t("ask.loading");
  return askEngine().then((eng) => {
    const ans = eng.answer(q);
    ASK_LAST = { q, html: eng.render(ans, ASK_BASE), outcome: ans.outcome, rows: askRows(ans) };
    LOG.asked = (LOG.asked || 0) + 1; saveLog();
    showAsk(true);
  }, () => { if (status) status.textContent = t("ask.unavailable"); });
}

function showAsk(light) { // light: put the answer on the sky (not when the tab is only shown again)
  const out = $("atlas-ask-out"), status = $("atlas-ask-status");
  if (!out || !ASK_LAST) return;
  out.innerHTML = ASK_LAST.html; // ask/present.py's markup: every value escaped (ask/tests/test_parity.py)
  const nodes = askNodes(out, ASK_LAST.rows);
  if (status) status.textContent = nodes.length ? t("ask.lit", { n: fmt(nodes.length) }) : "";
  if (!light) return;
  emphasise(nodes.length ? new Set(nodes) : null);
  announce(out.textContent.slice(0, 200));
}

function askClick(e) {
  const el = e.target.closest ? e.target.closest("a, [data-dsl], [data-q]") : null;
  if (!el) return;
  const q = el.getAttribute("data-dsl") || el.getAttribute("data-q");
  const href = el.getAttribute("href") || "";
  if (q) { e.preventDefault(); $("atlas-ask-q").value = q; ask(q); return; }
  if (!href.startsWith(ASK_BASE)) return;
  e.preventDefault();
  const ex = /^#ask\/ask\/q\/([^/]+)\/$/.exec(href);
  if (ex) { // an example question offered when one is not understood
    const text = el.textContent;
    $("atlas-ask-q").value = text; ask(text); return;
  }
  const i = askTarget(href);
  if (i === undefined) toast(t("ask.off_sky"));
  else focus(i);
}

function drawerAsk() {
  const input = h("input", { type: "search", id: "atlas-ask-q", "aria-label": t("ask.label"), placeholder: t("ask.placeholder"),
    value: ASK_LAST ? ASK_LAST.q : "", lang: "en", dir: "ltr", autocomplete: "off" });
  const form = h("form", { class: "ask-form", onsubmit: (e) => { e.preventDefault(); ask(input.value); } },
    input, h("button", { type: "submit", class: "chip primary small" }, t("ask.go")));
  input.addEventListener("focus", () => { askEngine().catch(() => {}); }, { once: true });
  const out = h("div", { class: "ask-out", id: "atlas-ask-out", lang: "en", dir: "ltr", "aria-live": "polite", onclick: askClick });
  const examples = (META.ask_examples || []).map((x) =>
    h("button", { type: "button", class: "chip small", lang: "en", dir: "ltr", onclick: () => { input.value = x; ask(x); } }, x));
  const res = [title(t("ask.title")), h("p", { class: "muted" }, t("ask.intro")),
    LANG === "ar" ? h("p", { class: "note" }, t("ask.english")) : null,
    form, h("p", { class: "muted", id: "atlas-ask-status", role: "status" }),
    examples.length ? h("div", { class: "row" }, ...examples) : null, out,
    h("p", { class: "note" }, t("ask.rules"))];
  if (ASK_LAST) setTimeout(showAsk, 0);
  return res;
}
