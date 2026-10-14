"""Day 4: merge raw_github.csv + raw_hn.csv into data/signals.csv and remove duplicates.

Rules:
- Same normalized URL = same company. A Show HN post that links to a GitHub repo is merged into the repo's row
  (source becomes "github+hackernews", HN points/comments are added).
- A Show HN post whose URL equals a repo's homepage is merged the same way.
- Two Show HN posts to the same URL: keep the one with more points.
- Also appends today's numbers to data/snapshots.csv so growth can be computed later (Day 7).
Safe to run repeatedly on the same day.
"""
import csv
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(os.environ.get("VCSE_ROOT", Path(__file__).resolve().parent.parent))
DATA = ROOT / "data"

FIELDS = [
    "source", "name", "url", "description", "stars", "forks", "language", "topics",
    "owner", "owner_type", "homepage", "created_at", "pushed_at", "keyword",
    "hn_points", "hn_comments", "hn_url", "collected_at",
]
SNAP_FIELDS = ["date", "url", "stars", "hn_points", "hn_comments"]


def norm(url):
    """Canonical form of a URL for comparison."""
    url = (url or "").strip().lower()
    if not url:
        return ""
    if "://" not in url:
        url = "http://" + url
    parts = urlsplit(url)
    host = parts.netloc.split("@")[-1]
    host = re.sub(r"^www\.", "", host)
    path = parts.path.rstrip("/")
    path = re.sub(r"\.git$", "", path)
    if host == "github.com":
        path = "/" + "/".join([p for p in path.split("/") if p][:2])
    return host + path


def read(name):
    path = DATA / name
    if not path.exists():
        print(f"(skipping {name}: not found)")
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def main():
    github = read("raw_github.csv")
    hn = read("raw_hn.csv")

    merged = {}      # normalized url -> row
    homepages = {}   # normalized homepage -> normalized url of the row that owns it

    for r in github:
        key = norm(r["url"])
        if not key or key in merged:
            continue
        row = {f: r.get(f, "") for f in FIELDS}
        row["source"] = "github"
        merged[key] = row
        hp = norm(r.get("homepage"))
        if hp and hp != key:
            homepages.setdefault(hp, key)

    for r in hn:
        key = norm(r["url"])
        if not key:
            continue
        if key not in merged and key in homepages:
            key = homepages[key]
        if key in merged:
            row = merged[key]
            if "hackernews" not in row["source"]:
                row["source"] += "+hackernews"
                row["hn_points"], row["hn_comments"], row["hn_url"] = r["hn_points"], r["hn_comments"], r["hn_url"]
            elif num(r["hn_points"]) > num(row["hn_points"]):
                row["hn_points"], row["hn_comments"], row["hn_url"] = r["hn_points"], r["hn_comments"], r["hn_url"]
            continue
        row = {f: r.get(f, "") for f in FIELDS}
        row["source"] = "hackernews"
        merged[key] = row

    rows = sorted(merged.values(), key=lambda r: max(num(r["stars"]), num(r["hn_points"])), reverse=True)

    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / "signals.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    # History for growth numbers: one line per company per day.
    today = datetime.now(timezone.utc).date().isoformat()
    old = [r for r in read("snapshots.csv") if r.get("date") != today]
    with (DATA / "snapshots.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SNAP_FIELDS)
        writer.writeheader()
        writer.writerows(old)
        for r in rows:
            writer.writerow({"date": today, "url": r["url"], "stars": r["stars"],
                             "hn_points": r["hn_points"], "hn_comments": r["hn_comments"]})

    both = sum(1 for r in rows if "+" in r["source"])
    print(f"github in: {len(github)}, hn in: {len(hn)} -> {len(rows)} unique rows "
          f"({both} found on both). Wrote data/signals.csv and data/snapshots.csv")


if __name__ == "__main__":
    main()
