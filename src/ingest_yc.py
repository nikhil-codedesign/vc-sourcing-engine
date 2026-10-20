"""Fetch Y Combinator climate/energy companies (yc-oss open dataset) into data/calibration_yc.csv.

This is NOT a source of leads. It is a known-positive list used by src/recall.py to measure how many real
climate startups the engine misses. (YC companies are already well known, so they are not under the radar.)
"""
import csv
import os
import sys
from pathlib import Path

import requests

ROOT = Path(os.environ.get("VCSE_ROOT", Path(__file__).resolve().parent.parent))
OUT = ROOT / "data" / "calibration_yc.csv"
URL = "https://yc-oss.github.io/api/companies/all.json"
TAGS = {"climate", "energy", "sustainability", "cleantech", "clean energy", "renewable energy", "carbon",
        "carbon removal", "climate tech", "batteries", "solar", "electric vehicles", "ev charging"}
FIELDS = ["name", "website", "one_liner", "batch", "status", "tags", "industries", "all_locations"]


def main():
    try:
        r = requests.get(URL, timeout=120, headers={"User-Agent": "vc-sourcing-engine"})
        r.raise_for_status()
        companies = r.json()
    except (requests.RequestException, ValueError) as e:
        print(f"WARNING: could not fetch YC list ({type(e).__name__}). Keeping any existing file.")
        return
    keep = []
    for c in companies:
        labels = {str(t).lower() for t in (c.get("tags") or []) + (c.get("industries") or []) + [c.get("subindustry") or ""]}
        if labels & TAGS and c.get("website"):
            keep.append({"name": c.get("name", ""), "website": c.get("website", ""), "one_liner": c.get("one_liner", ""),
                         "batch": c.get("batch", ""), "status": c.get("status", ""),
                         "tags": "; ".join(c.get("tags") or []), "industries": "; ".join(c.get("industries") or []),
                         "all_locations": c.get("all_locations", "")})
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(keep)
    print(f"{len(companies)} YC companies -> {len(keep)} climate/energy with a website. Wrote data/calibration_yc.csv")


if __name__ == "__main__":
    main()
