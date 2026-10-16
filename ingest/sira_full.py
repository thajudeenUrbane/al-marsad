#!/usr/bin/env python3
"""
Full-book pass over Ibn Hisham's al-Sira al-Nabawiyya: every section of the text, not a sample.

    .venv/bin/python ingest/sira_full.py chunks      # split the cached text into sections and chunks (cache only)
    .venv/bin/python ingest/sira_full.py verify N    # check one chunk's extraction output (quotes found, refs valid)
    .venv/bin/python ingest/sira_full.py status      # which chunks have output, and how much
    .venv/bin/python ingest/sira_full.py assemble    # resolve entities across chunks, mint IDs, write the committed
                                                     # ingest/claims/ibn-hisham-full-*.jsonl and identity.csv rows

ingest/ibn_hisham.py (slice 4) builds the Turtle; it reads these files beside its own.

The unit of the text here is the SECTION: the body between two of the edition's
headings (OpenITI lines starting ###). Each section that carries a claim becomes one
Passage and one Report. Headings are the editors' and are never quoted as evidence.

The extraction itself is done chunk by chunk (a chunk is a run of whole sections, about
CHUNK_CHARS characters of cleaned text) by an AI pass that writes
ingest/cache/full/out/NNN.jsonl. Those files quote the Arabic text (the quote a claim
rests on), so like the text they stay in the gitignored cache: `assemble` turns every
quote into character offsets and a checksum, and only those are committed.
"""

import argparse
import csv
import json
import re
import secrets
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ibn_hisham as ih  # noqa: E402

ROOT = ih.ROOT
FULL = ih.CACHE / "full"
CHUNKS = FULL / "chunks"
OUTDIR = FULL / "out"
SECTIONS = FULL / "sections.json"
EXISTING = FULL / "existing.tsv"
CHUNK_CHARS = 15000

F_PASSAGES = ih.CLAIMS_DIR / "ibn-hisham-full-passages.jsonl"
F_ENTITIES = ih.CLAIMS_DIR / "ibn-hisham-full-entities.jsonl"
F_CLAIMS = ih.CLAIMS_DIR / "ibn-hisham-full.jsonl"

ALLOWED = {
    # kinship
    "rel_father_of", "rel_mother_of", "rel_sibling_of", "rel_spouse_of", "rel_divorced_from",
    "rel_paternal_uncle_of", "rel_maternal_uncle_of", "rel_cousin_of", "rel_ancestor_of", "rel_adopted_by",
    # social and political
    "rel_mawla_of", "rel_ally_of", "rel_pledged_allegiance_to", "rel_party_to_treaty_with", "rel_opposed",
    "rel_fought_alongside", "rel_fought_against", "rel_killed", "rel_captured", "rel_manumitted", "rel_protected",
    "rel_sheltered", "rel_corresponded_with", "rel_sent_delegation_to", "rel_appointed", "rel_succeeded",
    "rel_governed",
    # transmission
    "rel_narrated_from",
    # spatial
    "rel_born_at", "rel_died_at", "rel_buried_at", "rel_resided_in", "rel_migrated_from", "rel_migrated_to",
    "rel_travelled_via", "rel_visited", "rel_sheltered_at",
    # participation and occurrence
    "rel_participated_in", "rel_led", "rel_witnessed", "rel_present_at", "rel_absent_from", "rel_occurred_at",
    "rel_occurred_during", "rel_part_of", "rel_preceded",
    # lifelines
    "rel_born_during", "rel_died_during", "rel_age_at", "rel_dated",
}
# what each end of a predicate may be (p person, l place, e event)
SHAPE = defaultdict(lambda: ("p", "p"))
SHAPE.update({
    "rel_governed": ("p", "l"),
    "rel_born_at": ("p", "l"), "rel_died_at": ("p", "l"), "rel_buried_at": ("p", "l"), "rel_resided_in": ("p", "l"),
    "rel_migrated_from": ("p", "l"), "rel_migrated_to": ("p", "l"), "rel_travelled_via": ("p", "l"),
    "rel_visited": ("p", "l"), "rel_sheltered_at": ("p", "l"),
    "rel_participated_in": ("p", "e"), "rel_led": ("p", "pe"), "rel_witnessed": ("p", "e"),
    "rel_present_at": ("p", "e"), "rel_absent_from": ("p", "e"),
    "rel_occurred_at": ("e", "l"), "rel_occurred_during": ("e", "e"), "rel_part_of": ("e", "e"),
    "rel_preceded": ("e", "e"),
    "rel_born_during": ("p", "e"), "rel_died_during": ("p", "e"), "rel_age_at": ("p", "e"),
    "rel_dated": ("e", "literal"),
})
KIND_OF = {"p": "person", "l": "place", "e": "event"}
ASCRIPTION_RE = re.compile(r"^(?:و?قال|حدثني|حدثنا)\s+(?:ابن إسحاق|ابن هشام)")


