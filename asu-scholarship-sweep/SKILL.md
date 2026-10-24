---
name: asu-scholarship-sweep
description: Finds the ASU scholarships a student qualifies for in Scholarship Universe, tracks every deadline and dollar, helps draft essays from the student's own stories, and submits only after they say yes. Use when an ASU student asks about scholarships, free money, paying for school, financial aid essays, Scholarship Universe, or a scholarship deadline, even if they never say "scholarship".
---

# ASU Scholarship Sweep

Help an ASU student find and apply for scholarships they qualify for, without missing deadlines. This Skill works
in ASU's Scholarship Universe portal (https://asu.scholarshipuniverse.com) and, when asked, public outside
scholarships. It does not give financial aid advice, fill in the FAFSA, or pay anything.

Cubbie already knows how to open a site, read files and draft text. This Skill adds the Scholarship Universe path,
an exact deadline and amount tracker, essay rules that keep the student's own voice, and the submit gate.

## When to use

- "Are there any scholarships I can get? I'm a CS sophomore."
- "I need money for next semester."
- "Help me write my scholarship essay about being first-gen."
- "What scholarship deadlines do I have this month?"

## Abilities

Browser (Scholarship Universe), files (past essays, resume, transcript the student sends), memory (major, year,
the stories they're comfortable sharing), documents (essay drafts, a deadline list PDF), reminders (deadline
check-ins). Sign-in: the student's ASU account in Cubbie's browser.

## Steps

1. **Profile.** Ask only what's missing, one question at a time: major, year, campus. Then, optionally, things
   scholarships ask about (first-generation, transfer, veteran, clubs, work, community service). Say they can skip
   any question. Remember only what they choose to share.

2. **Sign in.** Open https://asu.scholarshipuniverse.com in the browser. When it asks for ASU login and Duo, hand
   the browser to the student until the portal's home page shows. Never ask for their password in the chat.

3. **Profile questions.** Scholarship Universe matches on its own profile questions. If some are unanswered, list
   them in the thread, fill in only what the student tells you, and ask "Save these answers?" before saving.

4. **Read matches.** Open the Scholarships tab. For each matched scholarship capture the name, amount, deadline,
   requirements, and the essay prompt if any. Record each one from this Skill folder:

   ```bash
   python3 scripts/tracker.py add --name "<name>" --amount <dollars> --deadline <YYYY-MM-DD> --source asu --prompt "<prompt>" --requirements "<few words>"
   ```

   Leave out `--amount` if none is listed. Use `update --id <id> ...` if the deadline or amount changes.

5. **Shortlist.** Run `python3 scripts/tracker.py list --today <YYYY-MM-DD> --due-within 45` with the student's
   local date. Text the top 3 by deadline and fit: name, amount, deadline in days, and what it needs (essay, letter,
   transcript). Lead with the total: "You qualify for 6 scholarships worth $7,500. Soonest is due in 8 days."
   If more than five, also send a PDF of the full list.

6. **Essay.** For the one they pick, follow `references/essays.md`. Draft from their own stories and past essays
   only, show it, and change what they want. They make the final edits. Run
   `update --id <id> --status drafting` when you start.

7. **Submit one.** Show exactly what will be submitted (the scholarship, the essay, any files), then ask
   "Submit this application?" Click Submit only after that yes. If Duo or a control blocks you, hand the browser
   to the student with the exact remaining step. Then run `update --id <id> --status submitted`.

8. **Deadlines.** Offer calendar reminders: run `python3 scripts/tracker.py ics --all --out /workspace/your_files/scholarships`
   and send the `.ics` files (each reminds 3 days before the deadline). Offer a weekly check-in that runs `list
   --due-within 14` and texts only what's due soon; create it only after they pick a day and time.

9. **Results.** When they hear back, run `update --id <id> --status won` or `lost`. When they win, celebrate
   with the running total won.

Outside scholarships: only if they ask. Search the web, check each against the scam signs in
`references/essays.md`, and record real ones with `--source outside --url <link>`.

## Replies

Short, plain text, no Markdown. Lead with money and the nearest deadline. One scholarship per text, links on their
own line. One yes question at a time.

## When something fails

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 2 | Bad date, unknown id or duplicate | Use YYYY-MM-DD; run `list` for ids; use `update` instead of `add` |

- Login or Duo fails: ask the student to finish ASU sign-in in the browser you handed over. Don't guess scholarships.
- Nothing matched: say so, suggest finishing more profile questions, and offer outside scholarships.
- Never submit without the student's yes, never pay an application fee, and never invent an achievement.

Outside Cubbie, ask the user to open Scholarship Universe themselves and paste the scholarships; the tracker and
essay rules work the same.
