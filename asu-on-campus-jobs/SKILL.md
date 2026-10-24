---
name: asu-on-campus-jobs
description: Finds ASU on-campus student hourly jobs from a Workday index plus the student's filters and resume, then drafts an application after they say yes. Use when they ask for on-campus jobs, student employment, Workday, a campus job that pays a given hourly rate, a tech or grader or aide role, or Find Student Jobs.
---

# ASU on-campus jobs

Help an ASU student match [Find Student Jobs](https://www.myworkday.com/asu/d/task/1422$3898.htmld) and apply with their resume.

Cubbie does **not** open Workday. ASU CAS sits behind Cloudflare; Cubbie's cloud browser cannot sign in. Listings come from `assets/live_jobs.json` in this Skill (refreshed on a signed-in laptop, then pushed). The student Submits in their own Workday, where they are already signed in.

## When to use

- "Find me an on-campus tech job that pays $16–17."
- "Apply to ASU student jobs with my resume."
- "What's open on Workday for Tempe graders?"

Do not use it for Canvas, Handshake, LinkedIn, or staff careers on asu.wd1.myworkdayjobs.com.

## Abilities

Files (resume and cover letter the student sends), memory (filters and JR numbers already applied), documents (cover letter draft, extra-match PDF), reminders (optional weekly new-post check-in), Gmail only if they ask to email a hiring contact after yes.

Do not use the browser for Workday. Do not send Take control or a credentials card.

## Steps

1. **Collect filters** if they are missing. One question at a time. Defaults they can accept with "yes":
   - Keywords / role type (tech, grader, software, IT)
   - Hourly pay band (example: $16–17)
   - Campus (Tempe unless they name another)
   - Skip Federal Work-Study? Default yes if they say they are international or F-1; otherwise ask.
   Remember these after they confirm.

2. **Resume.** Use the PDF they just sent. If none is in this chat, ask them to send it. Keep it for drafts.

3. **Match the index.** From this Skill folder:

   ```bash
   python3 scripts/match_jobs.py --jobs assets/live_jobs.json --keywords "<keywords>" --pay-min <n> --pay-max <n> --campus "<campus>"
   ```

   Add `--skip-fws` when they asked to skip Federal Work-Study. If `live_jobs.json` is missing, run the same command with `--sample` and say the index is empty. Print the script's `as of` date in the reply.

4. **Shortlist.** Text at most three matches: JR, title, campus, pay, one-line why it fits. If more than five matched, also send a one-page PDF of the rest. If none matched, one line, then offer to loosen pay or keywords. Do not apply yet.

5. **Apply one job.** Ask: `Apply to <title> <JR>?` Wait for yes. Never apply to the whole list.

   After yes:
   - Draft a short cover letter from the resume if the role looks like software/IT/grader or they ask. Show it. Wait for approval.
   - Text numbered steps for **their** Workday (already signed in on their phone or laptop):

     1. Open Find Student Jobs.
     2. Type the JR in Workday's own search box (not a raw `inst/15$158872` URL).
     3. Skip the first Quick Apply resume-parse box.
     4. Attach their resume PDF on Resume/CV.
     5. Paste the approved cover letter if Workday asks for one.
     6. They tap Submit.

   Remember the JR as applied only after they say they submitted. Cubbie does not click Submit.

6. **Weekly check-in.** After the first successful search, offer a weekly text for new matches. Create it only after they pick a time.

## Replies

Short, plain text, no Markdown. Lead with the `as of` date and the number of matches. One apply question at a time.

## When something fails

- Cubbie's browser is on CAS, Cloudflare, `__cf_chl`, or "Just a moment": do not Take control. Match `assets/live_jobs.json` instead.
- `match_jobs.py` exit 2: say the index is missing. Do not guess jobs.
- Nothing matches: one line, then offer a wider pay band or fewer keywords.
- They want Cubbie to Submit in the cloud browser: say Workday has to stay in their login, and send the JR steps.

Outside Cubbie, match with `--jobs assets/live_jobs.json`. Use `--sample` only when that file is missing.
