# ASU Workday — Find Student Jobs

Listing (student's own browser, already signed in):

https://www.myworkday.com/asu/d/task/1422$3898.htmld

Cubbie never opens this URL. Cloudflare on `weblogin.asu.edu` blocks Cubbie's cloud browser (`__cf_chl`, "Just a moment..."). Listings in this Skill come from `assets/live_jobs.json`.

## Refresh the index (laptop, not Cubbie)

A signed-in Workday scrape is saved as CSV (JR, title, location, profile, funding, pay). Convert and commit:

```bash
python3 scripts/dump_jobs.py --from-csv /path/to/all-student-jobs.csv
```

Then push this Skill folder so Cubbie's next install sees a new `as of` date.

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

## Apply (student's Workday)

Skip the first Quick Apply parse box. Attach the resume PDF on Resume/CV. Cover letter for software/IT/grader-style roles after they approve the draft. Cap during fall/spring is typically 20 hours/week; mention it only if they ask.
