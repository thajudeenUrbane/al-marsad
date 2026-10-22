/* Sky Atlas, part 9 of 10 — shared work. The merge review: slice 11a's merge proposals
   (ontology/corpus/merge-proposals.csv), where an editor records accept, reject or ask a
   scholar for each pair, and copies the decisions out in the file's own format for the
   maintainer to approve and apply (propose_merges.py keeps decisions written into the
   file). Class notes: a teacher's note on a record, read by the class. Where the page is
   published with a shared store, notes are shared and only editors write; elsewhere they
   stay in this browser. Merge decisions stay in this browser for now: the review pages
   (PR #30) record them through the roster, and the maintainer is choosing which screen
   keeps the record (MERGE_SHARED). Nothing here changes the graph or merges a mark. */
const SHARE = { db: null, user: null, me: null, edit: false, readOnly: false, decisions: {}, notes: [], names: {}, dirty: false };
const LOCAL_DEC = "marsad-atlas-merges-v1", LOCAL_NOTES = "marsad-atlas-notes-v1";
const MERGE_FILTER = { show: "all", kind: "" };
const NOTE_MAX = 2000;
const MERGE_SHARED = false; // merge decisions in the shared store: off until the maintainer chooses (see above)

function today() { return new Date().toISOString().slice(0, 10); }
const shared = () => !!SHARE.db;
const canWrite = () => (shared() ? SHARE.edit && !SHARE.readOnly : true);
const mergeShared = () => MERGE_SHARED && shared();
const canDecide = () => (mergeShared() ? canWrite() : true);

async function shareStart() {
  SHARE.decisions = store.get(LOCAL_DEC, {}) || {};
  SHARE.notes = store.get(LOCAL_NOTES, []) || [];
  if (!window.claude || typeof window.claude.use !== "function") return;
  let db = null, user = null;
  try { [db, user] = await Promise.all([window.claude.use("db"), window.claude.use("user")]); } catch (e) { return; }
  if (!db) return;
  SHARE.db = db; SHARE.user = user;
  if (MERGE_SHARED) SHARE.decisions = {};
  SHARE.notes = [];
  if (user) {
    try { SHARE.me = await user.id(); SHARE.edit = await user.canEdit(); } catch (e) { SHARE.edit = false; }
  } else SHARE.edit = true; // nothing said about this viewer: keep the controls, a refused write decides
  const fail = () => { SHARE.db = null; shareChanged(); };
  if (MERGE_SHARED) db.collection("data/merge/decisions").onSnapshot((snap) => {
    const d = {};
    for (const doc of snap.docs) d[doc.id] = doc.data();
    SHARE.decisions = d; shareNames(); shareChanged();
  }, fail);
  db.collection("data/notes/items").onSnapshot((snap) => {
    SHARE.notes = snap.docs.map((doc) => Object.assign({ id: doc.id }, doc.data()));
    shareNames(); shareChanged();
  }, fail);
  shareChanged();
}

function shareNames() { // resolve who wrote each decision and note; only ids are stored
  if (!SHARE.user || typeof SHARE.user.profiles !== "function") return;
  const ids = new Set([...Object.values(SHARE.decisions).map((d) => d.by), ...SHARE.notes.map((x) => x.by)].filter((x) => x && !(x in SHARE.names)));
  if (!ids.size) return;
  for (const id of ids) SHARE.names[id] = "";
  SHARE.user.profiles([...ids]).then((ps) => {
    for (const id of ids) SHARE.names[id] = (ps && ps[id] && ps[id].name) || "";
    shareChanged();
  }, () => {});
}
const whoName = (id) => (!id ? "" : id === SHARE.me ? t("share.you") : SHARE.names[id] || t("share.someone"));

function shareChanged() { // redraw what shows shared state, never under a field being typed in
  const typing = document.activeElement && /input|textarea|select/i.test(document.activeElement.tagName) &&
    ($("drawer").contains(document.activeElement) || $("record").contains(document.activeElement));
  if (typing) { SHARE.dirty = true; return; }
  SHARE.dirty = false;
  if (!$("drawer").hidden && TAB === "merges") { const y = $("drawer-body").scrollTop; renderDrawer(); $("drawer-body").scrollTop = y; }
  const nf = $("notes-facet");
  if (nf && S.focus >= 0) nf.replaceWith(notesFacet(S.focus));
}
document.addEventListener("focusout", () => { if (SHARE.dirty) setTimeout(shareChanged, 0); });

function refused(e) { // a write the store turned down: this visit goes read-only
  if (e && e.code === "invalid_argument") { SHARE.readOnly = true; toast(t("share.refused")); }
  else if (e && e.code === "quota_exceeded") toast(t("share.full"));
  else toast(t("share.failed"));
  shareChanged();
}

