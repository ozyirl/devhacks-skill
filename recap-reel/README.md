# Recap Reel

A [Cubbie](https://cubbie.ai) Skill that turns your notes, slides or Canvas materials into a 30 to 90 second vertical
study video in a clean editorial style: a narrated title card, one numbered scene per key idea with points revealed as
they're explained, key-fact callouts, captions that underline each word as it's spoken, a segmented progress bar and
a closing recap checklist. Watch it in iMessage or post it as a TikTok or Instagram story.

Install: text this folder's link to Cubbie and reply "yes".

- `SKILL.md`: what Cubbie does, step by step, and the one-time Setup
- `scripts/reel.py`: makes the MP4 with an offline Piper voice, Pillow and ffmpeg (try `--sample`)
- `references/script-guide.md`: how to write a script that works as a short video

Voice: [Piper](https://github.com/OHF-Voice/piper1-gpl) `en_US-lessac-medium`.
Font: [Inter](https://github.com/rsms/inter), bundled in `assets/fonts/` under the SIL Open Font License
(`assets/fonts/OFL.txt`).
