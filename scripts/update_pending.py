#!/usr/bin/env python3
"""
Refresh the "Not assessed yet" list for the Preprint -> Publication site.

What it does
------------
bioRxiv links each preprint to its peer-reviewed publication, but that linkage
lags (often by months). The study corpus (data/index.json) only contains pairs
that were already linked when the data was harvested, so genuinely-published
preprints that were linked afterwards are missing.

This script asks bioRxiv's public "published" API for every preprint linked to a
journal article in a date window, keeps the ones that are NOT already in the
assessed corpus, and writes them to:

    data/pending.json           (one row per pending pair, same schema as index.json,
                                 with the change label set to "na" = not assessed yet)
    data/pending_authors.json   (parsed [surname, given] author lists, for name search)

These show up on the site with a "Not assessed yet" tag. They are NOT scored by
the LLM here — assessment (content change / hedging / claim type) is a separate
step in the extraction pipeline. Run this whenever you want the site to reflect
newly-published preprints; re-run the full extraction every few months to move
them from "pending" into the labelled corpus.

Usage
-----
    python3 scripts/update_pending.py --from 2025-01-01 --to 2026-12-31

Then:
    git add data/pending.json data/pending_authors.json
    git commit -m "Refresh not-assessed list"
    git push

Notes
-----
* Only the standard library is used (urllib) - no pip install needed.
* A pair can appear here if it was excluded from the study by a filter
  (e.g. very short abstract) rather than being brand new; this is rare and
  harmless for display purposes.
"""

import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
API = "https://api.biorxiv.org/pubs/biorxiv/{frm}/{to}/{cursor}"
PENDING_ID_BASE = 1_000_000  # keep pending ids clear of the 0..N-1 corpus ids


def fetch_published(frm, to):
    """Yield every published-preprint record from bioRxiv in [frm, to]."""
    cursor = 0
    while True:
        url = API.format(frm=frm, to=to, cursor=cursor)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    payload = json.loads(r.read().decode())
                break
            except Exception as e:  # transient network / rate limit
                if attempt == 3:
                    raise
                time.sleep(2 * (attempt + 1))
        msg = (payload.get("messages") or [{}])[0]
        coll = payload.get("collection") or []
        if not coll:
            break
        for c in coll:
            yield c
        total = int(msg.get("total", 0) or 0)
        count = int(msg.get("count", 0) or 0)
        cursor += count if count else len(coll)
        print(f"  ...{cursor}/{total}", file=sys.stderr)
        if count == 0 or cursor >= total:
            break
        time.sleep(0.34)  # be polite to the API


def parse_authors(preprint_authors, corresponding):
    """Parse 'Last, F.; Last, F.' + a corresponding full name into [surname, given]."""
    out = []
    for chunk in (preprint_authors or "").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        surname, given = (chunk.split(",", 1)) if "," in chunk else (chunk, "")
        surname = re.sub(r"[^a-z]", "", surname.lower())
        given = [t for t in re.sub(r"[^a-z]", " ", given.lower()).split() if t]
        if surname:
            out.append([surname, " ".join(given)])
    c = [t for t in re.sub(r"[^a-z]", " ", (corresponding or "").lower()).split() if t]
    if len(c) >= 2:
        out.append([c[-1], " ".join([c[0]] + c[1:-1])])  # surname = last token
    elif len(c) == 1:
        out.append([c[0], ""])
    return out


def days_between(p, j):
    try:
        return (date.fromisoformat(j) - date.fromisoformat(p)).days
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="Refresh the not-assessed list.")
    ap.add_argument("--from", dest="frm", default="2025-01-01", help="publication date from (YYYY-MM-DD)")
    ap.add_argument("--to", dest="to", default=str(date.today()), help="publication date to (YYYY-MM-DD)")
    args = ap.parse_args()

    # DOIs already assessed in the corpus (field [1] = bioRxiv DOI)
    index = json.loads((DATA / "index.json").read_text())
    corpus = {row[1] for row in index}
    print(f"Assessed corpus: {len(corpus):,} pairs. Harvesting bioRxiv publications "
          f"{args.frm} -> {args.to} ...", file=sys.stderr)

    pending, pending_authors, seen = [], [], set()
    i = 0
    for c in fetch_published(args.frm, args.to):
        doi = c.get("biorxiv_doi")
        if not doi or doi in corpus or doi in seen:
            continue
        seen.add(doi)
        authors = c.get("preprint_authors", "") or ""
        corr = c.get("preprint_author_corresponding", "") or ""
        pdate = c.get("preprint_date", "") or ""
        jdate = c.get("published_date", "") or ""
        year = int(pdate[:4]) if pdate[:4].isdigit() else None
        first = authors.split(";")[0].strip() if authors else ""
        pending.append([
            PENDING_ID_BASE + i, doi, c.get("published_doi", "") or "",
            c.get("preprint_title", "") or "", first, corr,
            c.get("preprint_author_corresponding_institution", "") or "",
            (c.get("preprint_category", "") or "").lower(),
            c.get("published_journal", "") or "", year, days_between(pdate, jdate),
            None, "",            # impact, quartile (unknown until assessed)
            "na", "na",          # content label / hedging -> not assessed
            "", "", 0,           # preType, pubType, typeChanged
            "", "", "", "",      # s1/s2 labels
            "",                  # published primary claim (none yet)
        ])
        pending_authors.append(parse_authors(authors, corr))
        i += 1

    if not pending:
        print("WARNING: found 0 new pairs. This almost always means api.biorxiv.org could not be "
              "reached (corporate VPN / proxy / firewall), not that there is nothing to add.\n"
              "Leaving the existing data/pending.json UNCHANGED so the current list is not wiped.\n"
              "Re-run from a network that can reach api.biorxiv.org.", file=sys.stderr)
        return
    (DATA / "pending.json").write_text(json.dumps(pending, separators=(",", ":"), ensure_ascii=False))
    (DATA / "pending_authors.json").write_text(json.dumps(pending_authors, separators=(",", ":"), ensure_ascii=False))
    print(f"Wrote {len(pending):,} not-assessed pairs to data/pending.json", file=sys.stderr)
    print("Next: git add data/pending.json data/pending_authors.json && git commit && git push", file=sys.stderr)


if __name__ == "__main__":
    main()