// ------------------------------------------------------------------ the merge review
function mergeOf(p) { return META.merges.find((m) => m.p === p); }
function mergesOf(i) { return META.merges.filter((m) => m.a === i || m.b === i); }
function decisionOf(m) { // the decision recorded here, else the one already in the file
  const d = SHARE.decisions[m.p];
  if (d && d.a === ND.id[m.a] && d.b === ND.id[m.b]) return Object.assign({ where: mergeShared() ? "shared" : "local" }, d);
  return m.dec ? { decision: m.dec, byName: m.by, on: m.on, where: "file" } : null;
}

function decide(m, decision, note) {
  const doc = { decision, note: (note || "").slice(0, NOTE_MAX), a: ND.id[m.a], b: ND.id[m.b], on: today(), by: SHARE.me || null };
  if (!mergeShared()) {
    if (decision) SHARE.decisions[m.p] = doc; else delete SHARE.decisions[m.p];
    store.set(LOCAL_DEC, SHARE.decisions); shareChanged(); toast(t("merge.saved_local"));
    return;
  }
  const ref = SHARE.db.doc("data/merge/decisions/" + m.p);
  (decision ? ref.set(doc) : ref.delete()).then(() => toast(t("merge.saved")), refused);
}

function mergeCard(m) {
  const d = decisionOf(m);
  const pick = h("select", { class: "field", "aria-label": t("merge.decision"), disabled: canDecide() ? null : true },
    h("option", { value: "" }, t("merge.undecided")),
    ...["accept", "reject", "scholar"].map((x) => h("option", { value: x, selected: d && d.where !== "file" && d.decision === x ? true : null }, t("merge.dec." + x))));
  const note = h("input", { type: "text", class: "field", maxlength: String(NOTE_MAX), "aria-label": t("merge.note"), placeholder: t("merge.note"),
    value: d && d.where !== "file" ? d.note || "" : "", disabled: canDecide() ? null : true });
  const state = !d ? t("merge.state.none")
    : d.where === "file" ? t("merge.state.file", { dec: t("merge.dec." + d.decision), by: d.byName || "—", on: d.on || "—" })
    : d.where === "local" ? t("merge.state.local", { dec: t("merge.dec." + d.decision), on: d.on })
    : t("merge.state.set", { dec: t("merge.dec." + d.decision), by: whoName(d.by) || t("share.someone"), on: d.on });
  return h("div", { class: "tour merge" + (d ? " decided" : "") },
    h("p", { class: "muted" }, m.p, " · ", t("merge.kind." + m.k), " · ", t("merge.conf", { c: t("merge.c." + m.conf) })),
    h("div", { class: "row" }, nameBtn(m.a), h("span", { class: "muted" }, "⇄"), nameBtn(m.b)),
    h("p", { class: "evidence", lang: "en", dir: "ltr" }, m.ev),
    h("div", { class: "row" },
      h("button", { type: "button", class: "chip small", onclick: () => compare(m.a, m.b) }, t("merge.compare")),
      h("button", { type: "button", class: "chip small", onclick: () => { emphasise(new Set([m.a, m.b])); focus(m.a); } }, t("merge.show"))),
    h("p", { class: "merge-state" + (d ? " on" : "") }, state),
    d && d.note ? h("p", { class: "muted" }, "“", d.note, "”") : null,
    canDecide() ? h("div", { class: "row merge-edit" }, pick, note,
      h("button", { type: "button", class: "chip primary small", onclick: () => decide(m, pick.value, note.value) }, t("merge.save"))) : null);
}

