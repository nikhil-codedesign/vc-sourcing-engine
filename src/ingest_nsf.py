"""Collect NSF SBIR/STTR awards (grants to small companies) from the NSF Awards API into data/raw_nsf.csv.

The NSF API returns the company NAME but no website, so these rows cannot be keyed by URL. dedupe.py matches them
to existing companies by name; unmatched ones go to data/nsf_unmatched.csv for you to look up by hand.
Env vars (optional): NSF_YEARS (look-back in years, default 3), NSF_MAX_PAGES (pages of 25 per keyword, default 6).
Fails soft: if the API errors, prints a warning and exits 0.
UNVERIFIED: the research.gov docs page is blocked to automated readers, so the parameters below come from
memory of the public API. Check the first run's log and fix here if a field name is wrong.
"""
import csv
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(os.environ.get("VCSE_ROOT", Path(__file__).resolve().parent.parent))
KEYWORDS_FILE = ROOT / "config" / "nsf_keywords.txt"
OUT_FILE = ROOT / "data" / "raw_nsf.csv"
API = "https://api.nsf.gov/services/v1/awards.json"
YEARS = int(os.environ.get("NSF_YEARS") or 3)
MAX_PAGES = int(os.environ.get("NSF_MAX_PAGES") or 6)
RPP = 25
PRINT = "id,title,awardeeName,awardeeCity,awardeeStateCode,startDate,fundsObligatedAmt,fundProgramName,abstractText"
FIELDS = ["source", "name", "description", "location", "grant_awards", "grant_total", "grant_last_year",
          "nsf_ids", "keyword", "collected_at"]


def keywords():
    if not KEYWORDS_FILE.exists():
        sys.exit("Missing config/nsf_keywords.txt")
    return [l.strip() for l in KEYWORDS_FILE.read_text().splitlines() if l.strip() and not l.startswith("#")]


def search(kw):
    since = (datetime.now(timezone.utc) - timedelta(days=365 * YEARS)).strftime("%m/%d/%Y")
    out = []
    for page in range(MAX_PAGES):
        params = {"keyword": kw, "dateStart": since, "printFields": PRINT, "rpp": RPP, "offset": page * RPP + 1}
        try:
            r = requests.get(API, params=params, timeout=60, headers={"User-Agent": "vc-sourcing-engine"})
            data = r.json() if r.status_code == 200 else {}
        except (requests.RequestException, ValueError) as e:
            print(f"  {kw!r} page {page}: {type(e).__name__}")
            break
        if r.status_code != 200 or "response" not in data:
            print(f"  {kw!r} page {page}: HTTP {r.status_code} {str(data)[:120]}")
            break
        awards = data["response"].get("award") or []
        out.extend(awards)
        if len(awards) < RPP:
            break
        time.sleep(1)
    return out


def main():
    firms, seen_ids = {}, set()
    for kw in keywords():
        got = [a for a in search(kw) if any(t in (a.get("fundProgramName") or "").upper() for t in ("SBIR", "STTR"))]
        print(f"{kw!r}: {len(got)} SBIR/STTR awards")
        for a in got:
            if a.get("id") in seen_ids:
                continue
            seen_ids.add(a.get("id"))
            name = (a.get("awardeeName") or "").strip()
            if not name:
                continue
            f = firms.setdefault(name.lower(), {"name": name, "n": 0, "total": 0, "last": 0, "ids": [], "kw": kw,
                                                "title": "", "abstract": "", "loc": ""})
            f["n"] += 1
            try:
                f["total"] += int(float(a.get("fundsObligatedAmt") or 0))
            except ValueError:
                pass
            yr = int((a.get("startDate") or "0000")[-4:] or 0)
            f["ids"].append(str(a.get("id")))
            if yr >= f["last"]:
                f["last"], f["title"], f["abstract"] = yr, a.get("title") or "", (a.get("abstractText") or "")
                f["loc"] = ", ".join(p for p in (a.get("awardeeCity"), a.get("awardeeStateCode"), "USA") if p)
    if not firms:
        print("WARNING: no NSF data returned. Keeping any existing raw_nsf.csv.")
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with OUT_FILE.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for f in firms.values():
            w.writerow({"source": "nsf", "name": f["name"], "description": f"{f['title']}. {f['abstract']}"[:600],
                        "location": f["loc"], "grant_awards": f["n"], "grant_total": f["total"],
                        "grant_last_year": f["last"] or "", "nsf_ids": " ".join(f["ids"][:5]),
                        "keyword": f["kw"], "collected_at": now})
    print(f"{len(seen_ids)} awards -> {len(firms)} firms. Wrote data/raw_nsf.csv")


if __name__ == "__main__":
    main()
