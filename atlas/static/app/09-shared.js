/* Sky Atlas, part 9 of 10 — the merge review and class notes. The merge review is a study
   aid: slice 11a's merge proposals (ontology/corpus/merge-proposals.csv) with their
   evidence and Compare on the sky, the decisions the repository has recorded (through the
   review pages and review/import_decisions.py, by a reviewer on the roster), and a working
   list of your own kept in this browser, never shown as recorded. Class notes: a teacher's
   note on a record, read by the class; where the page is published with a shared store,
   notes are shared and only editors write, elsewhere they stay in this browser. Nothing
   here changes the graph or merges a mark. */
const SHARE = { db: null, user: null, me: null, edit: false, readOnly: false, notes: [], names: {}, dirty: false };
let WORKLIST = {}; // proposal -> { decision, note, a, b, on }: this browser only
const LOCAL_DEC = "marsad-atlas-merges-v1", LOCAL_NOTES = "marsad-atlas-notes-v1";
const MERGE_FILTER = { show: "all", kind: "", limit: 40 };
const NOTE_MAX = 2000;

function today() { return new Date().toISOString().slice(0, 10); }
const shared = () => !!SHARE.db;
const canWrite = () => (shared() ? SHARE.edit && !SHARE.readOnly : true);

async function shareStart() {
  WORKLIST = store.get(LOCAL_DEC, {}) || {};
  SHARE.notes = store.get(LOCAL_NOTES, []) || [];
  if (!window.claude || typeof window.claude.use !== "function") return;
  let db = null, user = null;
  try { [db, user] = await Promise.all([window.claude.use("db"), window.claude.use("user")]); } catch (e) { return; }
  if (!db) return;
  SHARE.db = db; SHARE.user = user;
  SHARE.notes = [];
  if (user) {
    try { SHARE.me = await user.id(); SHARE.edit = await user.canEdit(); } catch (e) { SHARE.edit = false; }
  } else SHARE.edit = true; // nothing said about this viewer: keep the controls, a refused write decides
  const fail = () => { SHARE.db = null; shareChanged(); };
  db.collection("data/notes/items").onSnapshot((snap) => {
    SHARE.notes = snap.docs.map((doc) => Object.assign({ id: doc.id }, doc.data()));
    shareNames(); shareChanged();
  }, fail);
  shareChanged();
}

