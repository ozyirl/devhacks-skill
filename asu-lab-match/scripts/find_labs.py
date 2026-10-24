#!/usr/bin/env python3
"""Find ASU faculty whose research matches a student's interests, and track who the student has emailed.

Stdlib only. Searches ASU's public faculty directory (search.asu.edu), the same data as the ASU Search site.
The directory's search also matches people's names, so every result is re-scored on its research interests,
expertise areas, titles, department and bio; name-only matches are dropped.

    python3 scripts/find_labs.py search --interests "machine learning, healthcare" --skills "python, pandas"
    python3 scripts/find_labs.py search --interests "robotics" --campus tempe --limit 5
    python3 scripts/find_labs.py search --sample --interests "machine learning"
    python3 scripts/find_labs.py contacted --add jdoe --name "Jane Doe" --today 2026-10-24
    python3 scripts/find_labs.py contacted --replied jdoe
    python3 scripts/find_labs.py followups --today 2026-11-05

Saved state: ~/.config/asu-lab-match/contacted.json. Searches skip anyone already contacted.
Exit codes: 0 ok (also when nothing matches), 2 bad arguments, 5 the directory could not be reached.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

API = "https://search.asu.edu/api/v1/webdir-profiles/faculty-staff/filtered"
PROFILE = "https://search.asu.edu/profile/{eid}"
SAMPLE = Path(__file__).resolve().parent.parent / "assets" / "sample_faculty.json"
STATE = Path.home() / ".config" / "asu-lab-match" / "contacted.json"
FOLLOW_UP_DAYS = 10
PER_TERM = 50

# Where a match counts more: what they say they research beats a passing word in a bio.
WEIGHTS = {"expertise": 3.0, "research": 3.0, "title": 1.0, "department": 1.0, "bio": 1.0}
STOP = {"and", "or", "the", "of", "in", "for", "to", "a", "an", "with", "on", "my", "i", "im", "into"}
RESEARCH_TITLES = ("professor", "research scientist", "scientist", "researcher")


def die(code: int, message: str):
    print(message, file=sys.stderr)
    raise SystemExit(code)


def raw(profile: dict, key: str):
    value = profile.get(key)
    return value.get("raw") if isinstance(value, dict) else value


def as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def plain(text) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(text or "")))
    return re.sub(r"\s+", " ", text).strip()


def fetch(term: str) -> list[dict]:
    query = urllib.parse.urlencode({"query": term, "size": PER_TERM})
    request = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": "asu-lab-match (Cubbie Skill)"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response).get("results") or []
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        die(5, f"Couldn't reach ASU's faculty directory ({e}). Try again in a few minutes.")


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9+#]+", text.lower()) if w not in STOP and len(w) > 1]


def summarize(profile: dict) -> dict:
    titles = [str(t) for t in as_list(raw(profile, "primary_title")) + as_list(raw(profile, "titles")) if t]
    return {
        "asurite": raw(profile, "asurite_id") or (profile.get("_meta") or {}).get("id"),
        "name": raw(profile, "display_name"),
        "title": titles[0] if titles else "",
        "titles": sorted(set(titles)),
        "department": raw(profile, "primary_department") or "",
        "departments": as_list(raw(profile, "departments")),
        "campus": ", ".join(str(c).title() for c in as_list(raw(profile, "primary_job_campus"))),
        "email": raw(profile, "email_address") or "",
        "profile_url": PROFILE.format(eid=raw(profile, "eid")) if raw(profile, "eid") else "",
        "website": raw(profile, "research_website") or raw(profile, "website") or "",
        "cv_url": raw(profile, "cv_url") or "",
        "expertise": [str(e) for e in as_list(raw(profile, "expertise_areas"))],
        "research": plain(raw(profile, "research_interests")),
        "bio": plain(raw(profile, "short_bio") or raw(profile, "bio")),
        "classes": as_list(raw(profile, "simplified_empl_classes")),
    }


def does_research(person: dict) -> bool:
    titles = " ".join(person["titles"]).lower()
    return "Faculty" in person["classes"] and any(t in titles for t in RESEARCH_TITLES)


def score(person: dict, phrases: list[str], skills: list[str]) -> tuple[float, list[str]]:
    fields = {
        "expertise": " ".join(person["expertise"]).lower(),
        "research": person["research"].lower(),
        "title": " ".join(person["titles"]).lower(),
        "department": " ".join(person["departments"]).lower(),
        "bio": person["bio"].lower(),
    }
    total, matched = 0.0, []
    for phrase in phrases:
        best = 0.0
        for field, text in fields.items():
            if phrase in text:
                best = max(best, WEIGHTS[field] * 2)  # the whole phrase, not just its words
                continue
            parts = words(phrase)
            if parts:
                # Every word must appear, just not side by side ("learning ... machine").
                if all(re.search(rf"\b{re.escape(w)}", text) for w in parts):
                    best = max(best, WEIGHTS[field])
        if best:
            total += best
            matched.append(phrase)
    if total:
        blob = " ".join(fields.values())
        hits = [s for s in skills if re.search(rf"\b{re.escape(s)}\b", blob)]
        total += 0.5 * len(hits)
        matched += [f"skill: {s}" for s in hits]
    return round(total, 2), matched


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(state: dict):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))


def split(text: str | None) -> list[str]:
    return [p.strip().lower() for p in re.split(r"[,;\n]", text or "") if p.strip()]


def cmd_search(args):
    phrases = split(args.interests)
    if not phrases:
        die(2, "Give at least one interest, like --interests \"machine learning, healthcare\".")
    skills = split(args.skills)

    if args.sample:
        profiles = json.loads(SAMPLE.read_text(encoding="utf-8"))
        contacted = {}
    else:
        profiles = [p for phrase in phrases for p in fetch(phrase)]
        contacted = load_state()

    people = {}
    for profile in profiles:
        person = summarize(profile)
        if person["asurite"] and person["asurite"] not in people:
            people[person["asurite"]] = person

    results = []
    for person in people.values():
        if person["asurite"] in contacted:
            continue
        if not args.include_staff and not does_research(person):
            continue
        if args.campus and args.campus.lower() not in person["campus"].lower():
            continue
        points, matched = score(person, phrases, skills)
        if points:
            results.append({**person, "score": points, "matched": matched})
    results.sort(key=lambda p: -p["score"])

    for person in results:
        person["research"] = person["research"][:400]
        person["bio"] = person["bio"][:300]
        del person["classes"], person["titles"]
    print(json.dumps({"interests": phrases, "matched": len(results), "results": results[:args.limit]}, indent=2))


def cmd_contacted(args):
    state = load_state()
    if args.add:
        if not args.today:
            die(2, "Add --today YYYY-MM-DD (the student's local date) when marking someone contacted.")
        due = date.fromisoformat(args.today) + timedelta(days=FOLLOW_UP_DAYS)
        state[args.add] = {"name": args.name or args.add, "emailed": args.today, "follow_up": due.isoformat(),
                           "replied": False}
    if args.replied:
        if args.replied not in state:
            die(2, f"{args.replied} isn't in the contacted list.")
        state[args.replied]["replied"] = True
    if args.add or args.replied:
        save_state(state)
    print(json.dumps(state, indent=2))


def cmd_followups(args):
    today = date.fromisoformat(args.today)
    due = [{"asurite": k, **v} for k, v in load_state().items()
           if not v.get("replied") and date.fromisoformat(v["follow_up"]) <= today]
    print(json.dumps({"due": due}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="find faculty whose research matches")
    search.add_argument("--interests", required=True, help="comma-separated research interests")
    search.add_argument("--skills", help="comma-separated skills from the resume, for a small boost")
    search.add_argument("--campus", help="tempe, downtown, polytechnic, west...")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--include-staff", action="store_true", help="also staff and graduate students")
    search.add_argument("--sample", action="store_true", help="use the bundled sample; no network, no saved state")
    search.set_defaults(run=cmd_search)

    contacted = sub.add_parser("contacted", help="show, add or update who the student emailed")
    contacted.add_argument("--add", metavar="ASURITE")
    contacted.add_argument("--name")
    contacted.add_argument("--today", help="student's local date, YYYY-MM-DD")
    contacted.add_argument("--replied", metavar="ASURITE")
    contacted.set_defaults(run=cmd_contacted)

    followups = sub.add_parser("followups", help="emails with no reply after 10 days")
    followups.add_argument("--today", required=True, help="student's local date, YYYY-MM-DD")
    followups.set_defaults(run=cmd_followups)

    args = parser.parse_args()
    if getattr(args, "limit", 1) < 1:
        die(2, "--limit must be at least 1")
    try:
        args.run(args)
    except ValueError as e:
        die(2, f"Bad date: {e}. Use YYYY-MM-DD.")


if __name__ == "__main__":
    main()
