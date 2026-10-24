#!/usr/bin/env python3
"""Rank ASU student-hourly jobs from a live JSON feed.

Stdlib only. Cubbie runs this after fetching the public feed (or this
script fetches the URL itself). Prints a numbered plain-text shortlist.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_FEED = (
    "https://raw.githubusercontent.com/ozyirl/devhacks-skill/"
    "on-campus-jobs-skill/asu-on-campus-jobs/assets/live_jobs.json"
)

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

CAMPUS_HINTS = {
    "downtown": ("downtown",),
    "dtphx": ("downtown",),
    "phoenix downtown": ("downtown",),
    "tempe": ("tempe",),
    "poly": ("polytechnic",),
    "polytechnic": ("polytechnic",),
    "west": ("west",),
    "west valley": ("west",),
}


def die(code: int, msg: str) -> None:
    print(msg)
    raise SystemExit(code)


def read_json(raw: str) -> tuple[list[dict], str, str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        die(2, f"jobs file was not JSON: {exc}")
    as_of = ""
    status = "ok"
    if isinstance(data, dict):
        as_of = str(data.get("as_of") or "")
        status = str(data.get("status") or "ok")
        jobs = data.get("jobs", data)
    else:
        jobs = data
    if not isinstance(jobs, list) or not jobs:
        die(2, "jobs file was empty")
    return jobs, as_of, status


def load_jobs(src: str | None, sample_path: Path, bundled: Path) -> tuple[list[dict], str, str, str]:
    if src == "sample":
        return (*read_json(sample_path.read_text()), "sample")
    candidates: list[str] = []
    if src:
        candidates.append(src)
    else:
        candidates.append(DEFAULT_FEED)
        candidates.append(str(bundled))
    last_err = "could not read jobs"
    for item in candidates:
        try:
            if item.startswith("http://") or item.startswith("https://"):
                req = urllib.request.Request(
                    item,
                    headers={"User-Agent": "asu-on-campus-jobs/1"},
                )
                ctx = ssl.create_default_context()
                with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
                    raw = resp.read().decode("utf-8", "replace")
                jobs, as_of, status = read_json(raw)
                return jobs, as_of, status, item
            path = Path(item)
            jobs, as_of, status = read_json(path.read_text())
            return jobs, as_of, status, str(path)
        except (OSError, urllib.error.URLError, TimeoutError, ssl.SSLError) as exc:
            last_err = f"{item}: {exc}"
            continue
    die(2, f"could not read jobs file: {last_err}")
    raise AssertionError


def pay_window(job: dict) -> tuple[float | None, float | None]:
    if job.get("pay_min") is not None or job.get("pay_max") is not None:
        lo = job.get("pay_min")
        hi = job.get("pay_max")
        return (
            float(lo) if lo is not None else None,
            float(hi) if hi is not None else None,
        )
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


def blob_of(job: dict) -> str:
    return " ".join(
        str(job.get(k) or "")
        for k in (
            "title",
            "job_profile",
            "keywords",
            "department",
            "description",
            "qualifications",
            "summary",
            "campus",
            "funding",
        )
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


def campus_ok(job: dict, campus: str) -> bool:
    if not campus:
        return True
    loc = str(job.get("campus") or "").lower()
    if not loc:
        return True
    key = campus.lower().strip()
    needles = CAMPUS_HINTS.get(key, (key,))
    return any(n in loc for n in needles)


def score(job: dict, keywords: list[str], campus: str) -> int:
    blob = blob_of(job)
    n = 0
    if keywords and keyword_hit(blob, keywords):
        n += 3
    if any(t.strip() in blob for t in TECH):
        n += 2
    if campus and campus_ok(job, campus):
        n += 2
    if job.get("hybrid"):
        n += 1
    return n


def is_fws(job: dict) -> bool:
    funding = str(job.get("funding") or "").lower()
    return (
        "work study" in funding
        or "work-study" in funding
        or "fws" in funding
        or "70/30" in funding
    )


def pay_label(lo: float | None, hi: float | None) -> str:
    if lo is not None and hi is not None:
        if lo == hi:
            return f"${lo:g}/hr"
        return f"${lo:g}–${hi:g}/hr"
    return "pay not listed"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jobs", help="path or https URL; default is the public GitHub feed")
    p.add_argument("--sample", action="store_true")
    p.add_argument("--keywords", default="")
    p.add_argument("--pay-min", type=float, default=0.0)
    p.add_argument("--pay-max", type=float, default=999.0)
    p.add_argument("--campus", default="")
    p.add_argument("--skip-fws", action="store_true")
    p.add_argument("--limit", type=int, default=15)
    args = p.parse_args()

    root = Path(__file__).resolve().parent.parent
    src = "sample" if args.sample else args.jobs
    jobs, as_of, status, origin = load_jobs(
        src, root / "assets" / "sample_jobs.json", root / "assets" / "live_jobs.json"
    )

    if as_of:
        print(f"as of {as_of}")
    print(f"{len(jobs)} jobs in feed")
    if status and status not in ("ok", ""):
        print(f"feed status: {status}")
    if origin == str(root / "assets" / "live_jobs.json") and not (args.jobs or args.sample):
        print("live feed unreachable, using bundled copy")

    keywords = [k.strip() for k in re.split(r"[|,/]+", args.keywords) if k.strip()]

    kept = []
    for job in jobs:
        if not campus_ok(job, args.campus):
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
    top = kept[: max(1, args.limit)] if kept else []
    if not kept:
        print("0 matches")
        raise SystemExit(0)

    print(f"{len(kept)} matches, showing {len(top)}")
    for i, (s, job, lo, hi) in enumerate(top, start=1):
        jr = job.get("jr") or job.get("id") or "?"
        title = job.get("title") or "Untitled"
        campus = job.get("campus") or "campus n/a"
        fund = "FWS" if is_fws(job) else "hourly"
        print(f"{i}. {title} {jr} | {campus} | {pay_label(lo, hi)} | {fund}")


if __name__ == "__main__":
    main()
