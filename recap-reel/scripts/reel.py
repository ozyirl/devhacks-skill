#!/usr/bin/env python3
"""Turn a short study script into a narrated vertical recap video (MP4) with animated captions.

Cubbie writes the script from the student's notes or course materials as JSON; this script narrates each scene with
an offline Piper voice and animates 1080x1920 frames at 30 fps in a restrained editorial style (one dark
background, one accent color, the bundled Inter font): numbered sections that fade and rise in, key points
revealed and highlighted as they're explained, a "key fact" callout, lower-third captions that underline each word
as it's spoken, a segmented progress bar, and a closing recap checklist that ticks off every idea.

    python scripts/reel.py --script /workspace/reel.json --out /workspace/your_files/reel/recap.mp4
    python scripts/reel.py --sample --out /tmp/recap.mp4

Script file:
    {"title": "Cells in 60 Seconds", "course": "BIO 181", "intro": "...",
     "scenes": [{"heading": "Mitochondria", "points": ["Make ATP", "Own DNA"],
                 "key": "ATP", "narration": "..."}],
     "outro": "Save this for exam night."}
`key` (optional, a few characters or a number) is shown big in the middle of the scene.

Also writes cover.png (the title frame) next to the video. Voices are read from ~/.local/share/piper-voices
(see Setup in SKILL.md), or --voices-dir.
Prints JSON: mp4, cover, seconds, scenes. Exit codes: 0 ok, 2 bad script file, 3 voices or packages missing,
4 encoding failed.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import re
import subprocess
import sys
import tempfile
import wave
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SAMPLE = HERE / "assets" / "sample_reel.json"
VOICES = Path.home() / ".local" / "share" / "piper-voices"
VOICE = "en_US-lessac-medium"
W, H, FPS = 1080, 1920, 30
PAD = 80
TAIL = 0.45                 # seconds of quiet after each scene
MAX_SCENES, MAX_POINTS = 8, 3
CAPTION_WORDS = 6
FONTS = HERE / "assets" / "fonts"
# One restrained palette for every scene.
BG, GHOST, TRACK, RULE = (15, 16, 18), (27, 28, 32), (255, 255, 255, 46), (42, 43, 48)
WHITE, MUTED, UPCOMING, ACCENT = (255, 255, 255), (150, 151, 160), (105, 106, 114), (242, 179, 61)


def die(code: int, message: str):
    print(message, file=sys.stderr)
    raise SystemExit(code)


# ---------- script and narration ----------

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


def timeline(script: dict, voice) -> tuple[list[dict], bytes, int, float]:
    """Narrate every scene and work out when each word, point, key fact and recap tick appears."""
    content = [{**s, "kind": "scene", "points": [str(p) for p in (s.get("points") or [])][:MAX_POINTS]}
               for s in script["scenes"]]
    title = script.get("title") or "Quick Recap"
    headings = [s["heading"] for s in content]
    scenes = [{"kind": "intro", "heading": title, "points": [],
               "narration": script.get("intro") or f"{title}. Here's what you need to know."}]
    scenes += content
    scenes.append({"kind": "recap", "heading": "Recap", "points": headings,
                   "narration": "Quick recap. " + ". ".join(headings) + ". " + (script.get("outro") or "")})

    audio, rate, start = [], None, 0.0
    for scene in scenes:
        pcm, rate = narrate(voice, scene["narration"])
        speech = len(pcm) / 2 / rate
        audio.append(pcm + b"\x00\x00" * int(rate * TAIL))
        words = scene["narration"].split()
        weights = [len(re.sub(r"\W", "", w)) + 2 for w in words]
        total, times, acc = sum(weights), [], 0.0
        for weight in weights:
            times.append((acc / total * speech, (acc + weight) / total * speech))
            acc += weight
        n = len(scene["points"])
        if scene["kind"] == "recap":
            # Tick each idea the moment the recap says it (after the two words "Quick recap.").
            reveals, at = [], 2
            for heading in scene["points"]:
                reveals.append(times[min(at, len(times) - 1)][0])
                at += len(heading.split())
        else:
            reveals = [0.35 + speech * 0.9 * i / max(n, 1) for i in range(n)]
        scene.update(start=start, length=speech + TAIL, speech=speech, words=words, times=times,
                     chunks=caption_chunks(words), reveals=reveals, key_at=speech * 0.45)
        start += speech + TAIL
    numbered = 0
    for scene in scenes:
        if scene["kind"] == "scene":
            numbered += 1
            scene["number"] = numbered
    return scenes, b"".join(audio), rate, start


def caption_chunks(words: list[str]) -> list[tuple[int, int]]:
    """Word index ranges for caption phrases, breaking after punctuation when possible."""
    chunks, first = [], 0
    for i, word in enumerate(words):
        size = i - first + 1
        if size >= CAPTION_WORDS or (size >= 3 and re.search(r"[.,;:!?]$", word)) or i == len(words) - 1:
            chunks.append((first, i + 1))
            first = i + 1
    return chunks


# ---------- drawing helpers ----------

@lru_cache(maxsize=64)
def font(size: int, weight: int = 700):
    """Inter from the Skill's own assets, so the video looks the same on every machine."""
    from PIL import ImageFont
    try:
        return ImageFont.truetype(str(FONTS / f"Inter-{weight}.ttf"), size)
    except OSError:
        for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf") if weight >= 600 else ("DejaVuSans.ttf", "arial.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default(size=size)


def rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def ease(x: float) -> float:
    """Ease-out cubic: quick start, soft landing, no overshoot."""
    return 1 - (1 - clamp(x)) ** 3


def wrap(draw, text: str, face, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=face) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + ([line] if line else [])


def spaced(draw, xy, text: str, face, fill, tracking: float = 0.12) -> float:
    """Small-caps style label with letter spacing; returns its width."""
    x, y = xy
    gap = face.size * tracking
    for char in text:
        draw.text((x, y), char, font=face, fill=fill)
        x += draw.textlength(char, font=face) + gap
    return x - xy[0] - gap


def spaced_width(draw, text: str, face, tracking: float = 0.12) -> float:
    return sum(draw.textlength(c, font=face) for c in text) + face.size * tracking * (len(text) - 1)


def with_alpha(color, a: float):
    return tuple(color) + (int(255 * clamp(a)),)


@lru_cache(maxsize=1)
def background():
    """Solid near-black with a soft light from the top and a dark band behind the captions."""
    from PIL import Image, ImageDraw
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    for y in range(H):
        lift = 10 * (1 - y / H) ** 2                       # a hint of light at the top
        shade = 14 * clamp((y - 1180) / 500) * clamp((1700 - y) / 160 + 0.6)   # caption band
        v = [max(0, min(255, round(c + lift - shade))) for c in BG]
        draw.line([(0, y), (W, y)], fill=tuple(v))
    return image


# ---------- one frame ----------

def frame(script: dict, scenes: list[dict], total: float, t: float):
    from PIL import ImageDraw
    index = max(i for i, s in enumerate(scenes) if s["start"] <= t or i == 0)
    scene = scenes[index]
    lt = t - scene["start"]
    # Content fades in at the start of a scene and out at its end.
    show = ease(lt / 0.4) * clamp((scene["length"] - lt) / 0.22)

    image = background().copy()
    draw = ImageDraw.Draw(image, "RGBA")

    # A large, faint section number drifts slowly behind the content.
    if scene["kind"] == "scene":
        mark = f"{scene['number']:02d}"
        face = font(520, 700)
        draw.text((W - PAD - draw.textlength(mark, font=face) + 40, 330 - lt * 6), mark, font=face,
                  fill=with_alpha(GHOST, show))

    draw_progress(draw, scenes, t)
    label = script.get("course", "").upper()
    if label:
        spaced(draw, (PAD, 176), label, font(28, 600), with_alpha(MUTED, 1))
    count = {"intro": "", "recap": "REVIEW"}.get(scene["kind"])
    if count is None:
        count = f"{scene['number']:02d} / {sum(1 for s in scenes if s['kind'] == 'scene'):02d}"
    if count:
        face = font(28, 600)
        spaced(draw, (W - PAD - spaced_width(draw, count, face), 176), count, face, with_alpha(MUTED, 1))

    if scene["kind"] == "intro":
        draw_intro(draw, script, scene, scenes, lt, show)
    else:
        bottom = draw_scene(draw, scene, lt, show)
        if scene.get("key") and lt >= scene["key_at"]:
            draw_key(draw, str(scene["key"]), lt - scene["key_at"], show, bottom)
    draw_caption(draw, scene, lt)
    return image


