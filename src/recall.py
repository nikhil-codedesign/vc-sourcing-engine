"""Calibration: how many known climate startups (YC list) does the engine already have in data/signals.csv?

Matches on website domain. Writes data/recall_report.txt and data/recall_missed.csv.
Low recall is expected for a GitHub/HN-heavy engine; the missed list shows what kind of company it cannot see.
"""
import csv
import os
from pathlib import Path

from dedupe import site_key

ROOT = Path(os.environ.get("VCSE_ROOT", Path(__file__).resolve().parent.parent))
DATA = ROOT / "data"


def read(name):
    p = DATA / name
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    yc, sig = read("calibration_yc.csv"), read("signals.csv")
    if not yc or not sig:
        print("Need data/calibration_yc.csv and data/signals.csv (run Ingest).")
        return
    have = set()
    for r in sig:
        for u in (r.get("url"), r.get("homepage")):
            k = site_key(u)
            if k:
                have.add(k)
    hit = [r for r in yc if site_key(r["website"]) in have]
    miss = [r for r in yc if site_key(r["website"]) not in have]
    text = (f"YC climate/energy companies: {len(yc)}. Found in signals.csv: {len(hit)} "
            f"({100 * len(hit) / len(yc):.0f}% recall by website domain).\n")
    (DATA / "recall_report.txt").write_text(text)
    with (DATA / "recall_missed.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(yc[0].keys()))
        w.writeheader()
        w.writerows(miss)
    print(text.strip())


if __name__ == "__main__":
    main()
