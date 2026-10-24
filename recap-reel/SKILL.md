---
name: recap-reel
description: Turns a student's notes, slides or Canvas materials into a 30 to 90 second narrated recap video with captions, made for iMessage and TikTok or Instagram stories. Use when a student wants a video summary, a quick recap before an exam, a study reel, a TikTok-style explainer of a lecture, or something to send their study group.
---

# Recap Reel

Make a short, narrated study video a student actually wants to watch: a title card, one scene per key idea with
its points appearing as they're said, captions timed to the voice, and a progress bar. Cubbie can't make video on
its own; this Skill's script does, with a free offline voice and ffmpeg.

## When to use

- "Make me a 60 second recap of today's BIO 181 lecture."
- "Turn chapter 7 into a TikTok I can watch before the exam."
- "Can you make a video summary of these slides for my study group?"

Not for long lectures word for word (keep it under about 90 seconds), and not for music videos or real footage.

## Setup (first time only)

Install the voice engine, ffmpeg and Pillow once into a virtual environment under HOME, which Cubbie keeps, then
download the voice (about 63 MB):

```bash
python3 -m venv ~/.local/share/venvs/recap-reel && ~/.local/share/venvs/recap-reel/bin/pip install piper-tts==1.3.0 imageio-ffmpeg==0.6.0 pillow==11.1.0
mkdir -p ~/.local/share/piper-voices && cd ~/.local/share/piper-voices && curl -fsSLO "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" && curl -fsSLO "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
```

If the script says a voice or package is missing (exit 3), run these again. Other Skills that use Piper voices share
the same voices folder.

## Steps

1. **Topic and length.** Ask what to recap (a lecture, a chapter, an exam unit) if they haven't said. Default
   60 seconds; at most 90.

2. **Material.** Use what they send (slides, notes, a PDF, a photo of the board). If Canvas is connected and they
   name a course, search its materials for the topic. If nothing is available, ask them to send notes and stop;
   never make a recap from general knowledge without saying so.

3. **Write the script** as JSON at `/workspace/reel.json`, following `references/script-guide.md`:

   ```json
   {"title": "Cells in 60 Seconds", "course": "BIO 181", "intro": "...",
    "scenes": [{"heading": "Mitochondria", "points": ["Make ATP", "Own DNA"], "narration": "..."}],
    "outro": "Save this for exam night."}
   ```

   About 150 spoken words per minute in total; 3 to 6 scenes; at most 3 short points per scene.

4. **Make the video.** From this Skill folder:

   ```bash
   ~/.local/share/venvs/recap-reel/bin/python scripts/reel.py --script /workspace/reel.json --out /workspace/your_files/reel/<short-name>.mp4
   ```

   A 60-second video takes about a minute to make. It prints JSON with `mp4`, `cover` (the title frame as a PNG),
   `seconds` and `scenes`.

5. **Send it.** Send the MP4 with one line ("62 sec recap of cell bio, 4 key ideas."). Mention once that it's
   sized for a TikTok or Instagram story if they want to post it or send it to their study group.

6. **Change it.** If they want edits ("slower", "add the Krebs cycle", "shorter"), update the script and run the
   same command again.

## Replies

Short, plain text, no Markdown. Send the video first, then one line. Don't paste the script unless they ask.

## When something fails

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 2 | Bad script file (missing heading or narration, more than 8 scenes) | Fix the JSON and run again |
| 3 | Voice or packages missing | Run the Setup step, then run again |
| 4 | Video encoding failed | Try once more; if it fails again, send the key points as text instead |

Outside Cubbie, run the same commands where Python can install packages, or share the script as a text summary.
