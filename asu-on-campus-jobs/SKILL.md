---
name: asu-on-campus-jobs
description: Finds ASU on-campus student hourly jobs from a live Workday snapshot using the student's filters and resume, then drafts applications after they pick jobs. Use when they ask for on-campus jobs, student employment, Workday, Find Student Jobs, desk or grader or tech roles, or a campus job that pays a given hourly rate.
---

# ASU on-campus jobs

Help an ASU student match [Find Student Jobs](https://www.myworkday.com/asu/d/task/1422$3898.htmld) and draft an application from their resume.

Cubbie does not open Workday and does not save ASURITE. Cloudflare on `weblogin.asu.edu` blocks Cubbie's cloud browser. Listings come from a public JSON feed that a signed-in laptop refreshes, then Cubbie downloads on every search. The student Submits in their own Workday.

## When to use

- "Find me desk jobs over $15 on downtown campus."
- "Tempe tech jobs $16–17 skip FWS."
- "I like 7, 13, and 19, I wanna apply."
- "Apply to ASU student jobs with my resume."

Do not use it for Canvas, Handshake, LinkedIn, or staff careers on asu.wd1.myworkdayjobs.com.

## Abilities

Files (resume and cover letter the student sends), memory (filters, the numbered shortlist, JR numbers already applied), documents (cover letter drafts, extra-match PDF), reminders (optional check-in when they want one). Web, to download the jobs feed.

Do not use the browser for Workday. Do not send Take control or a credentials card. Do not run anything under `tools/`.

## Steps

1. **Collect filters** if they are missing. One question at a time. They can skip a filter. Map campus nicknames: downtown → Downtown, poly → Polytechnic, west → West Valley. "Over $15" means pay-min 15 and no pay-max cap.

2. **Resume.** If they already sent a PDF in this chat or memory, keep it. If not, wait until they pick jobs, then ask: `please send me your resume so I can tailor the answers for you`

3. **Match the live feed.** From this Skill folder (the script downloads the public GitHub file itself):

   ```bash
   python3 scripts/match_jobs.py --keywords "<keywords>" --campus "<campus>"
   ```

   Add `--pay-min <n>` and `--pay-max <n>` only if they named a pay band. Add `--skip-fws` when they asked to skip Federal Work-Study or said they are international / F-1. Add `--limit 40` when they want a long list. If the live URL fails, the script falls back to `assets/live_jobs.json` and prints that. `--sample` is only for a dry run.

4. **Shortlist.** Lead with the `as of` date and how many jobs are in the feed. Keep the script's numbering (1. 2. 3.) so "job 7" means that row. Text at most ten matches. If there are more, also send a one-page PDF of the rest with the same numbers. Remember the numbered list. If the feed status is not ok, still list jobs and say the snapshot is waiting on a refresh. If none matched, one line, then offer to loosen pay, campus, or keywords.

5. **They pick jobs.** "I like 7, 13, 19" or "apply to those" is yes for those numbers only. Map numbers to JR ids from the remembered list. Never apply to the whole list.

6. **Draft each picked job** only after that yes. If there is still no resume, ask for it and wait. For each JR:
   - Draft a short cover letter and likely application answers from the resume plus that job's title, pay, campus, funding, and summary.
   - Show the drafts. Wait if they want edits.
   - Then text numbered steps for **their** Workday (already signed in on their phone or laptop):
     1. Open Find Student Jobs.
     2. Type the JR in Workday's own search box (not a raw `inst/15$158872` URL).
     3. Skip the first Quick Apply resume-parse box.
     4. Attach their resume PDF on Resume/CV.
     5. Paste the approved cover letter if Workday asks for one.
     6. They tap Submit.
   Remember a JR as applied only after they say they submitted. Cubbie does not click Submit.

7. **Check-in.** After the first successful search, offer a text when they want to look again. Create it only after they pick a time.

## Replies

Short, plain text, no Markdown. Lead with the `as of` date and the number of matches. Numbered jobs, one apply question at a time unless they already named several numbers. Links on their own line.

## When something fails

- Cubbie's browser is on CAS, Cloudflare, `__cf_chl`, or "Just a moment": do not Take control. Match the feed instead.
- `match_jobs.py` exit 2: say the job list could not be downloaded. Do not guess jobs.
- Nothing matches: one line, then offer a wider pay band, another campus, or fewer keywords.
- They want Cubbie to Submit in the cloud browser: say Workday has to stay in their login, and send the JR steps.

Outside Cubbie, run the same `match_jobs.py` command. Use `--sample` only when checking the script without the feed.
