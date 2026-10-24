---
name: asu-on-campus-jobs
description: Finds ASU on-campus Workday student jobs from the student's filters and resume, then applies only after they say yes. Use when they ask for on-campus jobs, student employment, Workday, myworkday.com/asu, a campus job that pays a given hourly rate, a tech or grader or aide role, or to apply to Find Student Jobs.
---

# ASU on-campus jobs

Help an ASU student search [Find Student Jobs](https://www.myworkday.com/asu/d/task/1422$3898.htmld) and apply with their resume. This Skill is for ASU Workday student hourly jobs. It does not apply to Handshake, LinkedIn, or off-campus internships.

Cubbie already knows how to open a campus site and read a resume. This Skill adds the Workday path, the pay/title filter, and the apply gate.

## When to use

- "Find me an on-campus tech job that pays $16–17."
- "Apply to ASU student jobs with my resume."
- "What's open on Workday for Tempe graders?"
- The student sends a resume and talks about campus jobs, Workday, or student employment.

Do not use it for Canvas assignments, off-campus internships, or paying anything.

## Abilities

Browser (Workday), files (resume and cover letter the student sends), memory (filters and which JR numbers already applied), documents (shortlist PDF if more than five matches), reminders (optional weekly new-post check-in).

## Steps

1. **Collect filters** if they are missing. Ask one question at a time. Defaults the student can accept with "yes":
   - Keywords / role type (example: tech, grader, software, IT)
   - Hourly pay band (example: $16–17)
   - Campus (Tempe unless they name another)
   - Skip Federal Work-Study postings? Default yes if they say they are international or F-1; otherwise ask.
   Remember these with Cubbie's memory after they confirm.

2. **Resume.** Use the resume file the student just sent. If none is in this chat, ask them to send the PDF. Keep it for this search. Skip Workday's first Quick Apply parse box later; attach this file on the Resume/CV step.

3. **Get the job list.** ASU Workday sits behind Cloudflare on `weblogin.asu.edu`. Cubbie's cloud browser is almost always bounced (`__cf_chl`, "Just a moment...", CAS with no login form). Do not loop Take control.

   **Default (student's own Chrome):** they are already signed in there. Text them to open
   https://www.myworkday.com/asu/d/task/1422$3898.htmld
   filter **Student Employee** and their campus, then send screenshots and/or a copy-paste of rows (title, JR, campus, posting date). Read those files. Do not ask for a password.

   **Only if Cubbie's browser already shows Find Student Jobs** (job rows, no CAS, no `__cf_chl`): scrape that page. Do not reload.

   If Cubbie's browser URL contains `weblogin.asu.edu`, `__cf_chl`, or "Just a moment": stop. Tell them to Cancel the cloud browser and send screenshots from their Chrome.

4. **Search / capture.** From screenshots, paste, or a live job list, record JR, title, campus, posting date, job profile, funding (FWS vs none), listed pay if any, cover letter required. Read `references/workday-asu.md`. If they only sent the first screen, ask for more screenshots until the visible list is covered or they say that's all.

5. **Match.** From this Skill folder, write the captured jobs to a temp JSON file and run:

   ```bash
   python3 scripts/match_jobs.py --jobs /tmp/workday-jobs.json --keywords "<keywords>" --pay-min <n> --pay-max <n> --campus "<campus>"
   ```

   Add `--skip-fws` when they asked to skip Federal Work-Study. Add `--sample` only when testing this Skill without Workday; that uses `assets/sample_jobs.json` and does not touch student state.

6. **Shortlist.** Text at most three matches (JR, title, campus, pay or worker scale, one-line why it fits). If more than five matched, also send a one-page PDF of the rest. If none matched, say so in one line and offer to loosen pay or keywords. Do not apply yet.

7. **Apply one job.** Ask: `Apply to <title> <JR>?` Wait for yes. Never apply to the whole list in one shot.

   Cubbie does not Submit in the cloud browser (Cloudflare). After yes:
   - Draft the application answers from the resume. If a cover letter is required, draft it and wait for approval.
   - Text numbered steps for **their** Chrome: Find Student Jobs → type the JR in Workday's search box (not a raw `inst/15$158872` URL) → skip the first Quick Apply parse box → attach the resume PDF on Resume/CV → paste the approved cover letter if any → they tap Submit.
   - Remember the JR as applied only after they say they submitted.

   If Cubbie's browser somehow already has that posting open with no CAS, fill the form, then ask `Submit this application?` and click Submit only after that yes.

8. **Weekly check-in.** After the first successful search, offer a weekly text for new matching posts. Create it only after they pick a time.

## Replies

Short, plain text, no Markdown. Lead with the number of matches. Put each Workday link on its own line. One apply question at a time. If the widget fails, send the JR list and what to tap.

## When something fails

- Cloudflare / CAS / `__cf_chl` / "Just a moment" in Cubbie's browser: one line, then ask for screenshots from their Chrome. Do not send another Take control card.
- Find Student Jobs will not load: same screenshot path. Do not guess jobs.
- Search widgets will not click: stop applying. Text up to three JR titles and say they can open Find Student Jobs and search that JR.
- `match_jobs.py` exit 2: the jobs file was empty or unreadable. Capture the list again.
- Nothing matches: one line, then offer a wider pay band or fewer keywords.
- Apply/Submit clicked without a yes: do not recover by submitting. Ask again.

Outside Cubbie, ask the user to open the Workday URL themselves and use the same filter and apply-one-at-a-time rules.
