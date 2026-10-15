"""Day 5: classify every signal as keep/reject using the thesis, then compare with your hand labels.

Inputs : data/signals.csv, thesis.md, prompts/filter.txt, your labeled files (gold*labeled*.csv in data/ or repo root)
Outputs: data/filtered.csv, data/filter_report.csv, data/filter_disagreements.csv, data/filter_cache.csv
Env    : FILTER_SCOPE ("all" or "gold"), FILTER_BATCH (companies per AI call, default 8)

Results are cached per (company, prompt+model). Re-running only classifies what is new or changed,
and if the free daily quota runs out the run stops cleanly and resumes next time.
"""
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm  # noqa: E402

ROOT = Path(os.environ.get("VCSE_ROOT", Path(__file__).resolve().parent.parent))
DATA = ROOT / "data"
BATCH = int(os.environ.get("FILTER_BATCH") or 8)
SCOPE = (os.environ.get("FILTER_SCOPE") or "all").lower()

CATEGORIES = {
    "startup_or_product", "open_core_with_company", "academic_or_research", "student_or_tutorial",
    "personal_project", "list_or_docs", "nonprofit_or_standards", "services_or_agency",
    "thin_wrapper", "out_of_scope", "unclear",
}
CACHE_FIELDS = ["url", "prompt_hash", "verdict", "category", "reason", "model", "date"]
EXTRA = ["filter_verdict", "filter_category", "filter_reason"]


