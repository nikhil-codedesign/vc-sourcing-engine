"""Collect US government SBIR/STTR awards (grants to small companies) from the sbir.gov API into data/raw_sbir.csv.

One row per FIRM (awards are rolled up). Company-shaped: a firm with an award is a real, registered company
that is funded but usually unfunded by VCs, which is what "under the radar" looks like.
Env vars (optional): SBIR_AGENCIES (default "DOE"), SBIR_YEARS (how many calendar years back, default 3),
SBIR_MAX_PAGES (pages of 100 per agency-year, default 30).
The sbir.gov API has been flagged "under maintenance" and has no keyword search, so this script fails soft:
if the API errors, it prints a warning, keeps any existing raw_sbir.csv and exits 0.
"""
import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(os.environ.get("VCSE_ROOT", Path(__file__).resolve().parent.parent))
OUT_FILE = ROOT / "data" / "raw_sbir.csv"
API = "https://api.www.sbir.gov/public/api/awards"
AGENCIES = [a.strip().upper() for a in (os.environ.get("SBIR_AGENCIES") or "DOE").split(",") if a.strip()]
YEARS = int(os.environ.get("SBIR_YEARS") or 3)
MAX_PAGES = int(os.environ.get("SBIR_MAX_PAGES") or 30)
ROWS = 100

FIELDS = ["source", "name", "url", "description", "location", "grant_awards", "grant_total",
          "grant_first_year", "grant_last_year", "grant_agency", "employees", "collected_at"]


def fetch(agency, year):
    out = []
    for page in range(MAX_PAGES):
        params = {"agency": agency, "year": year, "rows": ROWS, "start": page * ROWS}
        for attempt in range(3):
            try:
                r = requests.get(API, params=params, timeout=60, headers={"User-Agent": "vc-sourcing-engine"})
                if r.status_code == 200:
                    data = r.json()
                    break
                print(f"  {agency} {year} page {page}: HTTP {r.status_code}")
            except (requests.RequestException, ValueError) as e:
                print(f"  {agency} {year} page {page}: {type(e).__name__}")
            time.sleep(5 * (attempt + 1))
        else:
            return out, False
        if not isinstance(data, list) or not data:
            break
        out.extend(data)
        if len(data) < ROWS:
            break
        time.sleep(1)
    return out, True


def clean_url(u):
    u = (u or "").strip()
    if not u or u.lower() in ("n/a", "none", "na", "-"):
        return ""
    return u if "://" in u else "https://" + u


def to_float(v):
    try:
        return float(str(v).replace(",", "").replace("$", ""))
    except ValueError:
        return 0.0


def main():
    this_year = datetime.now(timezone.utc).year
    firms, ok_all, total = {}, True, 0
    for agency in AGENCIES:
        for year in range(this_year, this_year - YEARS, -1):
            awards, ok = fetch(agency, year)
            ok_all = ok_all and ok
            total += len(awards)
            print(f"{agency} {year}: {len(awards)} awards{'' if ok else ' (stopped early)'}")
            for a in awards:
                name = (a.get("firm") or "").strip()
                if not name:
                    continue
                f = firms.setdefault(name.lower(), {
                    "name": name, "url": "", "title": "", "abstract": "", "city": "", "state": "",
                    "n": 0, "total": 0.0, "first": 9999, "last": 0, "agency": agency, "emp": ""})
                yr = int(to_float(a.get("award_year")) or 0)
                f["n"] += 1
                f["total"] += to_float(a.get("award_amount"))
                f["first"] = min(f["first"], yr or 9999)
                f["url"] = f["url"] or clean_url(a.get("company_url"))
                f["emp"] = f["emp"] or str(a.get("number_employees") or "")
                if yr >= f["last"]:
                    f["last"] = yr
                    f["title"] = (a.get("award_title") or "").strip()
                    f["abstract"] = (a.get("abstract") or "").strip()
                    f["city"], f["state"] = a.get("city") or "", a.get("state") or ""
    if not firms:
        print("WARNING: no SBIR data returned (API down or changed). Keeping any existing raw_sbir.csv.")
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for f in firms.values():
            desc = f"{f['title']}. {f['abstract']}"[:600]
            w.writerow({"source": "sbir", "name": f["name"], "url": f["url"], "description": desc,
                        "location": ", ".join(p for p in (f["city"], f["state"], "USA") if p),
                        "grant_awards": f["n"], "grant_total": int(f["total"]),
                        "grant_first_year": f["first"] if f["first"] != 9999 else "", "grant_last_year": f["last"] or "",
                        "grant_agency": f["agency"], "employees": f["emp"], "collected_at": now})
    print(f"{total} awards -> {len(firms)} firms ({sum(1 for f in firms.values() if f['url'])} with a website). "
          f"Wrote data/raw_sbir.csv{'' if ok_all else ' (some pages failed)'}")


if __name__ == "__main__":
    main()
