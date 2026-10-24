---
name: asu-lab-match
description: Matches an ASU student with faculty whose research fits their interests and resume, drafts a personal first email to each, and sends only after they say yes. Use when a student wants undergrad research, a research lab, a professor to work with, research experience for grad school, FURI or honors thesis mentors, or asks how to email a professor about research.
---

# ASU Lab Match

Help an ASU undergrad get into research: find the right professors in ASU's public faculty directory, explain
why each is a fit, draft a short personal email, and track replies. This Skill is for research at ASU. It is not for
jobs (use the on-campus jobs Skill), class questions, or emailing a professor about a grade or extension.

Cubbie already knows how to read a resume and draft email. This Skill adds the faculty search and ranking, the
email rules that get replies, the send gate, and follow-up tracking.

## When to use

- "I want to do research in AI for healthcare. Who should I email?"
- "How do I get into a lab at ASU? Here's my resume."
- "Find me a mentor for my honors thesis on desert ecology."
- "Did any of the professors I emailed reply?"

## Abilities

Files (the student's resume), Gmail (drafts, and checking for replies), memory (interests and the student's
year and major), reminders (follow-up check-in), documents (a PDF if they want the full list).
No sign-in: the faculty directory is public.

## Steps

1. **Interests.** Ask what they want to research, in their own words, if they haven't said. Turn it into 1 to 3
   short phrases ("machine learning, healthcare"). Ask their major and year once and remember them.

2. **Resume.** Use the resume they sent. If there is none, ask for it; it's optional but makes the match and the
   email much better. Pull out up to 6 concrete skills or tools (Python, PCR, CAD...) for `--skills`.

3. **Search.** From this Skill folder:

   ```bash
   python3 scripts/find_labs.py search --interests "<phrase 1>, <phrase 2>" --skills "<skill 1>, <skill 2>" --limit 5
   ```

   Add `--campus <campus>` only if they asked for one. It returns JSON with `results`, best match first. Each has
   `name`, `title`, `department`, `campus`, `email`, `profile_url`, `website`, `expertise`, `research`, `bio`,
   `matched` and `score`. People already emailed are left out.

4. **Shortlist.** Text the top 3, each as: name and title, department, one line on why it fits, citing their
   research and the student's own experience, and the profile link on its own line. If fewer than 3 matched,
   suggest a broader phrase and search again. Never invent a professor or a research topic; use only what the
   results say.

5. **Read before writing.** For the professor the student picks, open their `profile_url` and `website` (if any)
   in the browser and note one specific project, paper or topic to mention.

6. **Draft the email.** Follow `references/first-email.md`. Show the draft in the thread, then ask:
   "Save this as a Gmail draft?" After yes, create the draft to the professor's `email`, with the resume attached
   if the student agrees. Then ask: "Send it now?" Send only after that second yes. One professor at a time;
   at most 3 new emails a week, so each one is personal.

7. **Track it.** After an email is sent, run:

   ```bash
   python3 scripts/find_labs.py contacted --add <asurite> --name "<name>" --today <YYYY-MM-DD>
   ```

   using the student's local date. Offer a check-in in 10 days ("Want me to check for a reply on Nov 3?").
   Create it only after they agree.

8. **Follow up.** In the check-in (or when they ask), search Gmail for a reply from each professor. If one replied,
   run `contacted --replied <asurite>`, tell the student, and offer 3 talking points from that professor's work
   for a meeting. For the rest, run `followups --today <YYYY-MM-DD>` and offer one short, polite follow-up draft per
   person, with the same two yeses. Never send a second follow-up.

Also mention, once, that their department advisor can point them to ASU's undergrad research programs (for
example FURI in the Fulton Schools, or Barrett thesis advising) and to labs that post openings.

## Replies

Short, plain text, no Markdown. Lead with the best match. Profile links on their own line. Show email drafts as
plain text. One yes question at a time.

## When something fails

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 2 | Missing interests or a bad date | Ask for interests, or pass the date as YYYY-MM-DD |
| 5 | Directory unreachable | Say ASU's directory isn't answering; try again later. Never guess professors |

- Gmail not connected: show the draft in the thread for them to copy, and skip reply tracking.
- Nothing matches: one line, then offer broader phrases ("AI" instead of "graph neural networks for proteins").
- Sent without a yes: never. If a send goes wrong, tell the student exactly what was sent.

Outside Cubbie, run the same search, show the draft, and let the user send it from their own email.
