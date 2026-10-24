#!/usr/bin/env python3
"""Build assets/live_jobs.json from an OJC/Workday CSV dump.

Prefer tools/publish_jobs/publish.py for a live scrape. This converter
is for an existing CSV. Cubbie downloads the pushed JSON from GitHub.

  python3 scripts/dump_jobs.py --from-csv path/to/all-student-jobs.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path

PAY_ONE = re.compile(r"\$(\d+(?:\.\d+)?)\s*per hour", re.I)
PAY_RANGE = re.compile(r"\$(\d+(?:\.\d+)?)\s*[-–]\s*\$(\d+(?:\.\d+)?)", re.I)
SCALE = re.compile(r"Student Worker\s+(I|II|III|IV|V)\b", re.I)


def parse_pay(text: str) -> tuple[float | None, float | None]:
    text = text or ""
    m = PAY_RANGE.search(text)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = PAY_ONE.search(text)
    if m:
        v = float(m.group(1))
        return v, v
    return None, None


def campus_of(location: str) -> str:
    location = (location or "").strip()
    location = re.sub(r"^Campus:\s*", "", location, flags=re.I)
    return location


def row_to_job(row: dict) -> dict:
    profile = row.get("profile") or ""
    sm = SCALE.search(profile)
    lo, hi = parse_pay(row.get("pay") or "")
    loc = campus_of(row.get("location") or "")
    summary = (row.get("hours_schedule") or row.get("description") or "").strip()
    if len(summary) > 800:
        summary = summary[:797] + "..."
    job = {
        "jr": (row.get("id") or "").strip(),
        "title": (row.get("title") or "").strip(),
        "campus": loc,
        "hybrid": "hybrid" in (row.get("location") or "").lower()
        or "hybrid" in (row.get("title") or "").lower(),
        "job_profile": profile.strip(),
        "worker_scale": sm.group(1).upper() if sm else "",
        "funding": (row.get("funding") or "").strip(),
        "posting_end_date": (row.get("posting_end_date") or "").strip(),
        "pay_text": (row.get("pay") or "").strip(),
    }
    if summary:
        job["summary"] = summary
    if lo is not None:
        job["pay_min"] = lo
    if hi is not None:
        job["pay_max"] = hi
    return job


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--from-csv", required=True)
    p.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "assets" / "live_jobs.json"),
    )
    p.add_argument("--as-of", default=date.today().isoformat())
    args = p.parse_args()
    src = Path(args.from_csv)
    rows = list(csv.DictReader(src.open(newline="", encoding="utf-8")))
    jobs = [row_to_job(r) for r in rows if (r.get("id") or "").strip()]
    payload = {
        "as_of": args.as_of,
        "source": src.name,
        "status": "ok",
        "count": len(jobs),
        "jobs": jobs,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {len(jobs)} jobs to {out} as_of {payload['as_of']}")


if __name__ == "__main__":
    main()
