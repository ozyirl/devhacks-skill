# Writing a Commute Cram script

The student is listening, often walking or on a train, with no screen. Write for the ear.

## Length

- About 130 spoken words per minute; each question adds about 5 seconds (chime, pause, answer).
- 10 minutes is roughly 4 to 6 sections of 120 to 180 words, with 1 to 3 questions each.

## Rules

- **Only from their material.** Use the student's notes, slides or course files. Don't add facts that aren't
  there; if something important is missing, say "check your notes on this" instead of guessing.
- **Spoken, not written.** Short sentences. No bullet symbols, tables, URLs, or "see figure 3".
- **Say symbols out loud.** "H two O", "x squared", "delta G", "about three point one four".
- **Spell out tricky terms once** when it helps: "mitochondria, mito-KON-dree-uh".
- **Questions test recall,** not trivia: one fact or one step each, answerable in a few words.
- **Answers are short** and add the one-line reason when it helps memory.
- **Hardest parts first,** when the student is freshest; end with a two-sentence recap.
- `intro` (one or two sentences) and `outro` (one sentence) are optional; defaults are used if left out.

## Example section

```json
{"heading": "Cell membranes",
 "explain": "The cell membrane is a phospholipid bilayer. The heads love water and face out, the tails avoid water and face in, and proteins float in between to move things across.",
 "questions": [
   {"q": "Which part of a phospholipid faces the water?", "a": "The head. It's hydrophilic."}
 ]}
```
