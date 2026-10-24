# devhacks-skill

Cubbie Hackathon Track 1: ASU on-campus student hourly jobs.

Cubbie does not log into Workday. On every search it downloads:

https://raw.githubusercontent.com/ozyirl/devhacks-skill/on-campus-jobs-skill/asu-on-campus-jobs/assets/live_jobs.json

Then it matches filters, numbers the list, and drafts from the student's resume. The student Submits in their own Workday.

Install: text Cubbie this folder, then reply yes.

https://github.com/ozyirl/devhacks-skill/tree/on-campus-jobs-skill/asu-on-campus-jobs

## Refresh the feed (this Mac only)

Chrome must be able to open Find Student Jobs (ASURITE + Duo). Random people who install the Skill do not run this.

```bash
python3 tools/publish_jobs/publish.py --wait-login 300 --push
```

A dedicated Chrome window opens (`~/.local/share/asu-workday-scrape`). If Duo appears, sign in there; the script waits, then overwrites `asu-on-campus-jobs/assets/live_jobs.json` and pushes.
