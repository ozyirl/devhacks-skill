#!/usr/bin/env python3
"""Track a student's scholarships: deadlines, amounts, status, and calendar reminders.

Stdlib only. Cubbie reads scholarships from ASU's Scholarship Universe (or a public site) and records them here,
so deadlines and totals stay exact across conversations.

    python3 scripts/tracker.py add --name "Fulton Merit Award" --amount 2000 --deadline 2026-12-01 \
        --source asu --url "https://..." --prompt "Describe a challenge you overcame (500 words)"
    python3 scripts/tracker.py update --id fulton-merit-award --status submitted
    python3 scripts/tracker.py list --today 2026-10-24 [--due-within 14]
    python3 scripts/tracker.py ics --id fulton-merit-award --out /workspace/your_files/scholarships
    python3 scripts/tracker.py list --sample --today 2026-10-24

Statuses: found, drafting, submitted, won, lost, skipped.
Saved state: ~/.config/asu-scholarship-sweep/tracker.json. --sample uses assets/sample_scholarships.json and
saves nothing. Exit codes: 0 ok, 2 bad arguments or unknown id.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

STATE = Path.home() / ".config" / "asu-scholarship-sweep" / "tracker.json"
SAMPLE = Path(__file__).resolve().parent.parent / "assets" / "sample_scholarships.json"
STATUSES = ("found", "drafting", "submitted", "won", "lost", "skipped")
OPEN = ("found", "drafting")


def die(code: int, message: str):
    print(message, file=sys.stderr)
    raise SystemExit(code)


def day(text: str, what: str) -> date:
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        die(2, f"{what} must be YYYY-MM-DD, got {text!r}.")


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:48] or "scholarship"


def load(sample: bool) -> dict:
    path = SAMPLE if sample else STATE
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(data: dict):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=1))


def cmd_add(args):
    day(args.deadline, "--deadline")
    if args.amount is not None and args.amount < 0:
        die(2, "--amount can't be negative.")
    data = load(False)
    key = slug(args.name)
    if key in data and not args.replace:
        die(2, f"{key} is already tracked. Use update, or add --replace.")
    data[key] = {
        "name": args.name, "amount": args.amount, "deadline": args.deadline, "source": args.source,
        "url": args.url or "", "prompt": args.prompt or "", "requirements": args.requirements or "",
        "status": "found",
    }
    save(data)
    print(json.dumps({"id": key, **data[key]}, indent=2))


def cmd_update(args):
    data = load(False)
    if args.id not in data:
        die(2, f"No scholarship with id {args.id}. Run list to see ids.")
    item = data[args.id]
    if args.status:
        item["status"] = args.status
    if args.deadline:
        day(args.deadline, "--deadline")
        item["deadline"] = args.deadline
    if args.amount is not None:
        item["amount"] = args.amount
    if args.note:
        item["note"] = args.note
    save(data)
    print(json.dumps({"id": args.id, **item}, indent=2))


def cmd_list(args):
    today = day(args.today, "--today")
    data = load(args.sample)
    rows = []
    for key, item in data.items():
        left = (day(item["deadline"], f"deadline of {key}") - today).days
        if args.due_within is not None and (item["status"] not in OPEN or left > args.due_within):
            continue
        rows.append({"id": key, **item, "days_left": left,
                     "overdue": left < 0 and item["status"] in OPEN})
    rows.sort(key=lambda r: (r["status"] not in OPEN, r["deadline"]))

    def total(statuses):
        return sum(r.get("amount") or 0 for r in rows if r["status"] in statuses)

    print(json.dumps({
        "today": args.today,
        "open": sum(1 for r in rows if r["status"] in OPEN),
        "totals": {"open": total(OPEN), "submitted": total(("submitted",)), "won": total(("won",))},
        "scholarships": rows,
    }, indent=2))


def cmd_ics(args):
    data = load(args.sample)
    keys = list(data) if args.all else [args.id]
    for key in keys:
        if key not in data:
            die(2, f"No scholarship with id {key}. Run list to see ids.")
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    written = []
    for key in keys:
        item = data[key]
        if item["status"] not in OPEN:
            continue
        deadline = day(item["deadline"], f"deadline of {key}")
        amount = f" (${item['amount']:,})" if item.get("amount") else ""
        lines = [
            "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//asu-scholarship-sweep//EN", "BEGIN:VEVENT",
            f"UID:{key}@asu-scholarship-sweep", f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{deadline.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(deadline + timedelta(days=1)).strftime('%Y%m%d')}",
            fold(f"SUMMARY:Scholarship due: {escape(item['name'])}{escape(amount)}"),
            fold(f"DESCRIPTION:{escape(item.get('url') or 'Apply in ASU Scholarship Universe')}"),
            "BEGIN:VALARM", "TRIGGER:-P3D", "ACTION:DISPLAY", "DESCRIPTION:Scholarship due in 3 days", "END:VALARM",
            "END:VEVENT", "END:VCALENDAR",
        ]
        path = args.out / f"{key}.ics"
        path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
        written.append(str(path))
    print(json.dumps({"files": written}, indent=2))


def escape(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line: str) -> str:
    """Calendar files wrap lines longer than 75 bytes, continuing with a space."""
    parts, current = [], ""
    for char in line:
        if len((current + char).encode()) > (75 if not parts else 74):
            parts.append(current)
            current = ""
        current += char
    return "\r\n ".join(parts + [current])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="track a new scholarship")
    add.add_argument("--name", required=True)
    add.add_argument("--amount", type=int, help="dollars, if listed")
    add.add_argument("--deadline", required=True, help="YYYY-MM-DD")
    add.add_argument("--source", choices=("asu", "outside"), default="asu")
    add.add_argument("--url")
    add.add_argument("--prompt", help="the essay question, if any")
    add.add_argument("--requirements", help="GPA, major, year or other requirements, in a few words")
    add.add_argument("--replace", action="store_true")
    add.set_defaults(run=cmd_add)

    update = sub.add_parser("update", help="change status, deadline, amount or add a note")
    update.add_argument("--id", required=True)
    update.add_argument("--status", choices=STATUSES)
    update.add_argument("--deadline")
    update.add_argument("--amount", type=int)
    update.add_argument("--note")
    update.set_defaults(run=cmd_update)

    listing = sub.add_parser("list", help="all scholarships, soonest deadline first, with totals")
    listing.add_argument("--today", required=True, help="student's local date, YYYY-MM-DD")
    listing.add_argument("--due-within", type=int, help="only open ones due within this many days")
    listing.add_argument("--sample", action="store_true")
    listing.set_defaults(run=cmd_list)

    ics = sub.add_parser("ics", help="calendar reminders for open scholarships")
    ics.add_argument("--id")
    ics.add_argument("--all", action="store_true")
    ics.add_argument("--out", type=Path, required=True)
    ics.add_argument("--sample", action="store_true")
    ics.set_defaults(run=cmd_ics)

    args = parser.parse_args()
    if args.command == "ics" and bool(args.id) == bool(args.all):
        die(2, "Give either --id <id> or --all.")
    args.run(args)


if __name__ == "__main__":
    main()
