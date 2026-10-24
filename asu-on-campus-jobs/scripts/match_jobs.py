#!/usr/bin/env python3
"""Rank ASU Workday student jobs against pay, campus, and keyword filters.

Stdlib only. Prints a short plain-text shortlist for Cubbie to text.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCALE_BANDS = {
    "i": (14.7, 15.4),
    "ii": (15.1, 16.57),
    "iii": (15.97, 18.97),
    "iv": (17.75, 30.0),
    "v": (20.0, 50.0),
}

TECH = (
    "software",
    "grader",
    "information systems",
    "cis",
    "scai",
    "technician",
    "computer",
    "programming",
    "developer",
    "systems",
    "it support",
    "help desk",
)


def die(code: int, msg: str) -> None:
    print(msg)
    raise SystemExit(code)


def load_jobs(path: Path) -> tuple[list[dict], str]:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        die(2, f"could not read jobs file: {exc}")
    as_of = ""
    if isinstance(data, dict):
        as_of = str(data.get("as_of") or "")
        jobs = data.get("jobs", data)
    else:
        jobs = data
    if not isinstance(jobs, list) or not jobs:
        die(2, "jobs file was empty")
    return jobs, as_of


def pay_window(job: dict) -> tuple[float | None, float | None]:
    if job.get("pay_min") is not None or job.get("pay_max") is not None:
        lo = job.get("pay_min")
        hi = job.get("pay_max")
        return (float(lo) if lo is not None else None, float(hi) if hi is not None else None)
    scale = str(job.get("worker_scale") or "").strip().lower()
    scale = re.sub(r"[^ivx]", "", scale)
    if scale in SCALE_BANDS:
        return SCALE_BANDS[scale]
    return (None, None)


def overlaps(lo: float | None, hi: float | None, want_min: float, want_max: float) -> bool:
    if lo is None and hi is None:
        return True
    a = lo if lo is not None else hi
    b = hi if hi is not None else lo
    if a is None or b is None:
        return True
    return a <= want_max and b >= want_min


def tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def blob_of(job: dict) -> str:
    return " ".join(
        str(job.get(k) or "")
        for k in ("title", "job_profile", "keywords", "department")
    ).lower()


def keyword_hit(blob: str, keywords: list[str]) -> bool:
    for kw in keywords:
        k = kw.lower().strip()
        if not k:
            continue
        if k in ("tech", "technical", "it", "stem"):
            if any(t.strip() in blob for t in TECH):
                return True
            continue
        if k in blob:
            return True
    return False


def score(job: dict, keywords: list[str], campus: str) -> int:
    blob = blob_of(job)
    n = 0
    if keyword_hit(blob, keywords):
        n += 3
    if any(t.strip() in blob for t in TECH):
        n += 2
    if campus and campus.lower() in str(job.get("campus") or "").lower():
        n += 2
    if job.get("hybrid"):
        n += 1
    return n


def is_fws(job: dict) -> bool:
    funding = str(job.get("funding") or "").lower()
    return "work study" in funding or "work-study" in funding or "fws" in funding or "70/30" in funding


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jobs")
    p.add_argument("--sample", action="store_true")
    p.add_argument("--keywords", default="")
    p.add_argument("--pay-min", type=float, default=16.0)
    p.add_argument("--pay-max", type=float, default=17.0)
    p.add_argument("--campus", default="Tempe")
    p.add_argument("--skip-fws", action="store_true")
    p.add_argument("--limit", type=int, default=5)
    args = p.parse_args()

    root = Path(__file__).resolve().parent.parent
    jobs_path = Path(args.jobs) if args.jobs else None
    if args.sample:
        jobs_path = root / "assets" / "sample_jobs.json"
    if jobs_path is None:
        die(2, "pass --jobs or --sample")

    jobs, as_of = load_jobs(jobs_path)
    if as_of:
        print(f"as of {as_of}")
    keywords = [k.strip() for k in re.split(r"[|,/]+", args.keywords) if k.strip()]
    if not keywords:
        keywords = ["tech", "grader", "software", "information systems"]

    kept = []
    for job in jobs:
        if args.campus and args.campus.lower() not in str(job.get("campus") or "").lower():
            # keep unknown campus rather than dropping unscored rows
            if job.get("campus"):
                continue
        if args.skip_fws and is_fws(job):
            continue
        lo, hi = pay_window(job)
        if not overlaps(lo, hi, args.pay_min, args.pay_max):
            continue
        if keywords and not keyword_hit(blob_of(job), keywords):
            continue
        kept.append((score(job, keywords, args.campus), job, lo, hi))

    kept.sort(key=lambda row: (-row[0], str(row[1].get("title") or "")))
    top = kept[: max(1, args.limit)]
    if not top:
        print("0 matches")
        raise SystemExit(0)

    print(f"{len(kept)} matches, showing {len(top)}")
    for s, job, lo, hi in top:
        jr = job.get("jr") or job.get("id") or "?"
        title = job.get("title") or "Untitled"
        campus = job.get("campus") or "campus n/a"
        if lo is not None and hi is not None:
            pay = f"${lo:g}–${hi:g}/hr"
        else:
            pay = "pay not listed"
        why = "keyword+pay fit" if s >= 5 else "pay/campus fit"
        print(f"- {title} {jr} | {campus} | {pay} | {why}")


if __name__ == "__main__":
    main()
