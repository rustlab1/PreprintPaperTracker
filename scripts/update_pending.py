#!/usr/bin/env python3
"""
Refresh the "Not assessed yet" list for the Preprint -> Publication site.

The assessed corpus (data/index.json) only covers preprints published in a
journal up to ~Feb 2025. bioRxiv keeps linking older preprints to journal
articles every day, so anything published since then is "published but not yet
assessed". This script harvests those from bioRxiv's public "published" API,
keeps the ones NOT already in the corpus, and writes:

    data/pending.json           (one row per pending pair, same schema as index.json,
                                 change label = "na" = not assessed yet)
    data/pending_authors.json   (parsed [surname, given] author lists, for name search)

They show on the site with a "Not assessed yet" tag. No LLM scoring happens here;
assessment (content change / hedging / claim type) is a separate extraction step.

Usage
-----
    python3 scripts/update_pending.py                 # default: 2025-03-01 -> today
    python3 scripts/update_pending.py --from 2025-03-01 --to 2026-12-31

Then:
    git add data/pending.json data/pending_authors.json
    git commit -m "Refresh not-assessed list"
    git push

Only the standard library is used (urllib) - no pip install. Must run from a
network that can reach api.biorxiv.org (corporate VPNs sometimes block it).
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
            except Exception:
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
        time.sleep(0.34)


def g(rec, *keys):
    """First non-empty value among several possible key names (API field names vary)."""
    for k in keys:
        v = rec.get(k)
        if v not in (None, ""):
            return v
    return ""


def parse_authors(preprint_authors, corresponding):
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
        out.append([c[-1], " ".join([c[0]] + c[1:-1])])
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
    ap.add_argument("--from", dest="frm", default="2025-03-01", help="publication date from (YYYY-MM-DD)")
    ap.add_argument("--to", dest="to", default=str(date.today()), help="publication date to (YYYY-MM-DD)")
    args = ap.parse_args()

    index = json.loads((DATA / "index.json").read_text())
    corpus = {row[1] for row in index}
    print(f"Assessed corpus: {len(corpus):,} pairs. Harvesting bioRxiv publications "
          f"{args.frm} -> {args.to} ...", file=sys.stderr)

    pending, pending_authors, seen = [], [], set()
    n_fetched = n_in_corpus = n_nodoi = 0
    i = 0
    for c in fetch_published(args.frm, args.to):
        if n_fetched == 0:  # show the real field names once, for transparency
            print("First record keys:", sorted(c.keys()), file=sys.stderr)
        n_fetched += 1
        doi = g(c, "biorxiv_doi", "preprint_doi", "doi")
        if not doi:
            n_nodoi += 1
            continue
        if doi in corpus:
            n_in_corpus += 1
            continue
        if doi in seen:
            continue
        seen.add(doi)
        authors = g(c, "preprint_authors", "authors")
        corr = g(c, "preprint_author_corresponding", "author_corresponding")
        pdate = g(c, "preprint_date")
        jdate = g(c, "published_date")
        year = int(pdate[:4]) if pdate[:4].isdigit() else None
        first = authors.split(";")[0].strip() if authors else ""
        pending.append([
            PENDING_ID_BASE + i, doi, g(c, "published_doi", "journal_doi"),
            g(c, "preprint_title", "title"), first, corr,
            g(c, "preprint_author_corresponding_institution", "author_corresponding_institution"),
            (g(c, "preprint_category", "category") or "").lower(),
            g(c, "published_journal", "journal"), year, days_between(pdate, jdate),
            None, "",            # impact, quartile (unknown until assessed)
            "na", "na",          # content label / hedging -> not assessed
            "", "", 0,           # preType, pubType, typeChanged
            "", "", "", "",      # s1/s2 labels
            "",                  # published primary claim (none yet)
        ])
        pending_authors.append(parse_authors(authors, corr))
        i += 1

    print(f"Fetched {n_fetched:,} | already in corpus {n_in_corpus:,} | "
          f"missing DOI {n_nodoi:,} | NEW not-assessed {len(pending):,}", file=sys.stderr)

    if not pending:
        if n_fetched == 0:
            print("WARNING: could not fetch anything from api.biorxiv.org (likely a VPN / proxy / "
                  "firewall block). Leaving data/pending.json UNCHANGED. Re-run from an open network.",
                  file=sys.stderr)
        else:
            print("Nothing new to add; left data/pending.json unchanged.", file=sys.stderr)
        return
    (DATA / "pending.json").write_text(json.dumps(pending, separators=(",", ":"), ensure_ascii=False))
    (DATA / "pending_authors.json").write_text(json.dumps(pending_authors, separators=(",", ":"), ensure_ascii=False))
    print(f"Wrote {len(pending):,} not-assessed pairs to data/pending.json", file=sys.stderr)
    print("Next: git add data/pending.json data/pending_authors.json && git commit -m 'Refresh not-assessed list' && git push", file=sys.stderr)


if __name__ == "__main__":
    main()