def chunk_path(n: int) -> Path:
    return CHUNKS / f"{n:03d}.txt"


def out_path(n: int) -> Path:
    return OUTDIR / f"{n:03d}.jsonl"


# ---------------------------------------------------------------- sections and chunks


def split_sections(s: str) -> list[dict]:
    """Every run of text between two heading lines, with its heading and its cleaned body."""
    heads = [m for m in re.finditer(r"^###[^\n]*\n?", s, re.M)]
    out = []
    for k, m in enumerate(heads):
        if m.group(0).startswith("######OpenITI"):
            continue
        start = m.end()
        end = heads[k + 1].start() if k + 1 < len(heads) else len(s)
        body = s[start:end]
        cleaned = ih.clean(body)
        if not cleaned or cleaned.startswith("#META"):
            continue
        heading = re.sub(r"^###\s*\|+\s*", "", m.group(0)).strip()
        out.append({"start": start, "end": end, "heading": heading, "chars": len(cleaned)})
    for k, sec in enumerate(out, 1):
        sec["sec"] = f"S{k:04d}"
    return out


def cmd_chunks(text: ih.Text):
    secs = split_sections(text.s)
    CHUNKS.mkdir(parents=True, exist_ok=True)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    chunks, cur, size = [], [], 0
    for sec in secs:
        if cur and size + sec["chars"] > CHUNK_CHARS:
            chunks.append(cur)
            cur, size = [], 0
        cur.append(sec)
        size += sec["chars"]
    if cur:
        chunks.append(cur)
    for n, ch in enumerate(chunks, 1):
        parts = []
        for sec in ch:
            sec["chunk"] = n
            vol_page = text.page(sec["start"])
            where = f"vol. {vol_page[0]}, p. {vol_page[1]}" if vol_page else ""
            parts.append(f"=== {sec['sec']} | {where} | heading (editors', never quote it): {sec['heading']}\n"
                         f"{ih.clean(text.s[sec['start']:sec['end']])}\n")
        chunk_path(n).write_text("\n".join(parts), encoding="utf-8")
    SECTIONS.write_text(json.dumps(secs, ensure_ascii=False), encoding="utf-8")
    rows, _ = ih.load_identity()
    with EXISTING.open("w", encoding="utf-8") as fh:
        fh.write("kind\tpreferred_name_en\tname_ar\tnote\n")
        for r in rows:
            fh.write(f"{r['kind']}\t{r['preferred_name_en']}\t{r['name_ar']}\t{r['stories50_names']}\n")
    print(f"{len(secs)} sections, {len(chunks)} chunks in {CHUNKS.relative_to(ROOT)}; "
          f"{sum(s['chars'] for s in secs)} characters of cleaned text")


def load_sections() -> dict:
    return {s["sec"]: s for s in json.loads(SECTIONS.read_text(encoding="utf-8"))}


# ---------------------------------------------------------------- quotes -> offsets


def norm_ws(x: str) -> str:
    return re.sub(r"\s+", " ", x.strip())