def read_csv(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def gold_paths():
    found = set()
    for base in (DATA, ROOT):
        if base.exists():
            found.update(base.glob("gold*.csv"))
    return sorted(found)


def build_prompt():
    prompt = (ROOT / "prompts" / "filter.txt").read_text(encoding="utf-8")
    thesis = (ROOT / "thesis.md").read_text(encoding="utf-8")
    system = prompt.replace("{THESIS}", thesis)
    return system, hashlib.sha1((system + llm.MODEL).encode("utf-8")).hexdigest()[:10]


def payload(row, i):
    def cut(key, n):
        return (row.get(key) or "")[:n]
    return {
        "id": i, "name": cut("name", 120), "source": row.get("source", ""), "url": cut("url", 200),
        "description": cut("description", 320), "topics": cut("topics", 120), "owner": cut("owner", 60),
        "owner_type": row.get("owner_type", ""), "homepage": cut("homepage", 120),
        "stars": row.get("stars", ""), "hn_points": row.get("hn_points", ""),
        "created_at": cut("created_at", 10), "pushed_at": cut("pushed_at", 10),
    }


def classify(batch, system):
    items = [payload(r, i) for i, r in enumerate(batch)]
    out = llm.ask_json("CANDIDATES:\n" + json.dumps(items, ensure_ascii=False), system=system)
    if isinstance(out, dict):
        out = next((v for v in out.values() if isinstance(v, list)), [])
    results = {}
    for o in out if isinstance(out, list) else []:
        try:
            i = int(o["id"])
        except (KeyError, TypeError, ValueError):
            continue
        verdict = str(o.get("verdict", "")).strip().lower()
        if 0 <= i < len(batch) and verdict in ("keep", "reject"):
            cat = str(o.get("category", "unclear")).strip().lower()
            results[i] = (verdict, cat if cat in CATEGORIES else "unclear", str(o.get("reason", ""))[:200])
    return results


def classify_with_retry(batch, system):
    results = classify(batch, system)
    missing = [i for i in range(len(batch)) if i not in results]
    if missing:  # the model skipped some: ask once more for just those
        sub = classify([batch[i] for i in missing], system)
        for j, i in enumerate(missing):
            if j in sub:
                results[i] = sub[j]
    return results


def compare(set_name, labeled, verdicts, disagreements):
    stats = Counter()
    invalid = 0
    for r in labeled:
        mine = (r.get("my_label") or "").strip().lower()
        if mine not in ("keep", "reject"):
            invalid += 1
            continue
        v = verdicts.get(r["url"])
        if not v:
            stats["not_classified_yet"] += 1
            continue
        theirs = v["verdict"]
        stats["compared"] += 1
        stats[f"you_{mine}"] += 1
        stats[f"model_{theirs}"] += 1
        if mine == theirs:
            stats["agree"] += 1
        else:
            stats["model_kept_you_rejected" if theirs == "keep" else "model_rejected_you_kept"] += 1
            disagreements.append({
                "set": set_name, "name": r.get("name", ""), "url": r["url"],
                "description": (r.get("description") or "")[:200],
                "my_label": mine, "my_reason": r.get("my_reason", ""),
                "model_verdict": theirs, "model_category": v["category"], "model_reason": v["reason"],
            })
    n = stats["compared"]
    both_keep = stats["you_keep"] - stats["model_rejected_you_kept"]
    rows = [
        ("rows_in_file", len(labeled)),
        ("rows_without_valid_label", invalid),
        ("not_classified_yet", stats["not_classified_yet"]),
        ("compared", n),
        ("agree", f'{stats["agree"]} of {n}'),
        ("agreement_pct", f'{100 * stats["agree"] / n:.1f}' if n else ""),
        ("you_keep", stats["you_keep"]), ("you_reject", stats["you_reject"]),
        ("model_keep", stats["model_keep"]), ("model_reject", stats["model_reject"]),
        ("model_rejected_but_you_kept (costly misses)", stats["model_rejected_you_kept"]),
        ("model_kept_but_you_rejected (extra work)", stats["model_kept_you_rejected"]),
        ("share_of_your_keeps_the_model_kept_pct",
         f'{100 * both_keep / stats["you_keep"]:.1f}' if stats["you_keep"] else ""),
        ("share_of_model_keeps_you_agree_pct",
         f'{100 * both_keep / stats["model_keep"]:.1f}' if stats["model_keep"] else ""),
    ]
    return [{"set": set_name, "metric": m, "value": v} for m, v in rows]


def main():
    signals = read_csv(DATA / "signals.csv")
    if not signals:
        sys.exit("data/signals.csv is missing or empty. Run Ingest first.")
    system, phash = build_prompt()
    print(f"Model: {llm.MODEL} | prompt version: {phash} | scope: {SCOPE}")

    gold_rows = {}
    for p in gold_paths():
        for r in read_csv(p):
            if r.get("url"):
                gold_rows.setdefault(r["url"], r)
    by_url = {r["url"]: r for r in signals}
    extras = [r for u, r in gold_rows.items() if u not in by_url]  # labeled companies that left the search results

    cache = {}
    for r in read_csv(DATA / "filter_cache.csv"):
        if r["prompt_hash"] == phash:
            cache[r["url"]] = r

    ordered = [r for r in signals if r["url"] in gold_rows] + extras + \
              [r for r in signals if r["url"] not in gold_rows]
    if SCOPE == "gold":
        ordered = [r for r in ordered if r["url"] in gold_rows]
    pending = [r for r in ordered if r["url"] not in cache]
    print(f"{len(ordered)} companies in scope, {len(ordered) - len(pending)} already classified, "
          f"{len(pending)} to do ({-(-len(pending) // BATCH)} AI calls).")

    stopped_early = False
    cache_path = DATA / "filter_cache.csv"
    new_file = not cache_path.exists()
    DATA.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    with cache_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CACHE_FIELDS)
        if new_file:
            writer.writeheader()
        for start in range(0, len(pending), BATCH):
            batch = pending[start:start + BATCH]
            try:
                results = classify_with_retry(batch, system)
            except llm.QuotaExhausted as e:
                print(f"STOPPED EARLY: {e} Progress is saved; run Filter again later.")
                stopped_early = True
                break
            for i, (verdict, cat, reason) in results.items():
                row = {"url": batch[i]["url"], "prompt_hash": phash, "verdict": verdict,
                       "category": cat, "reason": reason, "model": llm.MODEL, "date": today}
                writer.writerow(row)
                cache[row["url"]] = row
            f.flush()
            print(f"  classified {min(start + BATCH, len(pending))}/{len(pending)}")

    # Full output for every company in signals.csv
    fields = list(signals[0].keys()) + EXTRA
    with (DATA / "filtered.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", restval="")
        writer.writeheader()
        for r in signals:
            v = cache.get(r["url"])
            writer.writerow({**r, "filter_verdict": v["verdict"] if v else "pending",
                             "filter_category": v["category"] if v else "",
                             "filter_reason": v["reason"] if v else ""})

    # Agreement with your labels
    report, disagreements = [], []
    for p in gold_paths():
        if "labeled" in p.name.lower():
            report += compare(p.stem, read_csv(p), cache, disagreements)
    if report:
        with (DATA / "filter_report.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["set", "metric", "value"])
            writer.writeheader()
            writer.writerows(report)
        with (DATA / "filter_disagreements.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["set", "name", "url", "description", "my_label",
                                                   "my_reason", "model_verdict", "model_category", "model_reason"])
            writer.writeheader()
            writer.writerows(disagreements)
        for r in report:
            if r["metric"] in ("agree", "agreement_pct"):
                print(f'{r["set"]}: {r["metric"]} = {r["value"]}')
    else:
        print("No labeled file found yet (gold_labeled.csv). Skipping the agreement report.")

    done = [cache[r["url"]] for r in signals if r["url"] in cache]
    print(f"Totals: {sum(v['verdict'] == 'keep' for v in done)} keep, "
          f"{sum(v['verdict'] == 'reject' for v in done)} reject, {len(signals) - len(done)} pending"
          + (" (stopped early on quota)" if stopped_early else ""))
    print("Reject reasons:", dict(Counter(v["category"] for v in done if v["verdict"] == "reject")))


if __name__ == "__main__":
    main()
