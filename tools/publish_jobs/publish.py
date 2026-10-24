#!/usr/bin/env python3
"""Scrape Find Student Jobs on this Mac, write live_jobs.json, optionally git push.

Cubbie never runs this. Random Skill installers only download the pushed JSON.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRAPE = Path(__file__).resolve().parent / "scrape_workday.py"
VENVS = [
    Path("/Users/mac/allfiles/ASU/Canvas agent/.venv/bin/python"),
    Path.home() / ".local/share/venvs/asu-workday-scrape/bin/python",
]


def python_with_playwright() -> str:
    for candidate in [Path(sys.executable), *VENVS]:
        if not candidate.is_file():
            continue
        ok = subprocess.run(
            [str(candidate), "-c", "from playwright.sync_api import sync_playwright"],
            capture_output=True,
        )
        if ok.returncode == 0:
            return str(candidate)
    sys.exit(
        "Playwright is missing. Use the Canvas-agent venv or: "
        "python3 -m pip install playwright && python3 -m playwright install chrome"
    )


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, text=True, capture_output=True)


def push_json() -> None:
    git("add", "asu-on-campus-jobs/assets/live_jobs.json")
    status = git("status", "--porcelain", "--", "asu-on-campus-jobs/assets/live_jobs.json").stdout.strip()
    if not status:
        print("live_jobs.json unchanged, nothing to push")
        return
    git("commit", "-m", "Refresh ASU student-job feed from signed-in Workday scrape.")
    git("push", "origin", "HEAD")
    print("pushed live_jobs.json")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--wait-login", type=int, default=300)
    p.add_argument("--list-only", action="store_true")
    p.add_argument("--max-jobs", type=int, default=200)
    p.add_argument("--push", action="store_true")
    p.add_argument("--skip-scrape", action="store_true")
    args = p.parse_args()

    if not args.skip_scrape:
        py = python_with_playwright()
        cmd = [
            py,
            str(SCRAPE),
            "--wait-login",
            str(args.wait_login),
            "--max-jobs",
            str(args.max_jobs),
        ]
        if args.list_only:
            cmd.append("--list-only")
        print("running", " ".join(cmd))
        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            print("scrape did not finish a full board; JSON may be needs_signin or empty")
            if args.push:
                # Still push status so Cubbie can say the feed is waiting.
                try:
                    push_json()
                except subprocess.CalledProcessError as exc:
                    print(exc.stderr or exc.stdout)
            raise SystemExit(proc.returncode)
    if args.push:
        try:
            push_json()
        except subprocess.CalledProcessError as exc:
            print(exc.stderr or exc.stdout)
            raise SystemExit(1)


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
