#!/usr/bin/env python3
"""Turn a short study script into a vertical, narrated recap video (MP4) with captions.

Cubbie writes the script from the student's notes or course materials as JSON; this script narrates each scene with
an offline Piper voice, draws 1080x1920 frames (title, key points revealed as they're said, big captions timed to
the voice, a progress bar), and encodes an MP4 that plays in iMessage and fits a TikTok or Instagram story.

    python scripts/reel.py --script /workspace/reel.json --out /workspace/your_files/reel/recap.mp4
    python scripts/reel.py --sample --out /tmp/recap.mp4

Script file:
    {"title": "Cell Biology in 60 Seconds", "course": "BIO 181",
     "scenes": [{"heading": "Mitochondria", "points": ["Make ATP", "Own DNA"], "narration": "..."}],
     "outro": "Save this for the exam."}

Also writes cover.png (the title frame) next to the video. Voices are read from ~/.local/share/piper-voices
(see Setup in SKILL.md), or --voices-dir.
Prints JSON: mp4, cover, seconds, scenes. Exit codes: 0 ok, 2 bad script file, 3 voices or packages missing,
4 encoding failed.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import tempfile
import textwrap
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SAMPLE = HERE / "assets" / "sample_reel.json"
VOICES = Path.home() / ".local" / "share" / "piper-voices"
VOICE = "en_US-lessac-medium"
W, H = 1080, 1920
TAIL = 0.35                 # seconds of quiet after each scene
MAX_SCENES, MAX_POINTS = 8, 3
# Scene colors, cycled: (top of gradient, bottom of gradient, accent)
THEMES = [("#1B1035", "#3A1C71", "#FFC627"), ("#062A2E", "#0F5A5E", "#7CF2D4"),
          ("#2B0F1A", "#6A1B3A", "#FFB86B"), ("#0D1B3D", "#1F4E8C", "#9AD0FF")]
INK, SOFT = "#FFFFFF", "#D9D4E6"


def die(code: int, message: str):
    print(message, file=sys.stderr)
    raise SystemExit(code)


def load_script(path: Path) -> dict:
    try:
        script = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        die(2, f"Couldn't read the script file {path}: {e}")
    scenes = script.get("scenes") if isinstance(script, dict) else None
    if not scenes or not isinstance(scenes, list):
        die(2, "The script needs a non-empty \"scenes\" list.")
    if len(scenes) > MAX_SCENES:
        die(2, f"Keep it to {MAX_SCENES} scenes or fewer; a recap should stay under about 90 seconds.")
    for i, scene in enumerate(scenes, 1):
        if not scene.get("heading") or not scene.get("narration"):
            die(2, f"Scene {i} needs a \"heading\" and a \"narration\".")
    return script


def load_voice(folder: Path):
    try:
        from piper import PiperVoice
    except ImportError:
        die(3, "piper-tts isn't installed; run the Setup step in SKILL.md.")
    model = folder / f"{VOICE}.onnx"
    if not model.exists() or not Path(f"{model}.json").exists():
        die(3, f"Voice {VOICE} is missing from {folder}; run the Setup step in SKILL.md.")
    return PiperVoice.load(str(model))


def narrate(voice, text: str) -> tuple[bytes, int]:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        voice.synthesize_wav(text, out)
    buffer.seek(0)
    with wave.open(buffer) as clip:
        return clip.readframes(clip.getnframes()), clip.getframerate()


def chunks(text: str, size: int = 6) -> list[str]:
    """Caption phrases of about `size` words, breaking after punctuation when possible."""
    words, out, current = text.split(), [], []
    for word in words:
        current.append(word)
        if len(current) >= size or (len(current) >= 3 and re.search(r"[.,;:!?]$", word)):
            out.append(" ".join(current))
            current = []
    if current:
        out.append(" ".join(current))
    return out


def font(size: int, bold: bool = False):
    from PIL import ImageFont
    names = ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf") if bold else ("DejaVuSans.ttf", "Arial.ttf", "arial.ttf")
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def background(theme):
    from PIL import Image, ImageDraw
    top, bottom = rgb(theme[0]), rgb(theme[1])
    image = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(image)
    for y in range(H):
        t = y / (H - 1)
        draw.line([(0, y), (W, y)], fill=tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return image


def wrap(draw, text: str, face, width: int) -> list[str]:
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            trial = f"{line} {word}".strip()
            if draw.textlength(trial, font=face) <= width or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def frame(script: dict, scene_index: int, total: int, heading: str, points: list[str], shown: int,
          caption: str, theme, progress: float):
    from PIL import ImageDraw
    image = background(theme)
    draw = ImageDraw.Draw(image)
    accent = theme[2]
    pad = 80

    # Progress bar, clear of the phone's status bar.
    draw.rounded_rectangle([pad, 150, W - pad, 162], radius=6, fill="#5A5470")
    draw.rounded_rectangle([pad, 150, pad + max(12, int((W - 2 * pad) * progress)), 162], radius=6, fill=accent)

    tag = (script.get("course") or "").upper()
    if tag:
        draw.text((pad, 200), tag, font=font(40, bold=True), fill=accent)
    label = f"{scene_index}/{total}" if scene_index else "RECAP"
    draw.text((W - pad - draw.textlength(label, font=font(36, bold=True)), 204), label, font=font(36, bold=True), fill=SOFT)

    # Title and outro cards get a big, centered heading; scenes keep it at the top.
    big = not scene_index
    size, step = (120, 140) if big else (92, 108)
    heading_lines = wrap(draw, heading, font(size, bold=True), W - 2 * pad)[:4]
    y = (620 - step * len(heading_lines) // 2) if big else 300
    for line in heading_lines:
        draw.text((pad, y), line, font=font(size, bold=True), fill=INK)
        y += step
    draw.rounded_rectangle([pad, y + 20, pad + 140, y + 32], radius=6, fill=accent)
    y += 90

    for point in points[:shown]:
        lines = wrap(draw, point, font(50, bold=True), W - 2 * pad - 110)[:2]
        box_h = 40 + 62 * len(lines)
        draw.rounded_rectangle([pad, y, W - pad, y + box_h], radius=28, fill=theme[0])
        draw.ellipse([pad + 34, y + box_h // 2 - 14, pad + 62, y + box_h // 2 + 14], fill=accent)
        ty = y + 22
        for line in lines:
            draw.text((pad + 96, ty), line, font=font(50, bold=True), fill=INK)
            ty += 62
        y += box_h + 24

    # Caption: big, centered, above the area where TikTok and Instagram put their buttons.
    if caption:
        face = font(64, bold=True)
        lines = wrap(draw, caption, face, W - 2 * pad - 60)[:3]
        line_h = 80
        block = line_h * len(lines) + 50
        top = 1540 - block
        draw.rounded_rectangle([pad - 10, top, W - pad + 10, top + block], radius=36, fill="#111018")
        ty = top + 25
        for line in lines:
            lw = draw.textlength(line, font=face)
            draw.text(((W - lw) / 2, ty), line, font=face, fill=accent if line is lines[0] else INK)
            ty += line_h
    return image


def build(script: dict, voice, workdir: Path) -> tuple[list[tuple[Path, float]], bytes, int, Path]:
    title = script.get("title") or "Quick Recap"
    scenes = [{"heading": title, "points": [], "narration": script.get("intro") or title, "intro": True}]
    scenes += [{**s, "points": [str(p) for p in (s.get("points") or [])][:MAX_POINTS]} for s in script["scenes"]]
    if script.get("outro"):
        scenes.append({"heading": script["outro"], "points": [], "narration": script["outro"], "outro": True})

    clips = [narrate(voice, s["narration"]) for s in scenes]
    rate = clips[0][1]
    lengths = [len(pcm) / 2 / rate + TAIL for pcm, _ in clips]
    total_seconds = sum(lengths)

    frames: list[tuple[Path, float]] = []
    elapsed = 0.0
    numbered = [s for s in scenes if not s.get("intro") and not s.get("outro")]
    cover = None
    for i, (scene, length) in enumerate(zip(scenes, lengths)):
        theme = THEMES[i % len(THEMES)]
        parts = chunks(scene["narration"])
        weights = [len(p) + 4 for p in parts]
        number = numbered.index(scene) + 1 if scene in numbered else 0
        spoken = 0.0
        for j, (part, weight) in enumerate(zip(parts, weights)):
            duration = (length - TAIL) * weight / sum(weights) + (TAIL if j == len(parts) - 1 else 0)
            # Reveal the scene's points evenly as the narration goes.
            share = (spoken + weight) / sum(weights)
            shown = min(len(scene["points"]), max(1, round(share * len(scene["points"])))) if scene["points"] else 0
            image = frame(script, number, len(numbered), scene["heading"], scene["points"], shown, part, theme,
                          (elapsed + (length - TAIL) * spoken / sum(weights)) / total_seconds)
            path = workdir / f"f{i:02d}_{j:02d}.png"
            image.save(path)
            if cover is None:
                cover = path
            frames.append((path, duration))
            spoken += weight
        elapsed += length

    pcm = b"".join(c[0] + b"\x00\x00" * int(rate * TAIL) for c in clips)
    return frames, pcm, rate, cover


def encode(frames, pcm: bytes, rate: int, workdir: Path, out: Path):
    try:
        import imageio_ffmpeg
    except ImportError:
        die(3, "imageio-ffmpeg isn't installed; run the Setup step in SKILL.md.")
    wav = workdir / "voice.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    listing = workdir / "frames.txt"
    lines = [f"file '{p.as_posix()}'\nduration {d:.3f}" for p, d in frames]
    lines.append(f"file '{frames[-1][0].as_posix()}'")  # the concat format needs the last frame twice
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
               "-f", "concat", "-safe", "0", "-i", str(listing), "-i", str(wav),
               "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
               "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        die(4, f"Couldn't encode the video: {result.stderr.strip()[-300:]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--script", type=Path, help="JSON recap script")
    parser.add_argument("--out", type=Path, required=True, help="MP4 file to write")
    parser.add_argument("--voices-dir", type=Path, default=VOICES)
    parser.add_argument("--sample", action="store_true", help="use the bundled sample script")
    args = parser.parse_args()
    if args.sample == bool(args.script):
        die(2, "Give either --script <file> or --sample.")
    try:
        import PIL  # noqa: F401
    except ImportError:
        die(3, "Pillow isn't installed; run the Setup step in SKILL.md.")

    script = load_script(SAMPLE if args.sample else args.script)
    voice = load_voice(args.voices_dir)
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        frames, pcm, rate, cover = build(script, voice, workdir)
        encode(frames, pcm, rate, workdir, args.out)
        cover_out = args.out.with_name("cover.png")
        cover_out.write_bytes(cover.read_bytes())
    print(json.dumps({"mp4": str(args.out), "cover": str(cover_out),
                      "seconds": round(len(pcm) / 2 / rate, 1), "scenes": len(script["scenes"])}, indent=2))


if __name__ == "__main__":
    main()
