#!/usr/bin/env python3
"""
Mint new al-Marsad identifiers (slice 1b, maintainer decision 5).

    .venv/bin/python ontology/tools/mint_id.py per          # one new person ID, e.g. per:Ab3...
    .venv/bin/python ontology/tools/mint_id.py plc -n 5     # five new place IDs
    .venv/bin/python ontology/tools/mint_id.py --known      # how many payloads are already taken

The rule:
  * the payload is 22 characters of base62 (0-9, A-Z, a-z) drawn from the
    `secrets` module (the operating system's cryptographic random source);
  * it is never derived from a name, a date, another ID or a hash of any of them;
  * it is checked against the payload of every existing IRI of ANY kind
    (person, place, event, report, assertion, ... in every .ttl under ontology/,
    plus every ID in ontology/corpus/identity.csv), so no payload is ever shared
    across kinds, not only within one kind;
  * it is also at least two characters away from every taken payload (one
    character substituted, added or dropped is a near-collision and is rejected).

Slice 1d renamed the IDs that broke this rule (see docs/handover/slice-1d.md);
identity_audit.py fails if a shared payload or a one-character near-collision
reappears.
This script only prints IDs. It writes nothing; put the ID in the data and
the identity table yourself.
"""

import argparse
import csv
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://w3id.org/marsad/id/"
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
LENGTH = 22
IRI_RE = re.compile(re.escape(BASE) + r"[a-z]+/([A-Za-z0-9]+)")
PREFIX_RE = re.compile(r"@prefix\s+([A-Za-z0-9_-]+):\s*<" + re.escape(BASE) + r"([a-z]+)/>")
CURIE_RE = r"(?<![A-Za-z0-9_:])({prefixes}):([A-Za-z0-9]+)(?![A-Za-z0-9])"


def taken_payloads():
    """Payloads of every instance IRI of any kind found in the repository's Turtle and identity table."""
    taken = set()
    for path in sorted((ROOT / "ontology").rglob("*.ttl")):
        text = path.read_text(encoding="utf-8")
        taken.update(IRI_RE.findall(text))
        prefixes = [p for p, _ in PREFIX_RE.findall(text)]
        if prefixes:
            curie = re.compile(CURIE_RE.format(prefixes="|".join(map(re.escape, prefixes))))
            taken.update(payload for _, payload in curie.findall(text))
    table = ROOT / "ontology" / "corpus" / "identity.csv"
    if table.exists():
        with table.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                for cid in [row["canonical_id"]] + [v for v in row["variant_ids"].split(";") if v]:
                    taken.add(cid.split(":", 1)[1])
    return taken


def _keys(payload):
    """The payload and each form of it with one character dropped."""
    return {payload} | {payload[:i] + payload[i + 1:] for i in range(len(payload))}


def new_payload(taken):
    """A fresh payload: not in `taken`, and not one character (substituted, added or dropped) from any member."""
    near = set()
    for p in taken:
        near |= _keys(p)
    while True:
        payload = "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))
        if payload not in taken and not (_keys(payload) & near):
            taken.add(payload)
            return payload


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("prefix", nargs="?", help="ID prefix, e.g. per, plc, ev, grp")
    ap.add_argument("-n", type=int, default=1, help="how many IDs to mint (default 1)")
    ap.add_argument("--known", action="store_true", help="print how many payloads are already taken and exit")
    args = ap.parse_args()
    taken = taken_payloads()
    if args.known:
        print(f"{len(taken)} payloads already in use")
        return 0
    if not args.prefix or not re.fullmatch(r"[a-z]{2,5}", args.prefix):
        ap.error("give a lower-case prefix such as per, plc, ev or grp")
    for _ in range(max(args.n, 1)):
        print(f"{args.prefix}:{new_payload(taken)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