function shareNames() { // resolve who wrote each note; only ids are stored
  if (!SHARE.user || typeof SHARE.user.profiles !== "function") return;
  const ids = new Set(SHARE.notes.map((x) => x.by).filter((x) => x && !(x in SHARE.names)));
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
function mergesOf(i) { return META.merges.filter((m) => m.a === i || m.b === i); }
const recorded = (m) => (m.dec ? { decision: m.dec, by: m.by, on: m.on, note: m.dn || "" } : null);
function listed(m) { // your working-list entry, if it still names the same two entries
  const d = WORKLIST[m.p];
  return d && d.a === ND.id[m.a] && d.b === ND.id[m.b] ? d : null;
}

function keep(m, decision, note) {
  if (decision) WORKLIST[m.p] = { decision, note: (note || "").slice(0, NOTE_MAX), a: ND.id[m.a], b: ND.id[m.b], on: today() };
  else delete WORKLIST[m.p];
  store.set(LOCAL_DEC, WORKLIST); shareChanged(); toast(t(decision ? "merge.saved_local" : "merge.cleared"));
}

function mergeCard(m) {
  const rec = recorded(m), mine = listed(m);
  const out = h("div", { class: "tour merge" + (rec ? " decided" : "") },
    h("p", { class: "muted" }, m.p, " · ", t("merge.kind." + m.k), " · ", t("merge.conf", { c: t("merge.c." + m.conf) })),
    h("div", { class: "row" }, nameBtn(m.a), h("span", { class: "muted" }, "⇄"), nameBtn(m.b)),
    h("p", { class: "evidence", lang: "en", dir: "ltr" }, m.ev),
    h("div", { class: "row" },
      h("button", { type: "button", class: "chip small", onclick: () => compare(m.a, m.b) }, t("merge.compare")),
      h("button", { type: "button", class: "chip small", onclick: () => { emphasise(new Set([m.a, m.b])); focus(m.a); } }, t("merge.show"))),
    h("p", { class: "merge-state" + (rec ? " on" : "") }, rec
      ? t("merge.state.file", { dec: t("merge.dec." + rec.decision), on: rec.on || "—" }) : t("merge.state.none")),
    rec && rec.note ? h("p", { class: "muted", lang: "en", dir: "ltr" }, "“", rec.note, "”") : null);
  if (rec) return out; // decided in the repository: a change goes through the maintainer
  const pick = h("select", { class: "field", "aria-label": t("merge.decision") },
    h("option", { value: "" }, t("merge.undecided")),
    ...["accept", "reject", "scholar"].map((x) => h("option", { value: x, selected: mine && mine.decision === x ? true : null }, t("merge.dec." + x))));
  const note = h("input", { type: "text", class: "field", maxlength: String(NOTE_MAX), "aria-label": t("merge.note"), placeholder: t("merge.note"), value: mine ? mine.note || "" : "" });
  out.append(h("p", { class: "muted merge-mine" }, mine ? t("merge.state.local", { dec: t("merge.dec." + mine.decision), on: mine.on }) : t("merge.state.mine_none")),
    h("div", { class: "row merge-edit" }, pick, note,
      h("button", { type: "button", class: "chip small", onclick: () => keep(m, pick.value, note.value) }, t("merge.keep"))));
  return out;
}

function mergesCsv() { // your working list, in the columns of merge-proposals.csv; who decided is left blank
  const q = (s) => (/[",\n]/.test(s) ? '"' + String(s).replace(/"/g, '""') + '"' : String(s));
  const lines = ["proposal,kind,keep_id,keep_name,merge_id,merge_name,evidence,confidence,decision,decided_by,decided_on,decision_note"];
  for (const m of META.merges) {
    const d = !recorded(m) && listed(m);
    if (d) lines.push([m.p, m.k, m.ka, m.an, m.kb, m.bn, m.ev, m.conf, d.decision, "", d.on, d.note || ""].map(q).join(","));
  }
  return lines.join("\n") + "\n";
}

function drawerMerges() {
  const all = META.merges || [];
  const nRec = all.filter(recorded).length, nMine = all.filter((m) => !recorded(m) && listed(m)).length;
  const kinds = [...new Set(all.map((m) => m.k))];
  const want = { all: () => true, open: (m) => !recorded(m), recorded: (m) => !!recorded(m), mine: (m) => !recorded(m) && !!listed(m) }[MERGE_FILTER.show] || (() => true);
  const list = all.filter((m) => (!MERGE_FILTER.kind || m.k === MERGE_FILTER.kind) && want(m));
  const refilter = (k) => (e) => { MERGE_FILTER[k] = e.target.value; MERGE_FILTER.limit = 40; renderDrawer(); };
  const out = [title(t("merge.title")), h("p", { class: "muted" }, t("merge.intro")), h("p", { class: "note" }, t("merge.where.local")),
    h("p", null, t("merge.tally", { n: fmt(all.length), f: fmt(nRec), w: fmt(nMine) })),
    h("div", { class: "row" },
      h("select", { class: "field", id: "merge-show", "aria-label": t("merge.filter"), onchange: refilter("show") },
        ...["all", "open", "recorded", "mine"].map((x) => h("option", { value: x, selected: MERGE_FILTER.show === x ? true : null }, t("merge.show." + x)))),
      h("select", { class: "field", id: "merge-kind", "aria-label": t("merge.kind"), onchange: refilter("kind") },
        h("option", { value: "" }, t("merge.kind.all")),
        ...kinds.map((k) => h("option", { value: k, selected: MERGE_FILTER.kind === k ? true : null }, t("merge.kind." + k))))),
    nMine ? h("div", { class: "row" },
      h("button", { type: "button", class: "chip small", onclick: () => copyText(mergesCsv(), $("drawer-body")) }, t("merge.copy")),
      h("span", { class: "muted" }, t("merge.copy_note"))) : null];
  if (!list.length) out.push(h("p", { class: "muted" }, t("merge.none")));
  for (const m of list.slice(0, MERGE_FILTER.limit)) out.push(mergeCard(m));
  if (list.length > MERGE_FILTER.limit) out.push(h("button", { type: "button", class: "chip small", id: "merge-more",
    onclick: () => { MERGE_FILTER.limit += 40; const y = $("drawer-body").scrollTop; renderDrawer(); $("drawer-body").scrollTop = y; } },
    t("merge.more", { n: fmt(Math.min(40, list.length - MERGE_FILTER.limit)), left: fmt(list.length - MERGE_FILTER.limit) })));
  return out;
}

function mergeFacet(i) { // on a record: the proposals that name it
  const ms = mergesOf(i);
  if (!ms.length) return null;
  return facet(t("merge.facet", { n: fmt(ms.length) }), h("p", { class: "muted" }, t("merge.facet_note")),
    h("ul", { class: "plain" }, ms.slice(0, 12).map((m) => { const rec = recorded(m); return h("li", null, m.p, " · ", nameBtn(m.a === i ? m.b : m.a), " · ",
      h("span", { class: "muted" }, rec ? t("merge.dec." + rec.decision) : t("merge.undecided"))); })),
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