def draw_progress(draw, scenes, t):
    """One segment per scene, like stories; the current one fills as it plays."""
    gap, y = 10, 124
    width = (W - 2 * PAD - gap * (len(scenes) - 1)) / len(scenes)
    for i, s in enumerate(scenes):
        x = PAD + i * (width + gap)
        draw.rounded_rectangle([x, y, x + width, y + 6], radius=3, fill=TRACK)
        filled = clamp((t - s["start"]) / s["length"])
        if filled:
            draw.rounded_rectangle([x, y, x + max(6, width * filled), y + 6], radius=3, fill=(255, 255, 255, 235))


def rise(alpha: float, base: int, distance: int = 28) -> int:
    return base + int((1 - alpha) * distance)


def draw_intro(draw, script, scene, scenes, lt, show):
    face = font(116, 700)
    lines = wrap(draw, scene["heading"], face, W - 2 * PAD)[:4]
    y = 640 - 64 * len(lines)
    kicker = "RECAP"
    a = ease(lt / 0.4) * show
    spaced(draw, (PAD, rise(a, y - 90)), kicker, font(32, 700), with_alpha(ACCENT, a), 0.18)
    for i, line in enumerate(lines):
        a = ease((lt - 0.1 - 0.1 * i) / 0.5) * show
        draw.text((PAD, rise(a, y)), line, font=face, fill=with_alpha(WHITE, a))
        y += 128
    rule = ease((lt - 0.45) / 0.6)
    draw.rectangle([PAD, y + 34, PAD + int(160 * rule), y + 40], fill=with_alpha(ACCENT, show))
    ideas = sum(1 for s in scenes if s["kind"] == "scene")
    meta = f"{ideas} key ideas  ·  {round(sum(s['length'] for s in scenes))} seconds"
    a = ease((lt - 0.6) / 0.5) * show
    draw.text((PAD, rise(a, y + 76)), meta, font=font(42, 400), fill=with_alpha(MUTED, a))


def draw_scene(draw, scene, lt, show) -> int:
    recap = scene["kind"] == "recap"
    a = ease(lt / 0.45) * show
    y = 300
    # Section label: "01 ——" in the accent color.
    label = "REVIEW" if recap else f"{scene['number']:02d}"
    lw = spaced(draw, (PAD, rise(a, y)), label, font(34, 700), with_alpha(ACCENT, a), 0.14)
    draw.rectangle([PAD + lw + 22, rise(a, y) + 20, PAD + lw + 22 + int(70 * ease((lt - 0.15) / 0.5)),
                    rise(a, y) + 23], fill=with_alpha(ACCENT, a))
    y += 74
    face = font(108, 700)
    for i, line in enumerate(wrap(draw, scene["heading"], face, W - 2 * PAD - 40)[:2]):
        la = ease((lt - 0.06 - 0.08 * i) / 0.45) * show
        draw.text((PAD, rise(la, y)), line, font=face, fill=with_alpha(WHITE, la))
        y += 120
    y += 60

    revealed = [i for i, at in enumerate(scene["reveals"]) if lt >= at]
    active = revealed[-1] if revealed else -1
    pface, nface = font(58, 400), font(40, 600)
    for i, point in enumerate(scene["points"]):
        lines = wrap(draw, point, pface, W - 2 * PAD - 120)[:2]
        row_h = 60 + 72 * len(lines)
        at = scene["reveals"][i]
        if lt >= at or recap:
            pa = (ease((lt - at) / 0.45) if not recap else ease(lt / 0.5)) * show
            top = rise(pa, y, 22)
            draw.line([(PAD, top), (W - PAD, top)], fill=with_alpha(RULE, pa), width=2)
            if recap:
                done = lt >= at
                box = [PAD, top + 42, PAD + 44, top + 86]
                if done:
                    k = ease((lt - at) / 0.3)
                    draw.rectangle(box, fill=with_alpha(ACCENT, pa * k), outline=with_alpha(ACCENT, pa), width=3)
                    draw.line([(PAD + 10, top + 64), (PAD + 19, top + 74), (PAD + 35, top + 52)],
                              fill=with_alpha(BG, pa * k), width=5)
                else:
                    draw.rectangle(box, outline=with_alpha(MUTED, pa), width=3)
                color = WHITE if done else MUTED
            else:
                draw.text((PAD, top + 42), f"{i + 1}", font=nface, fill=with_alpha(ACCENT, pa))
                color = WHITE if i == active else MUTED
            ty = top + 32
            for line in lines:
                draw.text((PAD + 90, ty), line, font=pface, fill=with_alpha(color, pa))
                ty += 72
        y += row_h
    return y


