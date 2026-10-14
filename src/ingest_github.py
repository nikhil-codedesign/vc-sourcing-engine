"""Day 3: collect candidate repos from GitHub search into data/signals.csv.

Reads search keywords from config/keywords.txt (one per line).
Uses only the official GitHub REST API. No scraping.
"""
import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
KEYWORDS_FILE = ROOT / "config" / "keywords.txt"
OUT_FILE = ROOT / "data" / "raw_github.csv"

PAGES_PER_KEYWORD = 2   # 2 pages x 50 = up to 100 results per keyword
PER_PAGE = 50
MIN_STARS = 3           # skip empty/abandoned experiments

FIELDS = [
    "source", "name", "url", "description", "stars", "forks", "language",
    "topics", "owner", "owner_type", "homepage", "created_at", "pushed_at",
    "keyword", "collected_at",
]


def load_keywords():
    if not KEYWORDS_FILE.exists():
        sys.exit(f"Missing {KEYWORDS_FILE.relative_to(ROOT)}. Complete Day 2 first.")
    lines = [l.strip() for l in KEYWORDS_FILE.read_text().splitlines()]
    keywords = [l for l in lines if l and not l.startswith("#")]
    if not keywords:
        sys.exit("config/keywords.txt is empty.")
    return keywords


def search(keyword, session):
    rows = []
    for page in range(1, PAGES_PER_KEYWORD + 1):
        resp = session.get(
            "https://api.github.com/search/repositories",
            params={
                "q": f"{keyword} stars:>={MIN_STARS} fork:false archived:false",
                "sort": "updated",
                "order": "desc",
                "per_page": PER_PAGE,
                "page": page,
            },
            timeout=30,
        )
        if resp.status_code in (403, 429):
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(5, min(reset - int(time.time()) + 2, 90))
            print(f"Rate limited. Waiting {wait}s...")
            time.sleep(wait)
            resp = session.get(resp.url, timeout=30)
        if resp.status_code != 200:
            print(f"  ! '{keyword}' page {page}: HTTP {resp.status_code} {resp.text[:200]}")
            break
        items = resp.json().get("items", [])
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for r in items:
            rows.append({
                "source": "github",
                "name": r["full_name"],
                "url": r["html_url"],
                "description": (r.get("description") or "").replace("\n", " ").strip(),
                "stars": r["stargazers_count"],
                "forks": r["forks_count"],
                "language": r.get("language") or "",
                "topics": ";".join(r.get("topics", [])),
                "owner": r["owner"]["login"],
                "owner_type": r["owner"]["type"],
                "homepage": r.get("homepage") or "",
                "created_at": r["created_at"],
                "pushed_at": r["pushed_at"],
                "keyword": keyword,
                "collected_at": now,
            })
        if len(items) < PER_PAGE:
            break
        time.sleep(2.5)  # stay under the search rate limit
    return rows


def main():
    session = requests.Session()
    session.headers.update({
        "Accept": "application/vnd.github+json",
        "User-Agent": "vc-sourcing-engine",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"

    seen = {}
    for kw in load_keywords():
        print(f"Searching: {kw}")
        for row in search(kw, session):
            seen.setdefault(row["url"], row)  # first keyword wins
        time.sleep(2.5)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(seen.values())
    print(f"Wrote {len(seen)} rows to {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
