#!/usr/bin/env python3
"""Turn a study script into a two-voice, podcast-style MP3 with quiz pauses.

Cubbie writes the script from the student's notes or course materials as JSON; this script reads it aloud with two
offline Piper voices (a host who explains, a quizzer who asks), adds a chime and a pause before each answer, and
encodes one MP3 with chapter times.

    python scripts/cram.py --script /workspace/cram.json --out /workspace/your_files/cram.mp3
    python scripts/cram.py --sample --out /tmp/cram.mp3

Script file:
    {"title": "BIO 181 Exam 2", "intro": "...",
     "sections": [{"heading": "Cell membranes", "explain": "...",
                   "questions": [{"q": "...", "a": "..."}]}],
     "outro": "..."}

--pause sets the seconds of silence to answer each question (default 4). Voices are read from
~/.local/share/piper-voices (see Setup in SKILL.md), or --voices-dir.
Prints JSON: mp3, minutes, chapters. Exit codes: 0 ok, 2 bad script file, 3 voices or packages missing, 4 encoding failed.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SAMPLE = HERE / "assets" / "sample_script.json"
VOICES = Path.home() / ".local" / "share" / "piper-voices"
HOST, QUIZ = "en_US-lessac-medium", "en_US-ryan-medium"
GAP = 0.45            # seconds between lines
SECTION_GAP = 1.0     # seconds before a new section


def die(code: int, message: str):
    print(message, file=sys.stderr)
    raise SystemExit(code)


def load_script(path: Path) -> dict:
    try:
        script = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        die(2, f"Couldn't read the script file {path}: {e}")
    sections = script.get("sections") if isinstance(script, dict) else None
    if not sections or not isinstance(sections, list):
        die(2, "The script needs a non-empty \"sections\" list.")
    for i, section in enumerate(sections, 1):
        if not section.get("explain") and not section.get("questions"):
            die(2, f"Section {i} needs an \"explain\" text or \"questions\".")
        for q in section.get("questions") or []:
            if not q.get("q") or not q.get("a"):
                die(2, f"Every question in section {i} needs \"q\" and \"a\".")
    return script


class Voices:
    def __init__(self, folder: Path):
        try:
            from piper import PiperVoice
        except ImportError:
            die(3, "piper-tts isn't installed; run the Setup step in SKILL.md.")
        self.voices = {}
        for role, name in (("host", HOST), ("quiz", QUIZ)):
            model = folder / f"{name}.onnx"
            if not model.exists() or not Path(f"{model}.json").exists():
                die(3, f"Voice {name} is missing from {folder}; run the Setup step in SKILL.md.")
            self.voices[role] = PiperVoice.load(str(model))
        self.rate = None

    def say(self, role: str, text: str) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as out:
            self.voices[role].synthesize_wav(text, out)
        buffer.seek(0)
        with wave.open(buffer) as clip:
            if self.rate is None:
                self.rate = clip.getframerate()
            elif clip.getframerate() != self.rate:
                die(3, "The two voices use different sample rates; use the voices named in SKILL.md.")
            return clip.readframes(clip.getnframes())


def silence(rate: int, seconds: float) -> bytes:
    return b"\x00\x00" * int(rate * seconds)


def chime(rate: int) -> bytes:
    """A soft two-note chime (16-bit mono) that says "your turn"."""
    frames = bytearray()
    for freq, length in ((880, 0.12), (1320, 0.18)):
        n = int(rate * length)
        for i in range(n):
            fade = min(1.0, i / (rate * 0.01), (n - i) / (rate * 0.04))
            frames += struct.pack("<h", int(6000 * fade * math.sin(2 * math.pi * freq * i / rate)))
    return bytes(frames)


def build(script: dict, voices: Voices, pause: float) -> tuple[bytes, int, list[dict]]:
    parts: list[bytes] = []
    chapters = []
    seconds = 0.0

    def add(audio: bytes):
        nonlocal seconds
        parts.append(audio)
        seconds += len(audio) / 2 / voices.rate

    def line(role: str, text: str):
        add(voices.say(role, text))
        add(silence(voices.rate, GAP))

    title = script.get("title") or "Your study session"
    line("host", script.get("intro") or f"This is your Commute Cram for {title}. Let's go.")
    for i, section in enumerate(script["sections"], 1):
        add(silence(voices.rate, SECTION_GAP))
        heading = section.get("heading") or f"Part {i}"
        chapters.append({"time": clock(seconds), "heading": heading})
        line("host", f"Part {i}. {heading}.")
        if section.get("explain"):
            line("host", section["explain"])
        for q in section.get("questions") or []:
            line("quiz", f"Quick check. {q['q']}")
            add(chime(voices.rate))
            add(silence(voices.rate, pause))
            line("host", q["a"])
    add(silence(voices.rate, SECTION_GAP))
    line("host", script.get("outro") or "That's the review. You've got this.")
    return b"".join(parts), voices.rate, chapters


def clock(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def encode_mp3(pcm: bytes, rate: int, title: str, out: Path):
    try:
        import imageio_ffmpeg
    except ImportError:
        die(3, "imageio-ffmpeg isn't installed; run the Setup step in SKILL.md.")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "cram.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm)
        command = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(wav),
                   "-codec:a", "libmp3lame", "-b:a", "96k", "-metadata", f"title={title}",
                   "-metadata", "artist=Commute Cram", str(out)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            die(4, f"Couldn't encode the MP3: {result.stderr.strip()[-300:]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--script", type=Path, help="JSON study script")
    parser.add_argument("--out", type=Path, required=True, help="MP3 file to write")
    parser.add_argument("--pause", type=float, default=4.0, help="seconds to answer each question (default 4)")
    parser.add_argument("--voices-dir", type=Path, default=VOICES)
    parser.add_argument("--sample", action="store_true", help="use the bundled sample script")
    args = parser.parse_args()
    if args.sample == bool(args.script):
        die(2, "Give either --script <file> or --sample.")
    if not 1 <= args.pause <= 15:
        die(2, "--pause must be between 1 and 15 seconds.")

    script = load_script(SAMPLE if args.sample else args.script)
    pcm, rate, chapters = build(script, Voices(args.voices_dir), args.pause)
    title = script.get("title") or "Commute Cram"
    encode_mp3(pcm, rate, title, args.out)
    print(json.dumps({"mp3": str(args.out), "title": title,
                      "minutes": round(len(pcm) / 2 / rate / 60, 1), "chapters": chapters}, indent=2))


if __name__ == "__main__":
    main()
