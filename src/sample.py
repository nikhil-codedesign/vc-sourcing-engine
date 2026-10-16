"""Day 5: draw a random sample of companies from data/signals.csv for you to label by hand.

Env vars: SAMPLE_SIZE (default 30), SAMPLE_OUT (default gold_sample.csv),
SAMPLE_SEED (default 42), SAMPLE_OVERWRITE ("true" to replace an existing file).
SAMPLE_POOL: "random" draws from everything; "model_keep" / "model_reject" draw only from what the filter
kept / rejected (needs data/filtered.csv). The verdict itself is NOT written to the sample, so you label blind.
Never reuses a company that is already in another gold*.csv file, so a second sample is a fresh blind test set.
"""
import csv
import os
import random
import sys
from pathlib import Path

ROOT = Path(os.environ.get("VCSE_ROOT", Path(__file__).resolve().parent.parent))
DATA = ROOT / "data"

SIZE = int(os.environ.get("SAMPLE_SIZE") or 30)
OUT = os.environ.get("SAMPLE_OUT") or "gold_sample.csv"
SEED = int(os.environ.get("SAMPLE_SEED") or 42)
OVERWRITE = (os.environ.get("SAMPLE_OVERWRITE") or "").lower() == "true"
POOL = (os.environ.get("SAMPLE_POOL") or "random").lower()   # random | model_keep | model_reject

FIELDS = ["url", "name", "source", "description", "topics", "owner", "owner_type", "homepage",
          "stars", "hn_points", "created_at", "pushed_at", "my_label", "my_reason"]


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    out_path = DATA / OUT
    if out_path.exists() and not OVERWRITE:
        print(f"{OUT} already exists, leaving it alone (your labels may depend on it). "
              f"Set overwrite to true to replace it.")
        return
    if not (DATA / "signals.csv").exists():
        sys.exit("data/signals.csv not found. Run Ingest first.")

    signals = read(DATA / "signals.csv")
    if POOL in ("model_keep", "model_reject"):
        want = POOL.split("_")[1]
        filtered = read(DATA / "filtered.csv")
        signals = [r for r in filtered if r.get("filter_verdict") == want]
        if not signals:
            sys.exit(f"No rows the filter marked '{want}' yet. Run Filter with scope=all first.")
    used = set()
    for base in (DATA, ROOT):
        for p in base.glob("gold*.csv"):
            if p.resolve() != out_path.resolve():
                used.update(r.get("url", "") for r in read(p))
    pool = [r for r in signals if r["url"] not in used]
    if len(pool) < SIZE:
        sys.exit(f"Only {len(pool)} unused companies available, wanted {SIZE}.")

    picked = random.Random(SEED).sample(pool, SIZE)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(picked)
    print(f"Wrote {SIZE} companies to data/{OUT} (pool: {POOL}, {len(pool)} available).")


if __name__ == "__main__":
    main()