class SectionText:
    def __init__(self, text: ih.Text, sec: dict):
        self.raw = text.s[sec["start"]:sec["end"]]
        self.cleaned, self.idx = ih.clean_with_map(self.raw)

    def find(self, quote: str):
        q = norm_ws(quote)
        if not q:
            return None
        h = self.cleaned.find(q)
        if h < 0:
            return None
        return [self.idx[h], self.idx[h + len(q) - 1] + 1]


# ---------------------------------------------------------------- one chunk's output


def read_out(n: int) -> list[dict]:
    p = out_path(n)
    if not p.exists():
        return []
    rows = []
    for k, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            rows.append({"t": "_bad", "line": k, "error": str(e)})
    return rows


def check_chunk(n: int, text: ih.Text, secs: dict, existing: set) -> tuple[list[str], dict]:
    rows = read_out(n)
    errs = []
    ents, stexts = {}, {}
    mine = {s for s, v in secs.items() if v.get("chunk") == n}

    def st(sec):
        if sec not in stexts:
            stexts[sec] = SectionText(text, secs[sec])
        return stexts[sec]

    counts = defaultdict(int)
    for r in rows:
        t = r.get("t")
        counts[t] += 1
        if t == "_bad":
            errs.append(f"line {r['line']}: not JSON ({r['error']})")
        elif t in ("person", "place", "event"):
            i = r.get("id")
            if not i or i in ents:
                errs.append(f"{t} {i!r}: missing or repeated id")
                continue
            ents[i] = r
            if r.get("existing"):
                if (t, r["existing"]) not in existing:
                    errs.append(f"{i}: existing {r['existing']!r} is not a {t} preferred_name_en in existing.tsv")
            elif not r.get("name"):
                errs.append(f"{i}: no name")
            if t == "place" and r.get("place_type") not in ih.PLACE_TYPES:
                errs.append(f"{i}: place_type {r.get('place_type')!r} not one of {sorted(ih.PLACE_TYPES)}")
            if r.get("ar"):
                if r.get("sec") not in mine:
                    errs.append(f"{i}: sec {r.get('sec')!r} is not in this chunk")
                elif st(r["sec"]).find(r["ar"]) is None:
                    errs.append(f"{i}: ar {r['ar']!r} not found in {r['sec']}")
            elif t != "event" and not r.get("existing"):
                errs.append(f"{i}: a new {t} needs its name as written (ar)")
        elif t == "section":
            if r.get("sec") not in mine or not r.get("label"):
                errs.append(f"section label for {r.get('sec')!r}: not in this chunk or no label")
    for r in rows:
        if r.get("t") != "claim":
            continue
        where = f"claim {r.get('s')} {r.get('p')} {r.get('o', r.get('o_quote'))} ({r.get('sec')})"
        if r.get("sec") not in mine:
            errs.append(f"{where}: sec not in this chunk")
            continue
        p = r.get("p")
        if p not in ALLOWED:
            errs.append(f"{where}: predicate not allowed")
            continue
        sk, ok = SHAPE[p]
        s_ent = ents.get(r.get("s"))
        if not s_ent or s_ent["t"] not in [KIND_OF[c] for c in sk]:
            errs.append(f"{where}: subject must be a {'/'.join(KIND_OF[c] for c in sk)}")
        if ok == "literal":
            if not r.get("o_quote") or st(r["sec"]).find(r["o_quote"]) is None:
                errs.append(f"{where}: o_quote not found")
        else:
            o_ent = ents.get(r.get("o"))
            if not o_ent or o_ent["t"] not in [KIND_OF[c] for c in ok]:
                errs.append(f"{where}: object must be a {'/'.join(KIND_OF[c] for c in ok)}")
            if r.get("o") == r.get("s"):
                errs.append(f"{where}: subject and object are the same")
        if not r.get("quote") or st(r["sec"]).find(r["quote"]) is None:
            errs.append(f"{where}: quote not found in the section: {r.get('quote')!r}")
        if p == "rel_age_at":
            if not r.get("age_quote") or st(r["sec"]).find(r["age_quote"]) is None:
                errs.append(f"{where}: age_quote missing or not found")
        for q in r.get("q", []):
            if q not in ih.QUALIFIERS:
                errs.append(f"{where}: unknown qualifier {q}")
        if not r.get("gloss"):
            errs.append(f"{where}: no gloss")
    return errs, dict(counts)


