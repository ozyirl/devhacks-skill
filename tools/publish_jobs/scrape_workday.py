#!/usr/bin/env python3
"""Walk ASU Find Student Jobs in a signed-in Chrome and write live_jobs.json.

Maintainer-only. Cubbie never runs this. A dedicated Chrome profile lives at
~/.local/share/asu-workday-scrape so it does not fight the user's daily Chrome.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

HUB = "https://www.myworkday.com/asu/d/task/1422$3898.htmld"
PROFILE = Path.home() / ".local/share/asu-workday-scrape"
PAY_ONE = re.compile(r"\$(\d+(?:\.\d+)?)\s*per hour", re.I)
PAY_RANGE = re.compile(r"\$(\d+(?:\.\d+)?)\s*[-–]\s*\$(\d+(?:\.\d+)?)", re.I)
SCALE = re.compile(r"Student Worker\s+(I|II|III|IV|V)\b", re.I)
JR_RE = re.compile(r"\bJR\d{5,}\b")
INST_RE = re.compile(r"selectedItem_([0-9$]+)")
LOGIN_BITS = (
    "weblogin.asu.edu",
    "cas/login",
    "authgwy",
    "duosecurity",
    "login.htmld",
    "just a moment",
    "__cf_chl",
)


def arizona_today() -> str:
    return datetime.now(ZoneInfo("America/Phoenix")).date().isoformat()


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


def field_after(text: str, label: str) -> str:
    pat = re.compile(
        rf"{re.escape(label)}\s*:?\s*\n+(.*?)(?:\n\s*\n|\n[A-Z][A-Za-z /]+:|\Z)",
        re.I | re.S,
    )
    m = pat.search(text)
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1)).strip()


def looks_like_login(url: str, body: str) -> bool:
    blob = f"{url}\n{body}".lower()
    return any(bit in blob for bit in LOGIN_BITS)


def looks_ready(body: str) -> bool:
    return bool(JR_RE.search(body) or "job profile" in body.lower() or "selectedItem_" in body)


def job_from_list_row(extra: str, inst: str = "") -> dict[str, Any] | None:
    extra = re.sub(r"\s+", " ", extra or "").strip()
    jr_m = JR_RE.search(extra)
    if not jr_m:
        return None
    jr = jr_m.group(0)
    campus_m = re.search(r"Campus:\s*([^|]+)", extra, re.I)
    loc_m = re.search(r"Off-Campus:\s*([^|]+)", extra, re.I)
    if campus_m:
        campus = campus_of("Campus: " + campus_m.group(1))
    elif loc_m:
        campus = campus_of("Off-Campus: " + loc_m.group(1))
    else:
        campus = ""
    title = extra.split(jr, 1)[0]
    title = re.sub(r"[\s|]+$", "", title).strip(" |-")
    if not title or title == jr:
        after = extra.split(jr, 1)[-1]
        title = re.split(r"\s*\|\s*", after, maxsplit=1)[0].strip(" |-")
        if title.lower().startswith("campus:"):
            title = jr
    end_m = re.search(r"Posting Date:\s*([0-9/]+)", extra, re.I)
    sm = SCALE.search(extra)
    lo, hi = parse_pay(extra)
    job: dict[str, Any] = {
        "jr": jr,
        "title": (title or jr)[:160],
        "campus": campus,
        "hybrid": "hybrid" in extra.lower(),
        "job_profile": "",
        "worker_scale": sm.group(1).upper() if sm else "",
        "funding": "",
        "posting_end_date": end_m.group(1) if end_m else "",
        "pay_text": "",
        "list_text": extra[:400],
    }
    if inst:
        job["inst"] = inst
    if lo is not None:
        job["pay_min"] = lo
    if hi is not None:
        job["pay_max"] = hi
    return job


def job_from_posting(text: str, url: str = "") -> dict[str, Any] | None:
    jr_m = JR_RE.search(text) or JR_RE.search(url)
    if not jr_m:
        return None
    jr = jr_m.group(0)
    title = field_after(text, "View Job Posting Details")
    if not title:
        for line in text.splitlines():
            line = line.strip()
            if line and line not in ("Apply", "Skip to main content", "Home") and "Worker" not in line:
                if 3 < len(line) < 120 and not line.endswith(":"):
                    title = line
                    break
    title = title.split("\n")[0].strip() if title else jr
    # first non-nav heading is often duplicated; prefer the line after "View Job Posting Details"
    loc = field_after(text, "Location") or field_after(text, "Campus")
    profile = field_after(text, "Job Profile")
    funding = field_after(text, "Funding")
    pay_text = field_after(text, "Pay Rate") or field_after(text, "Pay Range") or ""
    if not pay_text:
        m = PAY_ONE.search(text) or PAY_RANGE.search(text)
        pay_text = m.group(0) if m else ""
    end = field_after(text, "End Date") or field_after(text, "Apply before")
    desc = field_after(text, "Job Description") or field_after(text, "Essential Duties")
    quals = field_after(text, "Desired Qualifications") or field_after(text, "Minimum Qualifications")
    sm = SCALE.search(profile or text)
    lo, hi = parse_pay(pay_text or text)
    loc = campus_of(loc)
    blob = f"{title} {loc}".lower()
    job: dict[str, Any] = {
        "jr": jr,
        "title": title[:160],
        "campus": loc,
        "hybrid": "hybrid" in blob,
        "job_profile": profile,
        "worker_scale": sm.group(1).upper() if sm else "",
        "funding": funding,
        "posting_end_date": end,
        "pay_text": pay_text,
    }
    if lo is not None:
        job["pay_min"] = lo
    if hi is not None:
        job["pay_max"] = hi
    if desc:
        job["description"] = desc[:1200]
    if quals:
        job["qualifications"] = quals[:800]
    return job


def extract_list_items(page) -> list[dict[str, str]]:
    return page.evaluate(
        """() => {
          const seen = new Map();
          const add = (inst, jr, extra) => {
            const key = jr || inst;
            if (!key) return;
            const prev = seen.get(key);
            if (!prev || extra.length > (prev.extra || '').length) {
              seen.set(key, {inst: inst || '', jr: jr || '', title: extra.slice(0, 200), extra});
            }
          };
          const nodes = document.querySelectorAll(
            '[id^="selectedItem_"], [data-automation-id="compositeContainer"], [data-automation-id="compositeSubHeaderOne"]'
          );
          for (const n of nodes) {
            const host = n.closest('[id^="selectedItem_"]') || n;
            const inst = (host.id || '').replace(/^selectedItem_/, '');
            const t = (host.innerText || n.innerText || '').replace(/\\s+/g, ' ').trim();
            const jr = (t.match(/JR\\d{5,}/) || [''])[0];
            add(inst, jr, t);
          }
          return Array.from(seen.values());
        }"""
    )


def scroll_list(page, rounds: int = 40) -> list[dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    last = -1
    stagnant = 0
    for _ in range(rounds):
        for item in extract_list_items(page):
            key = item.get("jr") or item.get("inst") or item.get("title")
            if key:
                found[key] = item
        if len(found) == last:
            stagnant += 1
        else:
            stagnant = 0
        last = len(found)
        if stagnant >= 4:
            break
        page.evaluate(
            """() => {
              const nodes = [
                document.querySelector('[data-automation-id="scrollable"]'),
                document.querySelector('[data-automation-id="itemContainer"]'),
                document.scrollingElement,
              ].filter(Boolean);
              for (const n of nodes) n.scrollBy(0, 900);
              window.scrollBy(0, 900);
            }"""
        )
        page.wait_for_timeout(700)
    return list(found.values())


def open_detail(page, item: dict[str, str]) -> str:
    inst = item.get("inst") or ""
    if inst:
        loc = page.locator(f"#selectedItem_{inst}")
        if loc.count():
            try:
                loc.first.evaluate("el => el.click()")
                page.wait_for_timeout(1800)
                return page.inner_text("body")
            except Exception:
                pass
        try:
            page.goto(
                f"https://www.myworkday.com/asu/d/inst/15$158872/{inst}.htmld",
                wait_until="domcontentloaded",
                timeout=45000,
            )
            page.wait_for_timeout(2000)
            return page.inner_text("body")
        except Exception:
            return ""
    title = (item.get("title") or "").split("JR")[0].strip()
    if title:
        try:
            page.get_by_text(title[:40], exact=False).first.click(timeout=4000)
            page.wait_for_timeout(1800)
            return page.inner_text("body")
        except Exception:
            return ""
    return ""


def back_to_list(page) -> None:
    for sel in (
        '[data-automation-id="backButton"]',
        '[data-automation-id="navigationItem"]',
        'button:has-text("Back")',
    ):
        try:
            loc = page.locator(sel)
            if loc.count():
                loc.first.click(timeout=2000)
                page.wait_for_timeout(1200)
                return
        except Exception:
            continue
    page.goto(HUB, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2000)


def payload(jobs: list[dict[str, Any]], status: str, source: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "as_of": arizona_today(),
        "as_of_time": now,
        "source": source,
        "status": status,
        "count": len(jobs),
        "jobs": jobs,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {data['count']} jobs status={data['status']} as_of={data['as_of']} -> {path}")


def write_preserving(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Keep the last good board if this run only hit login."""
    if data.get("status") == "ok" and data.get("jobs"):
        write_json(path, data)
        return data
    if path.exists():
        try:
            old = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            old = {}
        if old.get("jobs"):
            old["status"] = data.get("status") or "needs_signin"
            write_json(path, old)
            print("kept previous jobs; marked", old["status"])
            return old
    write_json(path, data)
    return data