def draw_key(draw, key: str, since: float, show, top: int):
    """A key fact: small label, big value, one accent rule."""
    a = ease(since / 0.5) * show
    y = rise(a, max(top + 70, 1010), 30)
    spaced(draw, (PAD, y), "KEY FACT", font(28, 700), with_alpha(ACCENT, a), 0.18)
    size = 150
    face = font(size, 700)
    while draw.textlength(key, font=face) > W - 2 * PAD and size > 60:
        size -= 10
        face = font(size, 700)
    draw.rectangle([PAD, y + 52, PAD + 6, y + 52 + size * 1.05], fill=with_alpha(ACCENT, a))
    draw.text((PAD + 34, y + 44), key, font=face, fill=with_alpha(WHITE, a))


def draw_caption(draw, scene, lt):
    """Lower-third caption: the phrase being spoken; spoken words white, the current one underlined."""
    times, words = scene["times"], scene["words"]
    if lt > scene["speech"] + 0.15:
        return
    current = next((i for i, (a, b) in enumerate(times) if lt < b), len(words) - 1)
    first, last = next(c for c in scene["chunks"] if c[0] <= current < c[1])
    face = font(62, 700)
    space = draw.textlength(" ", font=face)
    rows, row, row_w = [], [], 0.0
    for i in range(first, last):
        w = draw.textlength(words[i], font=face)
        if row and row_w + space + w > W - 2 * PAD - 80:
            rows.append((row, row_w))
            row, row_w = [], 0.0
        row_w += (space if row else 0) + w
        row.append((i, w))
    rows = (rows + [(row, row_w)])[:2]
    a = ease((lt - times[first][0]) / 0.18)
    ty = 1500 - 76 * len(rows)
    for row, row_w in rows:
        x = (W - row_w) / 2
        for i, w in row:
            spoken = i <= current
            draw.text((x, ty), words[i], font=face, fill=with_alpha(WHITE if spoken else UPCOMING, a))
            if i == current:
                k = clamp((lt - times[i][0]) / max(times[i][1] - times[i][0], 0.05))
                draw.rectangle([x, ty + 72, x + w * ease(k * 1.4), ty + 77], fill=with_alpha(ACCENT, a))
            x += w + space
        ty += 76


# ---------- video ----------

def encode(script: dict, scenes: list[dict], pcm: bytes, rate: int, total: float, out: Path) -> Path:
    try:
        import imageio_ffmpeg
    except ImportError:
        die(3, "imageio-ffmpeg isn't installed; run the Setup step in SKILL.md.")
    out.parent.mkdir(parents=True, exist_ok=True)
    cover = out.with_name("cover.png")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "voice.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm)
        command = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                   "-i", str(wav), "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for n in range(math.ceil(total * FPS)):
                image = frame(script, scenes, total, n / FPS)
                if n == int(1.2 * FPS):
                    image.save(cover)
                process.stdin.write(image.tobytes())
            process.stdin.close()
        except BrokenPipeError:
            pass
        error = process.stderr.read().decode(errors="replace")
        if process.wait() != 0:
            die(4, f"Couldn't encode the video: {error.strip()[-300:]}")
    return cover


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
    scenes, pcm, rate, total = timeline(script, load_voice(args.voices_dir))
    cover = encode(script, scenes, pcm, rate, total, args.out)
    print(json.dumps({"mp4": str(args.out), "cover": str(cover), "seconds": round(total, 1),
                      "scenes": len(script["scenes"])}, indent=2))


if __name__ == "__main__":
    main()