def existing_names() -> set:
    rows, _ = ih.load_identity()
    return {(r["kind"], r["preferred_name_en"]) for r in rows}


def cmd_verify(text, n: int):
    secs = load_sections()
    errs, counts = check_chunk(n, text, secs, existing_names())
    print(f"chunk {n:03d}: {counts}")
    for e in errs[:200]:
        print("  " + e)
    print(f"{len(errs)} problems" if errs else "OK")
    return 1 if errs else 0


def cmd_status(text):
    secs = load_sections()
    n_chunks = max(s["chunk"] for s in secs.values())
    ex = existing_names()
    tot = defaultdict(int)
    missing, bad = [], []
    for n in range(1, n_chunks + 1):
        if not out_path(n).exists():
            missing.append(n)
            continue
        errs, counts = check_chunk(n, text, secs, ex)
        for k, v in counts.items():
            tot[k] += v
        if errs:
            bad.append((n, len(errs)))
    print(f"{n_chunks} chunks; done {n_chunks - len(missing)}; missing {missing}")
    print(f"with problems: {bad}")
    print(dict(tot))


# ---------------------------------------------------------------- assemble


AR_DIACRITICS = re.compile(r"[ً-ْٰـ]")


def norm_ar(x: str) -> str:
    x = AR_DIACRITICS.sub("", x)
    x = re.sub("[إأآٱ]", "ا", x).replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    x = re.sub(r"\bابن\b", "بن", x)
    x = re.sub(r"[^ء-ي ]", " ", x)
    return re.sub(r"\s+", " ", x).strip()


def norm_en(x: str) -> str:
    x = unicodedata.normalize("NFKD", x)
    x = "".join(c for c in x if not unicodedata.combining(c))
    x = x.replace("ʿ", "").replace("ʾ", "").replace("'", "").replace("’", "").replace("‘", "").lower()
    x = re.sub(r"\bibn\b|\bbin\b", "b.", x)
    x = re.sub(r"\babd al-|\babdul|\babdal", "abd al-", x)
    x = re.sub(r"\babdullah\b|\babd allah\b|\babdallah\b", "abd allah", x)
    x = re.sub(r"\(.*?\)", "", x)
    x = re.sub(r"[^a-z. -]", "", x)
    return re.sub(r"\s+", " ", x).strip()


def taken_payloads() -> set:
    taken = set()
    for f in (ROOT / "ontology").rglob("*.ttl"):
        taken |= set(re.findall(r"[a-z]{2,5}:([0-9A-Za-z]{22})\b", f.read_text(encoding="utf-8")))
    for f in ih.CLAIMS_DIR.glob("*.jsonl"):
        taken |= set(re.findall(r'[a-z]{2,5}:([0-9A-Za-z]{22})"', f.read_text(encoding="utf-8")))
    with ih.IDENTITY.open(encoding="utf-8") as fh:
        taken |= set(re.findall(r"[a-z]{2,5}:([0-9A-Za-z]{22})\b", fh.read()))
    return taken


ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


class Minter:
    """ontology/tools/mint_id.py's rule (random base62, never shared or near), for thousands of IDs at once."""

    def __init__(self):
        self.taken = taken_payloads()
        self.grams = set()
        for t in self.taken:
            self._add_grams(t)

    def _add_grams(self, t):
        for k in range(len(t) - 7):
            self.grams.add(t[k:k + 8])

    def __call__(self, prefix: str) -> str:
        while True:
            p = "".join(secrets.choice(ALPHABET) for _ in range(22))
            if p in self.taken or any(p[k:k + 8] in self.grams for k in range(15)):
                continue
            self.taken.add(p)
            self._add_grams(p)
            return f"{prefix}:{p}"