def scrape(out: Path, wait_login: int, details: bool, max_jobs: int) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    PROFILE.mkdir(parents=True, exist_ok=True)
    xhr_jobs: list[dict[str, Any]] = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            channel="chrome",
            headless=False,
            accept_downloads=False,
            viewport={"width": 1280, "height": 900},
            timeout=90000,
        )
        page = context.pages[0] if context.pages else context.new_page()

        def on_response(resp: Any) -> None:
            try:
                ctype = (resp.headers or {}).get("content-type", "")
                if "json" not in ctype:
                    return
                data = resp.json()
            except Exception:
                return
            blob = json.dumps(data)
            if "JR" not in blob:
                return
            # Keep raw JR hits from XHR as a last-resort index.
            for jr in set(JR_RE.findall(blob)):
                xhr_jobs.append({"jr": jr})

        page.on("response", on_response)
        page.goto(HUB, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        deadline = time.time() + max(0, wait_login)
        while time.time() < deadline:
            body = page.inner_text("body")
            url = page.url
            if looks_ready(body) and not looks_like_login(url, body):
                break
            print("NEEDS_SIGNIN: sign into Workday in the Chrome window that just opened, including Duo.")
            page.wait_for_timeout(4000)
        else:
            body = page.inner_text("body")
            url = page.url
        body = page.inner_text("body")
        url = page.url
        if looks_like_login(url, body) or not looks_ready(body):
            data = payload([], "needs_signin", "find-student-jobs")
            write_preserving(out, data)
            print("Still on login/Duo. Leave Chrome open, sign in, rerun this command.")
            context.close()
            return data

        items = scroll_list(page)
        print(f"list rows: {len(items)}")
        jobs: list[dict[str, Any]] = []
        seen = set()

        if details:
            for item in items[: max(1, max_jobs)]:
                text = open_detail(page, item)
                job = job_from_posting(text or item.get("extra") or item.get("title") or "", page.url)
                if job and job["jr"] not in seen:
                    seen.add(job["jr"])
                    jobs.append(job)
                    print(f"  {job['jr']} {job['title'][:50]}")
                back_to_list(page)
        else:
            for item in items:
                extra = item.get("extra") or item.get("title") or ""
                job = job_from_list_row(extra, item.get("inst") or "") or job_from_posting(extra)
                if job and job.get("jr") and job["jr"] not in seen:
                    seen.add(job["jr"])
                    jobs.append(job)

        if not jobs and xhr_jobs:
            for row in xhr_jobs:
                if row["jr"] not in seen:
                    seen.add(row["jr"])
                    jobs.append(row)

        data = payload(jobs, "ok" if jobs else "empty", "find-student-jobs")
        write_preserving(out, data)
        context.close()
        return data


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    default_out = root / "asu-on-campus-jobs" / "assets" / "live_jobs.json"
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(default_out))
    p.add_argument("--wait-login", type=int, default=300, help="seconds to wait on Duo/login")
    p.add_argument("--list-only", action="store_true")
    p.add_argument("--max-jobs", type=int, default=200)
    args = p.parse_args()
    data = scrape(Path(args.out), args.wait_login, details=not args.list_only, max_jobs=args.max_jobs)
    if data["status"] != "ok":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
