"""Day 4: collect Show HN posts from the official Hacker News (Algolia) API into data/raw_hn.csv.

Reads search phrases from config/hn_keywords.txt (one per line). No key or account needed.
Env vars (optional): HN_DAYS (look-back window, default 540), HN_MIN_POINTS (default 3).
"""
import csv
import html
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(os.environ.get("VCSE_ROOT", Path(__file__).resolve().parent.parent))
KEYWORDS_FILE = ROOT / "config" / "hn_keywords.txt"
OUT_FILE = ROOT / "data" / "raw_hn.csv"

DAYS = int(os.environ.get("HN_DAYS", "540"))
MIN_POINTS = int(os.environ.get("HN_MIN_POINTS", "3"))
PAGES = 3          # up to 300 posts per keyword
PER_PAGE = 100

FIELDS = [
    "source", "name", "url", "description", "owner", "created_at",
    "hn_points", "hn_comments", "hn_url", "keyword", "collected_at",
]


def load_keywords():
    if not KEYWORDS_FILE.exists():
        sys.exit(f"Missing {KEYWORDS_FILE.relative_to(ROOT)}.")
    lines = [l.strip() for l in KEYWORDS_FILE.read_text().splitlines()]
    keywords = [l for l in lines if l and not l.startswith("#")]
    if not keywords:
        sys.exit("config/hn_keywords.txt is empty.")
    return keywords


def clean(text, limit=400):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def fetch(keyword, since_ts):
    rows = []
    for page in range(PAGES):
        params = {
            "query": keyword,
            "tags": "show_hn",
            "numericFilters": f"created_at_i>{since_ts},points>={MIN_POINTS}",
            "hitsPerPage": PER_PAGE,
            "page": page,
        }
        data = None
        for attempt in range(1, 5):
            resp = requests.get("https://hn.algolia.com/api/v1/search", params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                break
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(5 * attempt)
                continue
            print(f"  ! '{keyword}' page {page}: HTTP {resp.status_code} {resp.text[:150]}")
            break
        if data is None:
            break
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for h in data.get("hits", []):
            item_id = h.get("objectID")
            hn_url = f"https://news.ycombinator.com/item?id={item_id}"
            title = re.sub(r"^\s*Show HN:\s*", "", h.get("title") or "", flags=re.I).strip()
            rows.append({
                "source": "hackernews",
                "name": title,
                "url": h.get("url") or hn_url,
                "description": clean(h.get("story_text")),
                "owner": h.get("author") or "",
                "created_at": h.get("created_at") or "",
                "hn_points": h.get("points") or 0,
                "hn_comments": h.get("num_comments") or 0,
                "hn_url": hn_url,
                "keyword": keyword,
                "collected_at": now,
            })
        if page + 1 >= data.get("nbPages", 0):
            break
        time.sleep(0.5)
    return rows


def main():
    since_ts = int(time.time()) - DAYS * 86400
    seen = {}
    for kw in load_keywords():
        print(f"Searching HN: {kw}")
        for row in fetch(kw, since_ts):
            seen.setdefault(row["hn_url"], row)  # same post under several keywords: keep the first
        time.sleep(0.5)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(seen.values())
    print(f"Wrote {len(seen)} rows to {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