def cmd_assemble(text):
    """Turn every chunk's output into the committed JSONL files and identity.csv rows."""
    secs = load_sections()
    n_chunks = max(s["chunk"] for s in secs.values())
    ex = existing_names()
    for n in range(1, n_chunks + 1):
        errs, _ = check_chunk(n, text, secs, ex)
        if not out_path(n).exists() or errs:
            sys.exit(f"chunk {n:03d} is missing or has problems: run `verify {n}`")
    resolutions = {}
    res_file = FULL / "resolution.json"
    if res_file.exists():
        resolutions = json.loads(res_file.read_text(encoding="utf-8"))
    groups = build_groups(n_chunks)
    write_outputs(text, secs, n_chunks, groups, resolutions)


def entity_key(r: dict) -> tuple:
    if r.get("existing"):
        return ("existing", r["t"], r["existing"])
    if r.get("same_as"):
        return ("key", r["t"], norm_en(r["same_as"]))
    return ("key", r["t"], norm_en(r["name"]))


def build_groups(n_chunks: int) -> dict:
    """(chunk, local id) -> group key. Same kind and same normalised English name (with the
    lineage the extraction wrote into it) is one entity; nothing else is merged."""
    g = {}
    for n in range(1, n_chunks + 1):
        for r in read_out(n):
            if r.get("t") in ("person", "place", "event"):
                g[(n, r["id"])] = entity_key(r)
    return g


def cmd_groups(text):
    """A review list of names that might be one person and were kept apart (for a resolution pass)."""
    secs = load_sections()
    n_chunks = max(s["chunk"] for s in secs.values())
    by_key = defaultdict(list)
    for n in range(1, n_chunks + 1):
        for r in read_out(n):
            if r.get("t") in ("person", "place", "event") and not r.get("existing"):
                by_key[entity_key(r)].append((n, r))
    print(json.dumps({"groups": len(by_key)}, ensure_ascii=False))


