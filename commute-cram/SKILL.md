---
name: commute-cram
description: Turns a student's notes, slides or Canvas course materials into a podcast-style MP3 review with two voices, quiz questions and pauses to answer, sized to their commute or walk. Use when a student wants to study on the go, listen to their notes, review on the bus, light rail, walk or at the gym, or asks for an audio or podcast version of a lecture or study guide.
---

# Commute Cram

Make a short audio review a student can listen to with their phone locked: a host explains each topic, a second
voice asks quick questions, a chime and a pause give them time to answer out loud, then the host gives the answer.
Cubbie can't make audio on its own; this Skill's script does, with free offline voices.

## When to use

- "I have 25 minutes on the light rail, make me something to review for BIO 181."
- "Turn these slides into a podcast."
- "Quiz me out loud on chapter 4 while I walk to class."
- "Can I listen to my study guide?"

Not for music, or for reading a whole textbook word for word.

## Setup (first time only)

Install the voice engine and the audio encoder once into a virtual environment under HOME, which Cubbie keeps,
then download the two voices (about 63 MB each):

```bash
python3 -m venv ~/.local/share/venvs/commute-cram && ~/.local/share/venvs/commute-cram/bin/pip install piper-tts==1.3.0 imageio-ffmpeg==0.6.0
mkdir -p ~/.local/share/piper-voices && cd ~/.local/share/piper-voices && for v in lessac ryan; do curl -fsSLO "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/$v/medium/en_US-$v-medium.onnx" && curl -fsSLO "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/$v/medium/en_US-$v-medium.onnx.json"; done
```

If the script says a voice or package is missing (exit 3), run these again. Other Skills that use Piper voices share
the same voices folder.

## Steps

1. **What and how long.** Ask what to review (a course, a chapter, an exam) and how many minutes they have.
   Default 10 minutes. Remember their usual commute length.

2. **Material.** Use what they send (notes, slides, a PDF, a photo of the whiteboard). If Canvas is connected and
   they name a course, search its materials for the topic. If nothing is available, ask them to send notes and stop;
   never review from general knowledge alone without saying so.

3. **Write the script** as JSON at `/workspace/cram.json`, following `references/script-guide.md`:

   ```json
   {"title": "BIO 181 Exam 2", "intro": "...",
    "sections": [{"heading": "Cell membranes", "explain": "...",
                  "questions": [{"q": "...", "a": "..."}]}],
    "outro": "..."}
   ```

   About 130 spoken words per minute, plus 5 seconds per question.

4. **Make the MP3.** From this Skill folder:

   ```bash
   ~/.local/share/venvs/commute-cram/bin/python scripts/cram.py --script /workspace/cram.json --out /workspace/your_files/cram/<short-name>.mp3
   ```

   Add `--pause 6` if they want more time to answer. A 10-minute episode takes a minute or two to make. It prints
   JSON with `mp3`, `minutes` and `chapters` (start time and heading of each part).

5. **Send it.** Send the MP3 file with one line ("10 min, 4 parts, 9 questions. Answer out loud at the chime."),
   then the chapter list as a short text so they can skip around.

6. **Next time.** Offer: "Want one before every exam? Tell me the dates." If they give dates, offer a reminder the
   night before each one that makes a fresh episode from that unit's materials. Create it only after they agree.

## Replies

Short, plain text, no Markdown. Send the file first, then the one-line summary, then chapters as "0:07 Mitochondria"
lines. Don't paste the whole script unless they ask.

## When something fails

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 2 | Bad script file | Fix the JSON (every question needs "q" and "a") and run again |
| 3 | Voices or packages missing | Run the Setup step, then run again |
| 4 | MP3 encoding failed | Try once more; if it fails again, send the script as text so they can still review |

Outside Cubbie, run the same commands where Python can install packages, or share the script as a text review.
