# ASU Workday — Find Student Jobs

Student hourly listing (student's own browser, already signed in):

https://www.myworkday.com/asu/d/task/1422$3898.htmld

Cubbie never opens this URL. Cloudflare on `weblogin.asu.edu` blocks Cubbie's cloud browser (`__cf_chl`, "Just a moment...").

## Live feed Cubbie downloads

https://raw.githubusercontent.com/ozyirl/devhacks-skill/on-campus-jobs-skill/asu-on-campus-jobs/assets/live_jobs.json

`scripts/match_jobs.py` fetches that URL on every search. The copy in `assets/live_jobs.json` is only a fallback if GitHub is unreachable.

## Refresh the feed (laptop, not Cubbie)

From the repo root, on a Mac whose Chrome can open Find Student Jobs:

```bash
python3 tools/publish_jobs/publish.py --wait-login --push
```

That opens a dedicated Chrome profile, waits if Duo/login is showing, walks the board, writes `asu-on-campus-jobs/assets/live_jobs.json`, and pushes. Random Skill installers never run this. They only `curl` the raw URL.

CSV from an older scrape can still be converted:

```bash
python3 scripts/dump_jobs.py --from-csv /path/to/all-student-jobs.csv --as-of YYYY-MM-DD
```

Do not put manager names, resumes, or Workday form answers in the JSON.

## Search (student's Workday)

Type a JR number in Workday's own search on Find Student Jobs. Browser-page find can miss titles. Direct `inst/15$158872/...` URLs often hang; close that tab, search the JR instead.

## Pay

Prefer `pay_min` / `pay_max` on the index. If only a worker scale is present:

- Worker I: about $14.70–$15.40
- Worker II: about $15.10–$16.57
- Worker III: about $15.97–$18.97
- Worker IV: about $17.75 and up
- Worker V: about $20 and up

$16–17 usually fits Worker III.

## Funding / F-1

"Federal Work Study" / "70/30% ASU" / "America Reads" is FWS. "No Federal Funding" is the usual hourly job. Skip FWS when the student asked.

## Campuses

Workday labels: Tempe, Downtown Phoenix, West, Polytechnic, plus off-campus rows. "Downtown" in chat means Downtown Phoenix.

## Apply (student's Workday)

Skip the first Quick Apply parse box. Attach the resume PDF on Resume/CV. Cover letter for software/IT/grader-style roles after they approve the draft. Cap during fall/spring is typically 20 hours/week; mention it only if they ask.