function mergesCsv() { // ontology/corpus/merge-proposals.csv, decisions filled in from this page
  const q = (s) => (/[",\n]/.test(s) ? '"' + String(s).replace(/"/g, '""') + '"' : String(s));
  const lines = ["proposal,kind,keep_id,keep_name,merge_id,merge_name,evidence,confidence,decision,decided_by,decided_on"];
  for (const m of META.merges) {
    const d = decisionOf(m);
    // decided_by holds a reviewer's opaque roster ID, never a name: left for the maintainer unless the file has one
    const by = d && d.where === "file" ? d.byName || "" : "";
    lines.push([m.p, m.k, m.ka, m.an, m.kb, m.bn, m.ev, m.conf, d ? d.decision : "", by, d ? d.on || "" : ""].map(q).join(","));
  }
  return lines.join("\n") + "\n";
}

function drawerMerges() {
  const all = META.merges || [];
  const tally = { accept: 0, reject: 0, scholar: 0 };
  for (const m of all) { const d = decisionOf(m); if (d) tally[d.decision]++; }
  const decided = tally.accept + tally.reject + tally.scholar;
  const kinds = [...new Set(all.map((m) => m.k))];
  const list = all.filter((m) => (!MERGE_FILTER.kind || m.k === MERGE_FILTER.kind) &&
    (MERGE_FILTER.show === "all" || (MERGE_FILTER.show === "open") === !decisionOf(m)));
  const where = mergeShared() ? (canWrite() ? t("merge.where.shared_edit") : t("merge.where.shared_read")) : t("merge.where.local");
  const out = [title(t("merge.title")), h("p", { class: "muted" }, t("merge.intro")), h("p", { class: "note" }, where),
    h("p", null, t("merge.tally", { n: fmt(all.length), d: fmt(decided), a: fmt(tally.accept), r: fmt(tally.reject), s: fmt(tally.scholar) })),
    h("div", { class: "row" },
      h("select", { class: "field", id: "merge-show", "aria-label": t("merge.filter"), onchange: (e) => { MERGE_FILTER.show = e.target.value; renderDrawer(); } },
        ...["all", "open", "decided"].map((x) => h("option", { value: x, selected: MERGE_FILTER.show === x ? true : null }, t("merge.show." + x)))),
      h("select", { class: "field", id: "merge-kind", "aria-label": t("merge.kind"), onchange: (e) => { MERGE_FILTER.kind = e.target.value; renderDrawer(); } },
        h("option", { value: "" }, t("merge.kind.all")),
        ...kinds.map((k) => h("option", { value: k, selected: MERGE_FILTER.kind === k ? true : null }, t("merge.kind." + k))))),
    h("div", { class: "row" },
      h("button", { type: "button", class: "chip small", onclick: () => copyText(mergesCsv(), $("drawer-body")) }, t("merge.copy")),
      h("span", { class: "muted" }, t("merge.copy_note")))];
  if (!list.length) out.push(h("p", { class: "muted" }, t("merge.none")));
  for (const m of list) out.push(mergeCard(m));
  return out;
}

function mergeFacet(i) { // on a record: the proposals that name it
  const ms = mergesOf(i);
  if (!ms.length) return null;
  return facet(t("merge.facet", { n: fmt(ms.length) }), h("p", { class: "muted" }, t("merge.facet_note")),
    h("ul", { class: "plain" }, ms.map((m) => { const d = decisionOf(m); return h("li", null, m.p, " · ", nameBtn(m.a === i ? m.b : m.a), " · ",
      h("span", { class: "muted" }, d ? t("merge.dec." + d.decision) : t("merge.undecided"))); })),
    h("button", { type: "button", class: "chip small", onclick: () => { MERGE_FILTER.show = "all"; MERGE_FILTER.kind = ""; openDrawer("merges"); } }, t("merge.open")));
}

// ------------------------------------------------------------------ class notes
function notesOf(i) { const id = ND.id[i]; return SHARE.notes.filter((x) => x.node === id).sort((a, b) => (a.at < b.at ? -1 : 1)); }

function addNote(i, text) {
  text = (text || "").trim().slice(0, NOTE_MAX);
  if (!text) return;
  const doc = { node: ND.id[i], text, by: SHARE.me || null, at: new Date().toISOString() };
  if (!shared()) {
    SHARE.notes.push(Object.assign({ id: "n" + Date.now().toString(36) }, doc));
    store.set(LOCAL_NOTES, SHARE.notes); shareChanged(); return;
  }
  SHARE.db.collection("data/notes/items").add(doc).then(() => toast(t("notes.saved")), refused);
}
function removeNote(x) {
  if (!shared()) { SHARE.notes = SHARE.notes.filter((y) => y.id !== x.id); store.set(LOCAL_NOTES, SHARE.notes); shareChanged(); return; }
  SHARE.db.doc("data/notes/items/" + x.id).delete().then(() => {}, refused);
}

function notesFacet(i) {
  const notes = notesOf(i);
  if (!notes.length && !canWrite()) return h("div", { id: "notes-facet" });
  const box = h("textarea", { class: "field", rows: "3", maxlength: String(NOTE_MAX), "aria-label": t("notes.add_label"), placeholder: t("notes.placeholder") });
  return h("section", { class: "facet", id: "notes-facet" }, h("h3", null, t("notes.title")),
    h("p", { class: "muted" }, shared() ? t("notes.intro_shared") : t("notes.intro_local")),
    notes.length ? h("ul", { class: "plain notes-list" }, notes.map((x) => h("li", null,
      h("p", { class: "note-text" }, x.text),
      h("p", { class: "muted" }, t("notes.by", { by: whoName(x.by) || t("share.this_browser"), on: (x.at || "").slice(0, 10) }),
        canWrite() ? h("button", { type: "button", class: "mini", "aria-label": t("notes.remove"), onclick: () => removeNote(x) }, "×") : null)))) : null,
    canWrite() ? h("div", { class: "index-tools" }, box,
      h("div", { class: "row" }, h("button", { type: "button", class: "chip small", onclick: () => addNote(i, box.value) }, t("notes.add")))) : null);
}
