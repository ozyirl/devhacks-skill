# devhacks-skill

Cubbie Hackathon Track 1: ASU on-campus student hourly jobs.

Cubbie does not log into Workday. It matches `asu-on-campus-jobs/assets/live_jobs.json` and drafts an application. The student Submits in their own Workday.

Install: text Cubbie this folder, then reply yes.

https://github.com/ozyirl/devhacks-skill/tree/on-campus-jobs-skill/asu-on-campus-jobs

Refresh the index after a signed-in Workday scrape:

```bash
python3 asu-on-campus-jobs/scripts/dump_jobs.py \
  --from-csv /path/to/all-student-jobs.csv \
  --as-of 2026-10-13
```