def write_outputs(text, secs, n_chunks, groups, resolutions):
    src = json.loads(ih.SOURCE.read_text(encoding="utf-8"))
    mint = Minter()
    id_rows, _ = ih.load_identity()
    existing_by_name = {(r["kind"], r["preferred_name_en"]): r for r in id_rows}

    # ---- collect entity groups
    members = defaultdict(list)  # key -> [(chunk, row)]
    for n in range(1, n_chunks + 1):
        for r in read_out(n):
            if r.get("t") in ("person", "place", "event"):
                members[groups[(n, r["id"])]].append((n, r))
    # merges decided by the resolution pass: key -> key
    merge = {tuple(json.loads(a)): tuple(json.loads(b)) for a, b in resolutions.get("merge", {}).items()}

    def final(key):
        seen = set()
        while key in merge and key not in seen:
            seen.add(key)
            key = merge[key]
        return key

    final_members = defaultdict(list)
    for k, v in members.items():
        final_members[final(k)].extend(v)

    # ---- one record per new entity; names must be unique per kind in identity.csv
    used_names = {(r["kind"], r["preferred_name_en"]) for r in id_rows}
    ent_name = {}  # final key -> preferred_name_en
    new_entities = []
    for key in sorted(final_members, key=lambda k: (k[1], k[2])):
        mem = final_members[key]
        kind = key[1]
        if key[0] == "existing":
            ent_name[key] = key[2]
            continue
        # the fullest Arabic form as written, the most frequent English name
        names = defaultdict(int)
        for _, r in mem:
            names[r["name"]] += 1
        name = sorted(names.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))[0][0]
        name = name.strip()
        base = name
        k = 2
        while (kind, name) in used_names:
            note = next((r.get("note") for _, r in mem if r.get("note")), "")
            cand = f"{base} ({note})" if note and k == 2 else f"{base} ({k})"
            name = cand if (kind, cand) not in used_names else f"{base} ({k})"
            k += 1
        used_names.add((kind, name))
        ent_name[key] = name
        att = [(n, r) for n, r in mem if r.get("ar")]
        att.sort(key=lambda x: (-len(norm_ar(x[1]["ar"])), x[1]["sec"]))
        new_entities.append({"key": key, "kind": kind, "name": name, "members": mem, "attested": att[0] if att else None})

    # ---- passages: one per section that carries a claim or attests a new name
    used_secs = set()
    for n in range(1, n_chunks + 1):
        for r in read_out(n):
            if r.get("t") == "claim":
                used_secs.add(r["sec"])
    for e in new_entities:
        if e["attested"]:
            used_secs.add(e["attested"][1]["sec"])
    labels = {}
    for n in range(1, n_chunks + 1):
        for r in read_out(n):
            if r.get("t") == "section":
                labels[r["sec"]] = r["label"]
    old = {p["id"]: p for p in ih.read_jsonl(F_PASSAGES)} if F_PASSAGES.exists() else {}
    old_by_sec = {p["key"]: p for p in old.values()}
    passages = {}
    stexts = {}
    for sec in sorted(used_secs):
        meta = secs[sec]
        st = SectionText(text, meta)
        stexts[sec] = st
        prev = old_by_sec.get(sec)
        pid = prev["id"] if prev else mint("psg")
        rid = prev["report"] if prev else mint("rpt")
        m = ASCRIPTION_RE.match(st.cleaned)
        asc = None
        if m:
            asc = [st.idx[0], st.idx[m.end() - 1] + 1]
        label = labels.get(sec) or f"Ibn Hisham, Sira, section {sec[1:]}"
        passages[sec] = {
            "id": pid, "report": rid, "key": sec, "start": meta["start"], "end": meta["end"],
            "label": f"{label} (Ibn Hisham, Sira, section {int(sec[1:])})",
            "ascription": asc, "ascription_class": "other" if asc else "none",
            "sha256": ih.sha256_text(text.s[meta["start"]:meta["end"]]),
            "note": "Full-book pass: the section of the edition between two of its headings. "
                    + ("The ascription formula is the compiler's; it is not completed."
                       if asc else "No ascription formula opens this section; none is completed here."),
        }

    # ---- entity IDs: keep IDs minted by an earlier assemble (identity.csv rows from this pass)
    prior = {}
    for r in id_rows:
        if "full-book pass" in r["note"]:
            prior[(r["kind"], r["preferred_name_en"])] = r["canonical_id"]
    ent_rows = []
    new_id_rows = []
    for e in new_entities:
        kind = e["kind"]
        cid = prior.get((kind, e["name"])) or mint(ih.KIND_PREFIX[kind])
        e["id"] = cid
        row = {"kind": kind, "name": e["name"]}
        notes = sorted({r.get("note", "") for _, r in e["members"] if r.get("note")})
        if notes:
            row["comment"] = "; ".join(notes)[:300]
        if e["attested"]:
            n, r = e["attested"]
            span = stexts[r["sec"]].find(r["ar"])
            row["attested"] = {"passage": passages[r["sec"]]["id"], "span": span}
        if kind == "place":
            types = defaultdict(int)
            for _, r in e["members"]:
                types[r.get("place_type")] += 1
            row["place_type"] = sorted(types.items(), key=lambda kv: -kv[1])[0][0]
        ent_rows.append(row)
        ar = norm_ws(ih.clean(e["attested"][1]["ar"])) if e["attested"] else ""
        new_id_rows.append({"kind": kind, "canonical_id": cid, "preferred_name_en": e["name"], "name_ar": ar,
                            "variant_ids": "", "stories50_names": "", "source_files": "ibn-hisham",
                            "confidence": "needs-review",
                            "note": "minted in the full-book pass (Ibn Hisham ingestion); not matched to any "
                                    "existing row"})

    # ---- claims
    prev_claims = {}
    if F_CLAIMS.exists():
        for c in ih.read_jsonl(F_CLAIMS):
            prev_claims[(c["passage"], c["predicate"], c["span"][0], c["span"][1],
                         json.dumps(c["subject"], sort_keys=True), json.dumps(c["object"], sort_keys=True))] = c["id"]
    claims = []
    seen = set()
    for n in range(1, n_chunks + 1):
        rows = read_out(n)
        local = {r["id"]: r for r in rows if r.get("t") in ("person", "place", "event")}
        for r in rows:
            if r.get("t") != "claim":
                continue
            sec = r["sec"]
            st = stexts[sec]
            span = st.find(r["quote"])
            raw = st.raw

            def ref(lid):
                ent = local[lid]
                return {"kind": ent["t"], "name": ent_name[final(groups[(n, lid)])]}

            subj = ref(r["s"])
            if SHAPE[r["p"]][1] == "literal":
                obj = {"literal_spans": [st.find(r["o_quote"])]}
            else:
                obj = ref(r["o"])
                if obj == subj:
                    continue
            dedupe = (sec, r["p"], json.dumps(subj, sort_keys=True), json.dumps(obj, sort_keys=True))
            if dedupe in seen:
                continue
            seen.add(dedupe)
            pid = passages[sec]["id"]
            k = (pid, r["p"], span[0], span[1], json.dumps(subj, sort_keys=True), json.dumps(obj, sort_keys=True))
            c = {"id": prev_claims.get(k) or mint("ast"), "passage": pid, "predicate": r["p"],
                 "subject": subj, "object": obj, "span": span,
                 "span_sha256": ih.sha256_text(raw[span[0]:span[1]]), "gloss": r["gloss"].strip()}
            if r.get("q"):
                c["qualifiers"] = sorted(set(r["q"]))
            if r["p"] == "rel_age_at":
                c["age"] = {"spans": [st.find(r["age_quote"])]}
                if r.get("years"):
                    c["age"]["years"] = r["years"]
            if r["p"] == "rel_dated":
                c["date"] = {"spans": [st.find(r["o_quote"])]}
            claims.append(c)

    # ---- write
    pl = sorted(passages.values(), key=lambda p: p["start"])
    F_PASSAGES.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pl), encoding="utf-8")
    F_ENTITIES.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in ent_rows), encoding="utf-8")
    order = {p["id"]: p["start"] for p in pl}
    claims.sort(key=lambda c: (order[c["passage"]], c["span"][0], c["id"]))
    F_CLAIMS.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in claims), encoding="utf-8")

    # identity.csv: drop this pass's earlier rows, append the current ones at the end
    keep = [r for r in id_rows if "full-book pass" not in r["note"]]
    for r in keep:  # rows referenced by this pass: source_files gains ibn-hisham
        if (r["kind"], r["preferred_name_en"]) in {(k[1], k[2]) for k in final_members if k[0] == "existing"}:
            sf = [x for x in r["source_files"].split(";") if x]
            if "ibn-hisham" not in sf:
                r["source_files"] = ";".join(sf + ["ibn-hisham"])
    with ih.IDENTITY.open(encoding="utf-8", newline="") as fh:
        fields = csv.DictReader(fh).fieldnames
    with ih.IDENTITY.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in keep + new_id_rows:
            w.writerow(r)
    print(f"{len(pl)} passages, {len(ent_rows)} new entities, {len(claims)} claims; "
          f"{sum(1 for k in final_members if k[0] == 'existing')} existing entities referenced")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("command", choices=["chunks", "verify", "status", "assemble", "groups"])
    ap.add_argument("args", nargs="*")
    a = ap.parse_args()
    src = json.loads(ih.SOURCE.read_text(encoding="utf-8"))
    text = ih.Text(ih.load_text(src))
    if a.command == "chunks":
        cmd_chunks(text)
    elif a.command == "verify":
        return cmd_verify(text, int(a.args[0]))
    elif a.command == "status":
        cmd_status(text)
    elif a.command == "assemble":
        cmd_assemble(text)
    elif a.command == "groups":
        cmd_groups(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
