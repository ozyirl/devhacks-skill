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

3. **Open Workday** in Cubbie's browser:
   https://www.myworkday.com/asu/d/task/1422$3898.htmld
   If the site asks for ASU login or Duo, hand the browser to the student until Find Student Jobs is visible. Cubbie cannot skip Duo. Saved login is reused next time.

4. **Search.** Read `references/workday-asu.md` before clicking. Filter Job Family to Student Employee. Use the page's own search box for keywords or a JR number — not the browser find command. Open enough result rows to cover the current list (often 100+). For each posting capture JR number, title, campus, posting date, job profile, funding (FWS vs none), listed pay if any, and whether it needs a cover letter.

5. **Match.** From this Skill folder, write the captured jobs to a temp JSON file and run:

   ```bash
   python3 scripts/match_jobs.py --jobs /tmp/workday-jobs.json --keywords "<keywords>" --pay-min <n> --pay-max <n> --campus "<campus>"
   ```

   Add `--skip-fws` when they asked to skip Federal Work-Study. Add `--sample` only when testing this Skill without Workday; that uses `assets/sample_jobs.json` and does not touch student state.

6. **Shortlist.** Text at most three matches (JR, title, campus, pay or worker scale, one-line why it fits). If more than five matched, also send a one-page PDF of the rest. If none matched, say so in one line and offer to loosen pay or keywords. Do not apply yet.

7. **Apply one job.** Ask: `Apply to <title> <JR>?` Wait for yes. Never apply to the whole list in one shot.
   After yes, open that posting from Find Student Jobs by typing the JR in the left search box (do not paste a raw `inst/15$158872/...` URL in a new tab).
   Fill Quick Apply from the resume. Skip the auto-parse resume box. Attach the student's PDF on Resume/CV. If the posting requires a cover letter, draft one, show it, and attach only after they approve.
   Show To / job / files that will go in, then ask `Submit this application?`
   Click Submit only after that second yes. If a control will not click, or Duo appears again, hand the browser to the student with the exact remaining step. Remember the JR as applied.

8. **Weekly check-in.** After the first successful search, offer a weekly text for new matching posts. Create it only after they pick a time.

## Replies

Short, plain text, no Markdown. Lead with the number of matches. Put each Workday link on its own line. One apply question at a time. If the widget fails, send the JR list and what to tap.

## When something fails

- Find Student Jobs will not load, or login/Duo fails: tell them to finish ASU sign-in in the browser Cubbie handed over. Do not guess jobs.
- Search widgets will not click: stop applying. Text up to three JR titles and say they can open Find Student Jobs and search that JR.
- `match_jobs.py` exit 2: the jobs file was empty or unreadable. Capture the list again.
- Nothing matches: one line, then offer a wider pay band or fewer keywords.
- Apply/Submit clicked without a yes: do not recover by submitting. Ask again.

Outside Cubbie, ask the user to open the Workday URL themselves and use the same filter and apply-one-at-a-time rules.
