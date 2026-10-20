"""Day 4: merge raw_github.csv + raw_hn.csv + data/manual_leads.csv + raw_sbir.csv (+ raw_nsf.csv by name) into data/signals.csv.

Rules:
- Same normalized URL = same company. A Show HN post that links to a GitHub repo is merged into the repo's row
  (source becomes "github+hackernews", HN points/comments are added).
- A Show HN post whose URL equals a repo's homepage is merged the same way.
- Two Show HN posts to the same URL: keep the one with more points.
- Company-shaped sources (manual leads, SBIR) merge on WEBSITE DOMAIN: acme.com matches a repo whose homepage is
  acme.com/docs. NSF rows have no website, so they match by normalised company name; unmatched grant rows with no
  website go to data/unmatched_grants.csv.
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
    "hn_points", "hn_comments", "hn_url", "country", "source_list",
    "location", "grant_awards", "grant_total", "grant_last_year", "collected_at",
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


CODE_HOSTS = {"github.com", "gitlab.com", "bitbucket.org", "news.ycombinator.com", "huggingface.co", "pypi.org",
              "npmjs.com", "medium.com", "linkedin.com", "twitter.com", "x.com", "youtube.com", "facebook.com",
              "github.io", "substack.com", "google.com", "docs.google.com", "notion.site", "readthedocs.io"}
NAME_SUFFIXES = {"inc", "llc", "corp", "corporation", "ltd", "limited", "co", "company", "pvt", "private", "lp", "llp", "plc"}


def site_key(url):
    """Website domain without www, or "" for code hosts and other sites that say nothing about one company."""
    url = (url or "").strip().lower()
    if not url:
        return ""
    if "://" not in url:
        url = "http://" + url
    host = re.sub(r"^www\.", "", urlsplit(url).netloc.split("@")[-1].split(":")[0])
    if not host or any(host == h or host.endswith("." + h) for h in CODE_HOSTS):
        return ""
    return host


def name_key(name):
    words = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower()).split()
    words = [w for w in words if w not in NAME_SUFFIXES]
    return " ".join(words)


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

    sites, names = {}, {}     # website domain -> row key; normalised name -> row key

    def reindex():
        sites.clear()
        names.clear()
        for k, row in merged.items():
            for u in (row["url"], row["homepage"]):
                sk = site_key(u)
                if sk:
                    sites.setdefault(sk, k)
            nk = name_key(row["name"])
            if len(nk) >= 4:
                names.setdefault(nk, k)

    def find(url, name=""):
        key = norm(url)
        if key in merged:
            return key
        sk = site_key(url)
        if sk and sk in sites:
            return sites[sk]
        nk = name_key(name)
        if not url and len(nk) >= 4 and nk in names:
            return names[nk]
        return None

    def add_source(row, tag):
        if tag not in row["source"].split("+"):
            row["source"] += "+" + tag

    def add_grants(row, r):
        row["grant_awards"] = r.get("grant_awards", "") or row["grant_awards"]
        row["grant_total"] = r.get("grant_total", "") or row["grant_total"]
        row["grant_last_year"] = r.get("grant_last_year", "") or row["grant_last_year"]
        row["location"] = row["location"] or r.get("location", "")

    unmatched = []

    # Hand-curated leads (cohort lists, government compendia, ...): data/manual_leads.csv
    reindex()
    for r in read("manual_leads.csv"):
        url = (r.get("url") or "").strip()
        if url and "://" not in url:
            url = "https://" + url
        if not norm(url):
            continue
        key = find(url)
        if key:
            row = merged[key]
            add_source(row, "manual")
            row["country"] = row["country"] or r.get("country", "")
            row["source_list"] = r.get("source_list", "")
            row["location"] = row["location"] or ", ".join(p for p in (r.get("city"), r.get("country")) if p)
            continue
        row = {f: "" for f in FIELDS}
        row.update({"source": "manual", "name": r.get("name", ""), "url": url, "description": r.get("description", ""),
                    "homepage": url, "country": r.get("country", ""), "source_list": r.get("source_list", ""),
                    "location": ", ".join(p for p in (r.get("city"), r.get("country")) if p),
                    "collected_at": r.get("date_added", "")})
        merged[norm(url)] = row
        reindex()

    # SBIR awardees (one row per firm, usually with a website)
    for r in read("raw_sbir.csv"):
        url = (r.get("url") or "").strip()
        key = find(url, r.get("name", "")) if (norm(url) or r.get("name")) else None
        if key:
            row = merged[key]
            add_source(row, "sbir")
            add_grants(row, r)
            row["country"] = row["country"] or "USA"
            continue
        if not norm(url):
            unmatched.append(r)
            continue
        row = {f: "" for f in FIELDS}
        row.update({"source": "sbir", "name": r.get("name", ""), "url": url, "description": r.get("description", ""),
                    "homepage": url, "country": "USA", "source_list": f"SBIR ({r.get('grant_agency', '')})",
                    "collected_at": r.get("collected_at", "")})
        add_grants(row, r)
        merged[norm(url)] = row
        reindex()

    # NSF awardees: no website, so enrich existing rows by name; keep the rest for a human to look up
    for r in read("raw_nsf.csv"):
        key = find("", r.get("name", ""))
        if key:
            row = merged[key]
            add_source(row, "nsf")
            if not row["grant_awards"]:
                add_grants(row, r)
        else:
            unmatched.append(r)

    if unmatched:
        seen, keep = set(), []
        for r in unmatched:
            nk = name_key(r.get("name", ""))
            if nk not in seen:
                seen.add(nk)
                keep.append(r)
        ufields = ["source", "name", "description", "location", "grant_awards", "grant_total", "grant_last_year"]
        with (DATA / "unmatched_grants.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=ufields, extrasaction="ignore", restval="")
            w.writeheader()
            w.writerows(keep)

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
